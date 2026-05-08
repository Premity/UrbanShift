"""
Seed database with schemes and housing data.

Usage (inside container via make):
    make seed
    # which runs: docker compose exec api python -m scripts.seed_db

Or directly:
    python -m scripts.seed_db
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data" / "seed"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://urbanshift:urbanshift_dev@db:5432/urbanshift",
)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_scheme_embedding_text(s: dict) -> str:
    extra = s.get("eligibility", {}).get("extra_rules_md") or ""
    categories = ", ".join(s.get("category", []))
    return f"{s['name']}. {categories}. {s.get('benefits_summary', '')}. {extra}".strip()


def _load_json(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        print(f"  [skip] {path.name} — file missing or empty")
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            print(f"  [skip] {path.name} — expected JSON array, got {type(data).__name__}")
            return []
        return data
    except json.JSONDecodeError as e:
        print(f"  [skip] {path.name} — JSON parse error: {e}")
        return []


async def seed_schemes(session: AsyncSession, encoder) -> int:
    from models.scheme import Scheme

    raw_schemes = _load_json(SEED_DIR / "schemes.json")
    if not raw_schemes:
        return 0

    upserted = 0
    for raw in raw_schemes:
        sid = raw.get("id")
        if not sid:
            print("  [warn] scheme missing id, skipping")
            continue

        existing = await session.get(Scheme, sid)
        embedding_text = _build_scheme_embedding_text(raw)
        vector = encoder.encode(embedding_text).tolist()

        attrs = dict(
            name=raw["name"],
            level=raw["level"],
            state=raw.get("state"),
            category=raw.get("category", []),
            has_jobs=raw.get("has_jobs", False),
            eligibility_json=raw.get("eligibility", {}),
            docs_required=raw.get("docs_required"),
            benefits_summary=raw.get("benefits_summary"),
            benefits_detail_md=raw.get("benefits_detail_md"),
            apply_link=raw["apply_link"],
            source_url=raw["source_url"],
            source_name=raw["source_name"],
            scraped_at=_parse_dt(raw.get("scraped_at")),
            embedding=vector,
        )

        if existing:
            for k, v in attrs.items():
                setattr(existing, k, v)
        else:
            session.add(Scheme(id=sid, **attrs))

        upserted += 1

    return upserted


async def seed_housing(session: AsyncSession) -> int:
    from models.housing import Housing

    raw_items = _load_json(SEED_DIR / "housing.json")
    if not raw_items:
        return 0

    upserted = 0
    for raw in raw_items:
        hid = raw.get("id")
        if not hid:
            print("  [warn] housing missing id, skipping")
            continue

        existing = await session.get(Housing, hid)

        attrs = dict(
            name=raw["name"],
            area=raw["area"],
            lat=raw.get("lat"),
            lng=raw.get("lng"),
            type=raw.get("type"),
            price_min=raw["price_min"],
            price_max=raw["price_max"],
            occupancy=raw.get("occupancy"),
            gender=raw.get("gender"),
            amenities=raw.get("amenities"),
            source_url=raw["source_url"],
            source_name=raw["source_name"],
            scraped_at=_parse_dt(raw.get("scraped_at")),
        )

        if existing:
            for k, v in attrs.items():
                setattr(existing, k, v)
        else:
            session.add(Housing(id=hid, **attrs))

        upserted += 1

    return upserted


async def main() -> None:
    print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded.\n")

    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        async with session.begin():
            print("Seeding schemes...")
            n_schemes = await seed_schemes(session, encoder)
            print(f"  → {n_schemes} schemes upserted")

            print("Seeding housing...")
            n_housing = await seed_housing(session)
            print(f"  → {n_housing} housing entries upserted")

    await engine.dispose()

    print("\nVerifying embedding population...")
    async with factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM schemes WHERE embedding IS NOT NULL")
        )
        print(f"  schemes with embedding: {result.scalar_one()}")

    print("\nSeed complete.")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    asyncio.run(main())
