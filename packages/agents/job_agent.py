"""Job Agent — T13 implementation (PRD §6.3).

Pipeline: structured filter → semantic rerank → scheme-linked join
         → LLM score_match per top 10 → return top 6.

This module is designed as a standalone async node that will be wired
into the LangGraph StateGraph by T16.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

# ── Lazy-loaded singletons ────────────────────────────────

_embedding_model = None
_job_prompt: Optional[str] = None

logger = logging.getLogger(__name__)


def _get_embedding_model():
    """Return the shared SentenceTransformer model (loaded once)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _get_job_prompt() -> str:
    """Load the Job Agent system prompt from disk (cached)."""
    global _job_prompt
    if _job_prompt is None:
        prompt_path = Path(__file__).parent / "prompts" / "job.txt"
        _job_prompt = prompt_path.read_text(encoding="utf-8")
    return _job_prompt


# ── Data Types ────────────────────────────────────────────


class JobMatchResult(BaseModel):
    """A single job match returned by the agent."""
    job: dict[str, Any]
    match_score: int = Field(ge=0, le=100)
    match_reason: str = ""
    scheme_link: Optional[str] = None
    citation: str = ""


class JobAgentOutput(BaseModel):
    """Output of the Job Agent node."""
    jobs: list[JobMatchResult] = Field(default_factory=list)


# ── Tool 1: Structured Search ────────────────────────────


async def search_jobs_structured(
    db: AsyncSession,
    profile: dict[str, Any],
    *,
    limit: int = 30,
) -> list[Any]:
    """Filter jobs by worker band (±1), preferred areas, and salary lower bound.

    Returns up to ``limit`` Job ORM rows.
    """
    from models.job import Job  # noqa: runtime import — avoids circular at module level

    band = profile.get("worker_band", 2)
    bands = [b for b in [band - 1, band, band + 1] if 1 <= b <= 4]

    conditions = [Job.worker_band.in_(bands)]

    # Area filter (if preferences set)
    preferred_areas = profile.get("preferred_areas") or []
    if preferred_areas:
        conditions.append(Job.area.in_(preferred_areas))

    # Salary lower-bound filter
    income_range = profile.get("income_range_inr")
    if income_range and isinstance(income_range, (list, tuple)) and len(income_range) >= 1:
        salary_floor = income_range[0]
        if salary_floor and salary_floor > 0:
            # Job should pay at least the candidate's minimum expectation
            # Use pay_max (best case) — if not set, skip the filter for that row
            conditions.append(
                or_(Job.pay_max >= salary_floor, Job.pay_max.is_(None))
            )

    stmt = select(Job).where(and_(*conditions)).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Tool 2: Semantic Search ──────────────────────────────


async def search_jobs_semantic(
    db: AsyncSession,
    profile: dict[str, Any],
    *,
    top_k: int = 15,
) -> list[Any]:
    """Embed the profile and retrieve closest jobs by cosine distance.

    Embedding text: ``"{sector}. {skills}. {education}"``.
    """
    from models.job import Job

    sector = profile.get("sector", "general")
    skills = ", ".join(profile.get("skills", []))
    education = profile.get("education", "")
    embed_text = f"{sector}. {skills}. {education}"

    model = _get_embedding_model()
    query_vec = model.encode(embed_text).tolist()

    # pgvector cosine-distance operator: <=>
    stmt = (
        select(Job)
        .where(Job.embedding.isnot(None))
        .order_by(Job.embedding.cosine_distance(query_vec))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Tool 3: Scheme-Linked Jobs ───────────────────────────


async def get_scheme_linked_jobs(
    db: AsyncSession,
    scheme_ids: list[str],
) -> list[Any]:
    """Return all jobs linked to the given scheme IDs."""
    if not scheme_ids:
        return []

    from models.job import Job

    stmt = select(Job).where(Job.scheme_link_id.in_(scheme_ids))
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── Tool 4: LLM Score Match ─────────────────────────────


async def score_match(
    job_dict: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Call LLM to score how well a job matches a profile.

    Returns ``{"score": int, "reason": str}``.
    Falls back to heuristic scoring if LLM is unavailable.
    """
    try:
        import litellm

        llm_profile = os.getenv("LLM_PROFILE", "dev")
        if llm_profile == "demo":
            model = "gemini/gemini-2.5-flash"
        else:
            model = "groq/llama-3.3-70b-versatile"

        system_prompt = _get_job_prompt()

        user_message = json.dumps(
            {
                "job": {
                    "title": job_dict.get("title", ""),
                    "sector": job_dict.get("sector", ""),
                    "required_skills": job_dict.get("required_skills", []),
                    "worker_band": job_dict.get("worker_band"),
                    "area": job_dict.get("area", ""),
                    "pay_min": job_dict.get("pay_min"),
                    "pay_max": job_dict.get("pay_max"),
                    "scheme_link_id": job_dict.get("scheme_link_id"),
                },
                "profile": {
                    "sector": profile.get("sector", ""),
                    "skills": profile.get("skills", []),
                    "worker_band": profile.get("worker_band", 2),
                    "education": profile.get("education", ""),
                    "preferred_areas": profile.get("preferred_areas", []),
                    "income_range_inr": profile.get("income_range_inr"),
                },
            },
            indent=2,
        )

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return {
            "score": max(0, min(100, int(parsed.get("score", 50)))),
            "reason": parsed.get("reason", ""),
        }

    except Exception as exc:
        logger.warning("LLM score_match failed, using heuristic: %s", exc)
        return _heuristic_score(job_dict, profile)


def _heuristic_score(job_dict: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Deterministic fallback scoring when LLM is unavailable."""
    score = 50  # base

    # Band proximity (±0 = +20, ±1 = +10, else +0)
    job_band = job_dict.get("worker_band") or 2
    profile_band = profile.get("worker_band", 2)
    band_diff = abs(job_band - profile_band)
    if band_diff == 0:
        score += 20
    elif band_diff == 1:
        score += 10

    # Skill keyword overlap
    job_skills = set(s.lower() for s in (job_dict.get("required_skills") or []))
    profile_skills = set(s.lower() for s in (profile.get("skills") or []))
    if job_skills and profile_skills:
        overlap = len(job_skills & profile_skills)
        score += min(15, overlap * 5)

    # Sector match
    if (job_dict.get("sector") or "").lower() == (profile.get("sector") or "").lower():
        score += 10

    # Area match
    preferred = set(a.lower() for a in (profile.get("preferred_areas") or []))
    if preferred and (job_dict.get("area") or "").lower() in preferred:
        score += 5

    reason_parts = []
    if band_diff == 0:
        reason_parts.append("exact band match")
    if job_skills & profile_skills:
        reason_parts.append(f"skill overlap: {', '.join(job_skills & profile_skills)}")
    if not reason_parts:
        reason_parts.append("general match based on profile")

    return {
        "score": max(0, min(100, score)),
        "reason": "; ".join(reason_parts),
    }


# ── Helpers ──────────────────────────────────────────────


def _job_to_dict(job_row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Job row to a plain dict."""
    return {
        "id": job_row.id,
        "source": job_row.source,
        "source_url": job_row.source_url,
        "source_listing_id": job_row.source_listing_id,
        "title": job_row.title,
        "employer": job_row.employer,
        "area": job_row.area,
        "lat": job_row.lat,
        "lng": job_row.lng,
        "pay_min": job_row.pay_min,
        "pay_max": job_row.pay_max,
        "sector": job_row.sector,
        "required_skills": job_row.required_skills or [],
        "worker_band": job_row.worker_band,
        "scheme_link_id": job_row.scheme_link_id,
        "description_md": job_row.description_md,
        "scraped_at": job_row.scraped_at.isoformat() if job_row.scraped_at else None,
    }


def _pre_score(job_dict: dict[str, Any], profile: dict[str, Any]) -> float:
    """Quick heuristic for ranking before LLM call (higher = better)."""
    score = 0.0

    # Band closeness (0 diff = 3, 1 diff = 1, else 0)
    job_band = job_dict.get("worker_band") or 2
    profile_band = profile.get("worker_band", 2)
    band_diff = abs(job_band - profile_band)
    if band_diff == 0:
        score += 3
    elif band_diff == 1:
        score += 1

    # Area match
    preferred = set(a.lower() for a in (profile.get("preferred_areas") or []))
    if preferred and (job_dict.get("area") or "").lower() in preferred:
        score += 2

    # Sector match
    if (job_dict.get("sector") or "").lower() == (profile.get("sector") or "").lower():
        score += 2

    # Scheme-linked bonus
    if job_dict.get("scheme_link_id"):
        score += 1

    return score


# ── Main Agent Node ──────────────────────────────────────


async def run_job_agent(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node entry point.

    Reads ``profile`` and ``scheme_out`` from state.
    Returns ``{"job_out": [...]}``.
    """
    from database import async_session_factory

    profile: dict[str, Any] = state.get("profile", {})
    scheme_out: list[dict[str, Any]] = state.get("scheme_out", [])

    # Extract scheme IDs where has_jobs is True
    scheme_ids_with_jobs = []
    for s in scheme_out:
        nested_scheme = s.get("scheme") if isinstance(s.get("scheme"), dict) else None
        has_jobs = s.get("has_jobs") or (nested_scheme and nested_scheme.get("has_jobs"))
        scheme_id = s.get("id")
        if scheme_id is None and nested_scheme:
            scheme_id = nested_scheme.get("id")
        if has_jobs and scheme_id is not None:
            scheme_ids_with_jobs.append(scheme_id)
    # All scheme IDs in the output (for tagging)
    all_scheme_ids = set()
    for s in scheme_out:
        if "id" in s:
            all_scheme_ids.add(s["id"])
        if isinstance(s.get("scheme"), dict) and "id" in s["scheme"]:
            all_scheme_ids.add(s["scheme"]["id"])

    async with async_session_factory() as db:
        # Step 1: Structured search
        structured_jobs = await search_jobs_structured(db, profile)
        logger.info("Structured search returned %d jobs", len(structured_jobs))

        # Step 2: Semantic search
        semantic_jobs = await search_jobs_semantic(db, profile)
        logger.info("Semantic search returned %d jobs", len(semantic_jobs))

        # Step 3: Merge & de-duplicate
        candidates: dict[str, dict[str, Any]] = {}
        for job_row in structured_jobs:
            candidates[job_row.id] = _job_to_dict(job_row)
        for job_row in semantic_jobs:
            if job_row.id not in candidates:
                candidates[job_row.id] = _job_to_dict(job_row)

        # Step 4: Scheme-linked jobs
        if scheme_ids_with_jobs:
            linked_jobs = await get_scheme_linked_jobs(db, scheme_ids_with_jobs)
            logger.info("Scheme-linked search returned %d jobs", len(linked_jobs))
            for job_row in linked_jobs:
                if job_row.id not in candidates:
                    candidates[job_row.id] = _job_to_dict(job_row)

    # Step 5: Tag scheme links for any candidate whose scheme_link_id is in output
    for job_dict in candidates.values():
        if job_dict.get("scheme_link_id") and job_dict["scheme_link_id"] in all_scheme_ids:
            job_dict["_scheme_linked"] = True

    # Step 6: Pre-score and pick top 10 for LLM scoring
    candidate_list = list(candidates.values())
    candidate_list.sort(key=lambda j: _pre_score(j, profile), reverse=True)
    top_candidates = candidate_list[:10]

    # Step 7: LLM score each candidate
    results: list[JobMatchResult] = []
    for job_dict in top_candidates:
        score_result = await score_match(job_dict, profile)

        # Build the match result
        result = JobMatchResult(
            job=job_dict,
            match_score=score_result["score"],
            match_reason=score_result["reason"],
            scheme_link=job_dict.get("scheme_link_id") if job_dict.get("_scheme_linked") else None,
            citation=job_dict.get("source_url", ""),
        )
        results.append(result)

    # Step 8: Sort by LLM score descending, return top 6
    results.sort(key=lambda r: r.match_score, reverse=True)
    top_results = results[:6]

    logger.info(
        "Job Agent complete: %d candidates → %d scored → %d returned",
        len(candidates),
        len(results),
        len(top_results),
    )

    return {"job_out": [r.model_dump() for r in top_results]}
