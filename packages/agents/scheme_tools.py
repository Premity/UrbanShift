"""Scheme Agent tools — deterministic functions for scheme retrieval and eligibility.

Tools:
    search_schemes_semantic  — embed profile → pgvector cosine (or keyword fallback)
    filter_by_seeker_type    — categorical pre-filter on scheme.category
    check_eligibility        — deterministic rule eval against EligibilitySchema
    explain_benefits         — returns benefit summary (optionally LLM-personalised)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Category mapping: seeker_type → relevant scheme categories ───

SEEKER_CATEGORY_MAP: dict[str, set[str]] = {
    "job": {
        "welfare", "registration", "insurance", "financial",
        "skill_training", "employment", "apprenticeship",
        "social_security", "job_portal",
    },
    "housing": {
        "welfare", "registration", "insurance", "financial",
        "housing", "rental",
    },
    "both": {
        "welfare", "registration", "insurance", "financial",
        "skill_training", "employment", "apprenticeship",
        "social_security", "job_portal",
        "housing", "rental",
    },
}


# ═══════════════════════════════════════════════════════════════
#  Tool 1: search_schemes_semantic
# ═══════════════════════════════════════════════════════════════

def _build_profile_text(profile: dict[str, Any]) -> str:
    """Build a natural-language snippet from a profile for embedding."""
    parts = []
    if profile.get("sector"):
        parts.append(f"Looking for work in {profile['sector']}")
    if profile.get("skills"):
        parts.append(f"Skills: {', '.join(profile['skills'])}")
    if profile.get("education"):
        parts.append(f"Education: {profile['education']}")
    if profile.get("employment_status"):
        parts.append(f"Currently {profile['employment_status']}")
    if profile.get("migrant_status"):
        parts.append(f"Migrant status: {profile['migrant_status']}")
    if profile.get("origin_state"):
        parts.append(f"From state: {profile['origin_state']}")
    if profile.get("budget_inr"):
        parts.append(f"Housing budget: ₹{profile['budget_inr']}/month")
    if profile.get("worker_band"):
        parts.append(f"Worker band: {profile['worker_band']}")
    return ". ".join(parts) if parts else "Urban migrant seeking assistance in Bengaluru"


def _keyword_score(scheme: dict[str, Any], profile: dict[str, Any]) -> float:
    """Fallback relevance scoring when embeddings are not available.

    Counts keyword overlap between profile fields and scheme text,
    and gives bonus for band/sector matches.
    """
    score = 0.0

    # Profile keywords
    profile_keywords: set[str] = set()
    for field in ("sector", "education", "employment_status", "migrant_status"):
        val = profile.get(field)
        if val:
            profile_keywords.add(str(val).lower())
    for skill in profile.get("skills", []):
        profile_keywords.add(skill.lower())

    # Scheme text
    scheme_text = " ".join([
        scheme.get("name", ""),
        scheme.get("benefits_summary", ""),
        " ".join(scheme.get("category", [])),
    ]).lower()

    # Keyword overlap
    for kw in profile_keywords:
        if kw in scheme_text:
            score += 1.0

    # Band match bonus
    elig = scheme.get("eligibility", {})
    worker_bands = elig.get("worker_bands")
    if worker_bands and profile.get("worker_band") in worker_bands:
        score += 2.0

    # Sector match bonus
    sectors = elig.get("sectors")
    if sectors and profile.get("sector") in sectors:
        score += 2.0

    # Migrant bonus
    if elig.get("migrant_only") and profile.get("migrant_status") in ("just_moved", "planning"):
        score += 1.5

    # has_jobs bonus for job seekers
    if scheme.get("has_jobs") and profile.get("employment_status") in ("unemployed", "underemployed"):
        score += 1.5

    return score


def search_schemes_semantic(
    all_schemes: list[dict[str, Any]],
    profile: dict[str, Any],
    top_k: int = 20,
    embedder: Any = None,
) -> list[dict[str, Any]]:
    """Rank schemes by relevance to a profile.

    If ``embedder`` is provided and schemes have embeddings, uses cosine
    similarity.  Otherwise falls back to keyword scoring.

    Args:
        all_schemes: List of scheme dicts (from DB or seed JSON).
        profile: User profile dict.
        top_k: Max results to return.
        embedder: Optional sentence-transformers model.

    Returns:
        Sorted list of (scheme_dict, score) limited to top_k.
    """
    # Check if we can do vector search
    has_embeddings = any(s.get("embedding") is not None for s in all_schemes)

    if has_embeddings and embedder is not None:
        profile_text = _build_profile_text(profile)
        profile_emb = embedder.encode(profile_text).tolist()

        scored = []
        for scheme in all_schemes:
            emb = scheme.get("embedding")
            if emb is None:
                scored.append((scheme, 0.0))
                continue
            # Cosine similarity
            dot = sum(a * b for a, b in zip(profile_emb, emb))
            norm_a = math.sqrt(sum(a * a for a in profile_emb))
            norm_b = math.sqrt(sum(b * b for b in emb))
            cos_sim = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0
            scored.append((scheme, cos_sim))
    else:
        logger.info("Using keyword fallback scoring (no embeddings or embedder)")
        scored = [(s, _keyword_score(s, profile)) for s in all_schemes]

    scored.sort(key=lambda x: x[1], reverse=True)

    # Attach score to each scheme
    results = []
    for scheme, score in scored[:top_k]:
        s = dict(scheme)
        s["_relevance_score"] = round(score, 4)
        results.append(s)

    return results


# ═══════════════════════════════════════════════════════════════
#  Tool 2: filter_by_seeker_type
# ═══════════════════════════════════════════════════════════════

def filter_by_seeker_type(
    schemes: list[dict[str, Any]],
    seeker_type: str,
) -> list[dict[str, Any]]:
    """Keep schemes whose category overlaps with the seeker's needs.

    ``seeker_type`` is one of ``job``, ``housing``, ``both``.
    """
    allowed_cats = SEEKER_CATEGORY_MAP.get(seeker_type, SEEKER_CATEGORY_MAP["both"])

    filtered = []
    for scheme in schemes:
        cats = set(scheme.get("category", []))
        if cats & allowed_cats:
            filtered.append(scheme)

    return filtered


# ═══════════════════════════════════════════════════════════════
#  Tool 3: check_eligibility
# ═══════════════════════════════════════════════════════════════

def check_eligibility(
    scheme: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic eligibility check.

    Compares scheme.eligibility rules against profile fields.

    Returns:
        ``{"eligible": bool, "reasons": list[str]}``
        Reasons explain *why* eligible or *why not*.
    """
    elig = scheme.get("eligibility", {})
    reasons_pass: list[str] = []
    reasons_fail: list[str] = []

    # ── Age ───────────────────────────────────────────
    age = profile.get("age", 0)
    age_min = elig.get("age_min")
    age_max = elig.get("age_max")
    if age_min is not None and age < age_min:
        reasons_fail.append(f"Age {age} is below minimum {age_min}")
    elif age_max is not None and age > age_max:
        reasons_fail.append(f"Age {age} is above maximum {age_max}")
    elif age_min or age_max:
        reasons_pass.append(f"Age {age} is within range ({age_min or '—'}–{age_max or '—'})")

    # ── Gender ────────────────────────────────────────
    gender = profile.get("gender")
    allowed_genders = elig.get("gender")
    if allowed_genders is not None and gender and gender not in allowed_genders:
        reasons_fail.append(f"Gender '{gender}' not in allowed: {allowed_genders}")
    elif allowed_genders and gender:
        reasons_pass.append(f"Gender '{gender}' is eligible")

    # ── Income ────────────────────────────────────────
    income_range = profile.get("income_range_inr")
    income_max = elig.get("income_max_inr")
    if income_max is not None and income_range:
        annual_income = max(income_range) * 12 if isinstance(income_range, (list, tuple)) else 0
        if annual_income > income_max:
            reasons_fail.append(
                f"Annual income ₹{annual_income:,} exceeds cap ₹{income_max:,}"
            )
        else:
            reasons_pass.append(f"Income within cap (₹{income_max:,}/year)")

    # ── Worker band ───────────────────────────────────
    worker_band = profile.get("worker_band")
    allowed_bands = elig.get("worker_bands")
    if allowed_bands is not None and worker_band is not None:
        if worker_band not in allowed_bands:
            reasons_fail.append(f"Worker band {worker_band} not in {allowed_bands}")
        else:
            reasons_pass.append(f"Worker band {worker_band} is eligible")

    # ── Sector ────────────────────────────────────────
    sector = profile.get("sector")
    allowed_sectors = elig.get("sectors")
    if allowed_sectors is not None and sector:
        if sector not in allowed_sectors:
            reasons_fail.append(f"Sector '{sector}' not in {allowed_sectors}")
        else:
            reasons_pass.append(f"Sector '{sector}' is targeted")

    # ── Aadhaar ───────────────────────────────────────
    requires_aadhaar = elig.get("requires_aadhaar", False)
    has_aadhaar = profile.get("aadhaar_available", False)
    if requires_aadhaar and not has_aadhaar:
        reasons_fail.append("Requires Aadhaar but user does not have one")
    elif requires_aadhaar and has_aadhaar:
        reasons_pass.append("Aadhaar available (required)")

    # ── Migrant only ──────────────────────────────────
    migrant_only = elig.get("migrant_only", False)
    migrant_status = profile.get("migrant_status", "long_term")
    if migrant_only and migrant_status == "long_term":
        reasons_fail.append("Scheme is migrant-only; user is long-term resident")
    elif migrant_only:
        reasons_pass.append("Migrant status qualifies")

    # ── State residency ───────────────────────────────
    state_req = elig.get("state_residency")
    if state_req is not None:
        origin = profile.get("origin_state", "")
        # Scheme requires specific state — check if user is from that state
        # or currently in that state (Bengaluru → KA)
        if origin != state_req and state_req != "KA":
            reasons_fail.append(
                f"Requires residency in {state_req}; user from {origin}"
            )
        else:
            reasons_pass.append(f"State residency OK ({state_req})")

    # ── Verdict ───────────────────────────────────────
    eligible = len(reasons_fail) == 0

    return {
        "eligible": eligible,
        "reasons": reasons_pass if eligible else reasons_fail,
    }


# ═══════════════════════════════════════════════════════════════
#  Tool 4: explain_benefits
# ═══════════════════════════════════════════════════════════════

def explain_benefits(
    scheme: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
) -> str:
    """Return a benefit summary for the scheme.

    Uses the stored ``benefits_detail_md`` or ``benefits_summary`` field.
    If an LLM is available in the future, this can be extended to generate
    a personalised summary.
    """
    detail = scheme.get("benefits_detail_md")
    if detail:
        return detail

    summary = scheme.get("benefits_summary", "")
    return summary if summary else f"Visit {scheme.get('apply_link', 'the official portal')} for details."
