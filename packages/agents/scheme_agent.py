"""Scheme Agent — LangGraph node for government scheme matching.

Pipeline:
    1. filter_by_seeker_type  → pre-filter by category
    2. search_schemes_semantic → rank by profile relevance (top 20)
    3. check_eligibility       → deterministic rule eval per scheme
    4. explain_benefits        → attach benefit summary + citation
    → return top 8 eligible schemes
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .scheme_tools import (
    check_eligibility,
    explain_benefits,
    filter_by_seeker_type,
    search_schemes_semantic,
)

logger = logging.getLogger(__name__)

# Max eligible schemes to return
MAX_RESULTS = 8


async def run_scheme_agent(
    all_schemes: list[dict[str, Any]],
    profile: dict[str, Any],
    seeker_type: str = "both",
    embedder: Any = None,
) -> dict[str, Any]:
    """Execute the scheme matching pipeline.

    Args:
        all_schemes: All scheme records (dicts with eligibility, category, etc.).
        profile: The user's profile dict.
        seeker_type: One of 'job', 'housing', 'both'.
        embedder: Optional sentence-transformers model for vector search.

    Returns:
        ``{"schemes": [...], "meta": {...}}``
    """
    logger.info(
        "Scheme agent: starting for seeker_type=%s, worker_band=%s, sector=%s",
        seeker_type,
        profile.get("worker_band"),
        profile.get("sector"),
    )

    # Step 1: Pre-filter by seeker type
    filtered = filter_by_seeker_type(all_schemes, seeker_type)
    logger.info("After seeker_type filter: %d / %d schemes", len(filtered), len(all_schemes))

    # Step 2: Semantic / keyword ranking
    ranked = search_schemes_semantic(filtered, profile, top_k=20, embedder=embedder)
    logger.info("After semantic ranking: top %d schemes", len(ranked))

    # Step 3: Eligibility check
    eligible_results: list[dict[str, Any]] = []
    ineligible_results: list[dict[str, Any]] = []

    for scheme in ranked:
        elig_result = check_eligibility(scheme, profile)

        entry = {
            "scheme_id": scheme["id"],
            "scheme_name": scheme["name"],
            "level": scheme.get("level", "central"),
            "category": scheme.get("category", []),
            "has_jobs": scheme.get("has_jobs", False),
            "eligibility_status": elig_result,
            "top_benefits": "",
            "citation": scheme.get("source_url", ""),
            "apply_link": scheme.get("apply_link", ""),
            "docs_required": scheme.get("docs_required", []),
            "_relevance_score": scheme.get("_relevance_score", 0),
        }

        if elig_result["eligible"]:
            eligible_results.append((entry, scheme))
        else:
            ineligible_results.append(entry)

    logger.info(
        "Eligibility: %d eligible, %d ineligible",
        len(eligible_results),
        len(ineligible_results),
    )

    # Step 4: Explain benefits for eligible schemes (top MAX_RESULTS)
    final_schemes: list[dict[str, Any]] = []
    for entry, scheme in eligible_results[:MAX_RESULTS]:
        entry["top_benefits"] = explain_benefits(scheme, profile)
        final_schemes.append(entry)

    return {
        "schemes": final_schemes,
        "meta": {
            "total_schemes": len(all_schemes),
            "after_seeker_filter": len(filtered),
            "after_ranking": len(ranked),
            "eligible": len(eligible_results),
            "ineligible": len(ineligible_results),
            "returned": len(final_schemes),
        },
    }
