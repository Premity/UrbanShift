"""Orchestrator Agent — entry (intent parse) and merge (plan build) phases.

Entry phase:
    - Validates profile fields
    - Auto-derives worker_band if missing
    - Emits an agent_step event

Merge phase:
    - Reads validator_out (validated + filtered_out)
    - Builds a Plan dict: {schemes, jobs, housing, checklist, citations, filtered_out}
    - Attaches citations from source items
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ── Worker-band derivation ──────────────────────────────────────────────────

_BAND_MAP: dict[str, int] = {
    # Band 1: unskilled / manual labour
    "construction": 1, "cleaning": 1, "labour": 1, "agriculture": 1,
    # Band 2: service / gig
    "driving": 2, "delivery": 2, "security": 2, "cooking": 2,
    "domestic": 2, "plumbing": 2, "electrician": 2, "mechanic": 2,
    # Band 3: semi-skilled / retail
    "retail": 3, "hospitality": 3, "tailoring": 3, "beauty": 3,
    "warehouse": 3, "manufacturing": 3,
    # Band 4: entry white-collar
    "bpo": 4, "data_entry": 4, "admin": 4, "accounting": 4,
    "customer_support": 4, "teaching": 4, "healthcare": 4,
}

_EDUCATION_BOOST: dict[str, int] = {
    "grad": 1, "postgrad": 1, "diploma": 1,
}


def derive_worker_band(profile: dict[str, Any]) -> int:
    """Compute worker_band (1-4) from sector + education + employment."""
    sector = (profile.get("sector") or "").lower().strip()
    education = (profile.get("education") or "").lower().strip()

    base = _BAND_MAP.get(sector, 2)  # default band 2

    # Boost for higher education
    boost = _EDUCATION_BOOST.get(education, 0)
    band = min(4, base + boost)

    return max(1, band)


# ── Entry Node ──────────────────────────────────────────────────────────────

def _make_step_event(agent: str, status: str, **extra: Any) -> dict[str, Any]:
    """Create an SSE-compatible agent_step event."""
    event: dict[str, Any] = {
        "type": "agent_step",
        "agent": agent,
        "status": status,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    event.update(extra)
    return event


async def orchestrator_entry_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — entry phase.

    Validates profile, derives worker_band, emits initial step event.

    Returns a PARTIAL state update (LangGraph reducer semantics).
    """
    profile: dict[str, Any] = dict(state.get("profile", {}))
    seeker_type: str = state.get("seeker_type", profile.get("seeker_type", "both"))

    # Auto-derive worker_band if absent or zero
    if not profile.get("worker_band"):
        profile["worker_band"] = derive_worker_band(profile)
        logger.info("Derived worker_band=%d for sector=%s", profile["worker_band"], profile.get("sector"))

    # Ensure seeker_type is set in profile
    profile["seeker_type"] = seeker_type

    logger.info(
        "Orchestrator entry: seeker_type=%s, worker_band=%d",
        seeker_type,
        profile.get("worker_band", 0),
    )

    # Return only CHANGED keys — agent_steps uses operator.add reducer,
    # so return only the NEW events (not the full accumulated list).
    return {
        "profile": profile,
        "seeker_type": seeker_type,
        "agent_steps": [
            _make_step_event("orchestrator", "running"),
            _make_step_event("orchestrator", "complete"),
        ],
    }


# ── Merge Node ──────────────────────────────────────────────────────────────

def _build_checklist(
    schemes: list[dict], jobs: list[dict], housing: list[dict]
) -> list[dict[str, Any]]:
    """Build a human-readable checklist of next steps from validated items."""
    checklist: list[dict[str, Any]] = []
    step = 1

    # Scheme steps
    for s in schemes:
        name = s.get("scheme_name") or s.get("name") or s.get("scheme_id", "Unknown scheme")
        apply_link = s.get("apply_link") or s.get("citation") or ""
        checklist.append({
            "step": step,
            "text": f"Apply for {name}",
            "category": "scheme",
            "item_id": s.get("scheme_id") or s.get("id"),
            "citation": apply_link,
        })
        step += 1

    # Job steps
    for j in jobs:
        job_data = j.get("job", j)
        title = job_data.get("title", "Job opportunity")
        employer = job_data.get("employer") or "employer"
        source_url = j.get("citation") or job_data.get("source_url", "")
        checklist.append({
            "step": step,
            "text": f"Apply for '{title}' at {employer}",
            "category": "job",
            "item_id": job_data.get("id"),
            "citation": source_url,
        })
        step += 1

    # Housing steps
    for h in housing:
        name = h.get("name", "Housing option")
        area = h.get("area", "")
        source_url = h.get("source_url", "")
        checklist.append({
            "step": step,
            "text": f"Contact {name} in {area}" if area else f"Contact {name}",
            "category": "housing",
            "item_id": h.get("id"),
            "citation": source_url,
        })
        step += 1

    # Document prep step (always)
    checklist.append({
        "step": step,
        "text": "Keep Aadhaar card and other ID documents ready for applications",
        "category": "general",
        "item_id": None,
        "citation": "",
    })

    return checklist


def _collect_citations(
    schemes: list[dict], jobs: list[dict], housing: list[dict]
) -> list[dict[str, str]]:
    """Collect all source citations across verticals."""
    seen: set[str] = set()
    citations: list[dict[str, str]] = []

    for s in schemes:
        url = s.get("citation") or s.get("source_url") or ""
        name = s.get("source_name") or s.get("scheme_name") or ""
        if url and url not in seen:
            seen.add(url)
            citations.append({"source_url": url, "source_name": name})

    for j in jobs:
        job_data = j.get("job", j)
        url = j.get("citation") or job_data.get("source_url") or ""
        name = job_data.get("source") or ""
        if url and url not in seen:
            seen.add(url)
            citations.append({"source_url": url, "source_name": name})

    for h in housing:
        url = h.get("source_url") or ""
        name = h.get("source_name") or ""
        if url and url not in seen:
            seen.add(url)
            citations.append({"source_url": url, "source_name": name})

    return citations


async def orchestrator_merge_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node — merge phase.

    Reads validator_out, builds the final Plan dict with checklist + citations.

    Returns a PARTIAL state update (LangGraph reducer semantics).
    """
    validator_out: dict = state.get("validator_out", {})

    validated = validator_out.get("validated", {})
    filtered_out = validator_out.get("filtered_out", [])

    schemes = validated.get("schemes", [])
    jobs = validated.get("jobs", [])
    housing = validated.get("housing", [])

    checklist = _build_checklist(schemes, jobs, housing)
    citations = _collect_citations(schemes, jobs, housing)

    plan = {
        "schemes": schemes,
        "jobs": jobs,
        "housing": housing,
        "checklist": checklist,
        "citations": citations,
        "filtered_out": filtered_out,
    }

    logger.info(
        "Orchestrator merge: %d schemes, %d jobs, %d housing, %d filtered, %d checklist steps",
        len(schemes), len(jobs), len(housing), len(filtered_out), len(checklist),
    )

    # Return only CHANGED keys — agent_steps uses operator.add reducer.
    return {
        "plan": plan,
        "agent_steps": [
            _make_step_event("merge", "running"),
            _make_step_event(
                "merge", "complete",
                schemes_count=len(schemes),
                jobs_count=len(jobs),
                housing_count=len(housing),
                filtered_count=len(filtered_out),
            ),
        ],
    }
