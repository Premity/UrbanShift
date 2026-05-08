"""Seed scheme embeddings into the database.

Usage:
    docker compose exec api python /scripts/seed_scheme_embeddings.py

Generates 384-dimensional embeddings using sentence-transformers/all-MiniLM-L6-v2
for each scheme in the DB. Idempotent — skips schemes that already have embeddings.
"""

import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def build_scheme_text(scheme_row) -> str:
    """Build a text snippet from a scheme record for embedding."""
    parts = [
        scheme_row.name,
        f"Level: {scheme_row.level}",
        f"Categories: {', '.join(scheme_row.category or [])}",
    ]
    if scheme_row.benefits_summary:
        parts.append(scheme_row.benefits_summary)
    if scheme_row.benefits_detail_md:
        # Take first 200 chars of detail
        parts.append(scheme_row.benefits_detail_md[:200])

    # Add eligibility keywords
    elig = scheme_row.eligibility_json or {}
    if elig.get("sectors"):
        parts.append(f"Sectors: {', '.join(elig['sectors'])}")
    if elig.get("worker_bands"):
        parts.append(f"Worker bands: {', '.join(str(b) for b in elig['worker_bands'])}")
    if elig.get("migrant_only"):
        parts.append("For migrants")
    if elig.get("requires_aadhaar"):
        parts.append("Requires Aadhaar")

    return ". ".join(parts)


async def main():
    # Import here so the script can be run from the API container
    # where PYTHONPATH includes /app
    try:
        from sqlalchemy import text as sql_text
        from database import engine
        from models import Scheme
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    except ImportError:
        logger.error(
            "Cannot import database modules. "
            "Run this inside the API container: "
            "docker compose exec api python /scripts/seed_scheme_embeddings.py"
        )
        sys.exit(1)

    # Load the embedding model
    logger.info("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
        logger.info("Install with: pip install sentence-transformers")
        sys.exit(1)

    # Connect to DB
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Fetch all schemes
        result = await session.execute(select(Scheme))
        schemes = result.scalars().all()
        logger.info("Found %d schemes in database", len(schemes))

        updated = 0
        skipped = 0

        for scheme in schemes:
            if scheme.embedding is not None:
                skipped += 1
                continue

            text = build_scheme_text(scheme)
            embedding = model.encode(text).tolist()

            await session.execute(
                sql_text(
                    "UPDATE schemes SET embedding = :emb WHERE id = :sid"
                ),
                {"emb": str(embedding), "sid": scheme.id},
            )
            updated += 1
            logger.info("  ✓ %s: embedded (%d chars)", scheme.id, len(text))

        await session.commit()
        logger.info(
            "Done: %d updated, %d skipped (already had embeddings)",
            updated, skipped,
        )


if __name__ == "__main__":
    asyncio.run(main())
