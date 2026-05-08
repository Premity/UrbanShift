"""Scheme matching routes — POST /api/schemes/match.

Exposes the Scheme Agent pipeline as an API endpoint for testing
and for use by the Orchestrator agent.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Scheme

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schemes", tags=["schemes"])

# ── Seed data fallback path ──────────────────────────────
SEED_PATH = Path("/data/seed/schemes.json")


# ── Request / Response schemas ───────────────────────────

class SchemeMatchRequest(BaseModel):
    """Profile to match against schemes."""
    profile: dict[str, Any]


class EligibilityResult(BaseModel):
    eligible: bool
    reasons: list[str] = Field(default_factory=list)


class SchemeMatchItem(BaseModel):
    scheme_id: str
    scheme_name: str
    level: str = "central"
    category: list[str] = Field(default_factory=list)
    has_jobs: bool = False
    eligibility_status: EligibilityResult
    top_benefits: str = ""
    citation: str = ""
    apply_link: str = ""
    docs_required: list[str] = Field(default_factory=list)


class SchemeMatchResponse(BaseModel):
    schemes: list[SchemeMatchItem]
    meta: dict[str, Any] = Field(default_factory=dict)


# ── Helpers ──────────────────────────────────────────────

def _scheme_row_to_dict(row: Scheme) -> dict[str, Any]:
    """Convert a SQLAlchemy Scheme row to a plain dict for the tools."""
    return {
        "id": row.id,
        "name": row.name,
        "level": row.level,
        "state": row.state,
        "category": row.category or [],
        "has_jobs": row.has_jobs,
        "eligibility": row.eligibility_json or {},
        "docs_required": row.docs_required or [],
        "benefits_summary": row.benefits_summary or "",
        "benefits_detail_md": row.benefits_detail_md or "",
        "apply_link": row.apply_link,
        "source_url": row.source_url,
        "source_name": row.source_name,
        "embedding": list(row.embedding) if row.embedding else None,
    }


async def _load_schemes(db: AsyncSession) -> list[dict[str, Any]]:
    """Load schemes from DB, falling back to seed JSON if table is empty."""
    result = await db.execute(select(Scheme))
    rows = result.scalars().all()

    if rows:
        logger.info("Loaded %d schemes from database", len(rows))
        return [_scheme_row_to_dict(r) for r in rows]

    # Fallback: load from seed file
    if SEED_PATH.exists():
        logger.warning("No schemes in DB — falling back to seed JSON")
        with open(SEED_PATH) as f:
            data = json.load(f)
        return data

    logger.error("No schemes found in DB or seed file")
    return []


# ── POST /api/schemes/match ─────────────────────────────

@router.post("/match", response_model=SchemeMatchResponse)
async def match_schemes(
    body: SchemeMatchRequest,
    db: AsyncSession = Depends(get_db),
) -> SchemeMatchResponse:
    """Run the Scheme Agent pipeline against a user profile.

    Returns a ranked list of eligible government schemes with
    citations and benefit explanations.
    """
    profile = body.profile

    # Validate minimum profile fields
    if not profile.get("worker_band") and not profile.get("sector"):
        raise HTTPException(
            status_code=400,
            detail="Profile must include at least 'worker_band' or 'sector'",
        )

    # Load schemes
    all_schemes = await _load_schemes(db)
    if not all_schemes:
        raise HTTPException(status_code=500, detail="No scheme data available")

    # Run the agent
    from packages.agents.scheme_agent import run_scheme_agent

    seeker_type = profile.get("seeker_type", "both")
    result = await run_scheme_agent(
        all_schemes=all_schemes,
        profile=profile,
        seeker_type=seeker_type,
        embedder=None,  # Use keyword fallback; embedder loaded on demand later
    )

    return SchemeMatchResponse(**result)
