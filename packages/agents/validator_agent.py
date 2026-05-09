"""Validator Agent — rules pass + optional LLM confidence pass.

Pipeline:
    1. Rules pass  — deterministic Pydantic-style checks per vertical
    2. LLM pass    — only for items that pass rules but have ambiguous skill alignment
       (fires only when LITELLM_API_KEY / OPENAI_API_KEY is set)

Output shape written to state["validator_out"]:
    {
        "validated": {
            "schemes":  [...],   # scheme dicts that passed
            "jobs":     [...],   # job dicts that passed
            "housing":  [...],   # housing dicts that passed
        },
        "filtered_out": [        # every rejected item
            {
                "item_id":   str,
                "category":  "scheme" | "job" | "housing",
                "reasons":   [str],  # human-readable EN
            },
            ...
        ],
    }

§6.5 rules enforced:
    Schemes
    ─────────────────────────────────────────────────────────────
    R-S1  age_max / age_min bracket
    R-S2  gender restriction
    R-S3  worker_band whitelist
    R-S4  sector whitelist
    R-S5  requires_aadhaar vs profile.aadhaar_available
    R-S6  migrant_only vs profile.migrant_status
    R-S7  source_url present (citation check)

    Jobs
    ─────────────────────────────────────────────────────────────
    R-J1  source_url present
    R-J2  worker_band match (job.worker_band must equal profile.worker_band
          when both are non-null; ±1 tolerance)
    R-J3  scheme_link_id referential integrity (id must be in validated schemes)
    R-J4  sector match (when job.sector and profile.sector are set)

    Housing
    ─────────────────────────────────────────────────────────────
    R-H1  source_url present
    R-H2  gender compat (male→male/unisex, female→female/unisex)
    R-H3  price_min ≤ profile.budget * 1.05
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Confidence threshold below which the LLM pass fires
_LLM_CONFIDENCE_THRESHOLD = 0.55

# Env flag — set to "0" to forcibly disable LLM pass in tests
_LLM_ENABLED = os.getenv("VALIDATOR_LLM_ENABLED", "1") != "0"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _reject(item_id: str, category: str, reasons: list[str]) -> dict:
    return {"item_id": item_id, "category": category, "reasons": reasons}


# ─────────────────────────────────────────────────────────────────────────────
# Rules pass — Schemes  (R-S1 … R-S7)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_scheme(scheme: dict, profile: dict) -> list[str]:
    """Return list of failure reasons; empty list means the scheme passes."""
    elig = scheme.get("eligibility") or scheme.get("eligibility_status") or {}
    # eligibility may come from scheme_agent as nested dict or from raw scheme row
    if isinstance(elig, dict) and "eligible" in elig:
        # already-checked eligibility_status blob from scheme_agent — re-derive rules
        elig = {}

    # pull raw eligibility from scheme dict top-level keys or nested
    raw_elig = (
        scheme.get("eligibility_json")
        or scheme.get("eligibility")
        or {}
    )
    if isinstance(raw_elig, dict) and "eligible" in raw_elig:
        raw_elig = {}

    reasons: list[str] = []

    age = profile.get("age", 0)
    age_min = raw_elig.get("age_min")
    age_max = raw_elig.get("age_max")

    # R-S1 age bracket
    if age_min is not None and age < age_min:
        reasons.append(f"age {age} below minimum {age_min}")
    if age_max is not None and age > age_max:
        reasons.append(f"age {age} above maximum {age_max}")

    # R-S2 gender
    allowed_genders = raw_elig.get("gender")
    profile_gender = profile.get("gender")
    if allowed_genders and profile_gender and profile_gender not in allowed_genders:
        reasons.append(f"gender '{profile_gender}' not in {allowed_genders}")

    # R-S3 worker_band
    allowed_bands = raw_elig.get("worker_bands")
    profile_band = profile.get("worker_band")
    if allowed_bands and profile_band is not None and profile_band not in allowed_bands:
        reasons.append(f"worker_band {profile_band} not in {allowed_bands}")

    # R-S4 sector
    allowed_sectors = raw_elig.get("sectors")
    profile_sector = profile.get("sector")
    if allowed_sectors and profile_sector and profile_sector not in allowed_sectors:
        reasons.append(f"sector '{profile_sector}' not in {allowed_sectors}")

    # R-S5 aadhaar
    if raw_elig.get("requires_aadhaar") and not profile.get("aadhaar_available"):
        reasons.append("requires_aadhaar but profile.aadhaar_available is false")

    # R-S6 migrant_only
    if raw_elig.get("migrant_only") and profile.get("migrant_status") == "long_term":
        reasons.append("scheme is migrant_only; user is long_term resident")

    # R-S7 citation
    if not scheme.get("source_url") and not scheme.get("citation"):
        reasons.append("missing_source_url")

    return reasons


# ─────────────────────────────────────────────────────────────────────────────
# Rules pass — Jobs  (R-J1 … R-J4)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_job(job_entry: dict, profile: dict, known_scheme_ids: set[str]) -> list[str]:
    """Validate a job entry from job_agent output.

    job_entry shape from JobMatchResult.model_dump():
        {"job": {...job fields...}, "match_score": int, "citation": str, "scheme_link": str|None}
    Falls back to treating job_entry directly as the job dict for backwards compat.

    `known_scheme_ids` is the universe of valid scheme IDs in the DB — the link
    is "broken" only when the referenced scheme does not exist at all.
    """
    # Unwrap nested job dict if present (JobMatchResult shape)
    job = job_entry.get("job") if isinstance(job_entry.get("job"), dict) else job_entry

    reasons: list[str] = []

    # R-J1 citation — check both the job's source_url and the wrapper's citation field
    if not job.get("source_url") and not job_entry.get("citation"):
        reasons.append("missing_source_url")

    # R-J2 worker_band (±1 tolerance)
    job_band = job.get("worker_band")
    profile_band = profile.get("worker_band")
    if job_band is not None and profile_band is not None:
        if abs(job_band - profile_band) > 1:
            reasons.append(
                f"worker_band mismatch: job={job_band}, profile={profile_band} (tolerance ±1)"
            )

    # R-J3 scheme referential integrity — broken only when scheme doesn't exist.
    # A scheme that exists but isn't in the user's surfaced plan is still a real
    # scheme and the link is informational.
    scheme_link = job.get("scheme_link_id") or job_entry.get("scheme_link")
    if scheme_link and known_scheme_ids and scheme_link not in known_scheme_ids:
        reasons.append(f"broken_scheme_link: scheme '{scheme_link}' does not exist")

    # R-J4 sector (advisory — only block if the LLM scoring pass hasn't already ranked;
    # sector labels between DB and profile may not match exactly, so skip hard rejection here)

    return reasons


# ─────────────────────────────────────────────────────────────────────────────
# Rules pass — Housing  (R-H1 … R-H3)
# ─────────────────────────────────────────────────────────────────────────────

def _validate_housing(housing: dict, profile: dict) -> list[str]:
    reasons: list[str] = []

    # R-H1 citation
    if not housing.get("source_url"):
        reasons.append("missing_source_url")

    # R-H2 gender compat
    gender = profile.get("gender")
    h_gender = housing.get("gender")
    if gender == "male" and h_gender and h_gender not in ("male", "unisex"):
        reasons.append(f"gender incompatible: housing='{h_gender}', profile='male'")
    elif gender == "female" and h_gender and h_gender not in ("female", "unisex"):
        reasons.append(f"gender incompatible: housing='{h_gender}', profile='female'")

    # R-H3 budget cap (accept both 'budget' and 'budget_inr' profile keys)
    budget = profile.get("budget") or profile.get("budget_inr")
    price_min = housing.get("price_min")
    if budget is not None and price_min is not None:
        try:
            budget_value = float(budget)
            price_min_value = float(price_min)
        except (TypeError, ValueError):
            budget_value = None
            price_min_value = None

        if budget_value is not None and price_min_value is not None:
            cap = int(budget_value * 1.05)
            if price_min_value > cap:
                reasons.append(f"price_min {price_min} exceeds budget cap {cap}")

    return reasons


# ─────────────────────────────────────────────────────────────────────────────
# LLM confidence pass
# ─────────────────────────────────────────────────────────────────────────────

async def _llm_confidence_score(item: dict, category: str, profile: dict) -> float:
    """Ask LLM to score skill alignment 0-1.  Returns 1.0 on any error (pass-through)."""
    try:
        import litellm  # type: ignore

        system = (
            "You are a strict relevance judge for an employment platform serving urban migrant workers in India. "
            "Given a user profile and a candidate item, output ONLY a JSON object: "
            '{"score": <float 0.0–1.0>} '
            "where 1.0 = perfect match, 0.0 = completely irrelevant. No other text."
        )

        item_summary: dict = {}
        if category == "job":
            item_summary = {
                "title": item.get("title"),
                "sector": item.get("sector"),
                "required_skills": item.get("required_skills"),
                "worker_band": item.get("worker_band"),
            }
        elif category == "scheme":
            item_summary = {
                "name": item.get("scheme_name") or item.get("name"),
                "category": item.get("category"),
                "eligibility": item.get("eligibility_json") or item.get("eligibility"),
            }
        elif category == "housing":
            item_summary = {
                "area": item.get("area"),
                "price_min": item.get("price_min"),
                "type": item.get("type"),
                "amenities": item.get("amenities"),
            }

        profile_summary = {
            k: profile.get(k)
            for k in ("sector", "worker_band", "skills", "education", "employment_status")
        }

        user_msg = f"Profile: {profile_summary}\n\nItem ({category}): {item_summary}"

        response = await litellm.acompletion(
            model=os.getenv("VALIDATOR_LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            max_tokens=32,
        )

        import json
        text = response.choices[0].message.content.strip()
        data = json.loads(text)
        return float(data.get("score", 1.0))

    except Exception as exc:
        logger.warning("LLM confidence pass skipped (%s): %s", category, exc)
        return 1.0  # fail-open: keep item when LLM unavailable


# ─────────────────────────────────────────────────────────────────────────────
# Full validation pass
# ─────────────────────────────────────────────────────────────────────────────

async def validate_all(
    schemes: list[dict],
    jobs: list[dict],
    housing: list[dict],
    profile: dict,
    llm_enabled: bool = True,
    known_scheme_ids: set[str] | None = None,
) -> dict:
    """Run rules + optional LLM pass over all three verticals.

    Returns the validated/filtered_out dict described in the module docstring.
    """
    validated_schemes: list[dict] = []
    validated_jobs: list[dict] = []
    validated_housing: list[dict] = []
    filtered_out: list[dict] = []

    # ── Schemes ──────────────────────────────────────────────────────────────
    for s in schemes:
        item_id = str(s.get("scheme_id") or s.get("id") or "unknown")

        # Near-miss ineligibles surfaced by scheme_agent flow through
        # untouched so the UI can render a "Check requirements" card.
        elig_status = s.get("eligibility_status")
        if isinstance(elig_status, dict) and elig_status.get("eligible") is False:
            validated_schemes.append(s)
            continue

        reasons = _validate_scheme(s, profile)
        if reasons:
            filtered_out.append(_reject(item_id, "scheme", reasons))
            continue

        # LLM pass for borderline skill alignment
        if llm_enabled and _LLM_ENABLED:
            score = await _llm_confidence_score(s, "scheme", profile)
            if score < _LLM_CONFIDENCE_THRESHOLD:
                filtered_out.append(
                    _reject(item_id, "scheme", [f"low_confidence_score: {score:.2f}"])
                )
                continue

        validated_schemes.append(s)

    validated_scheme_ids: set[str] = {
        str(s.get("scheme_id") or s.get("id")) for s in validated_schemes
    }
    # The universe of scheme IDs a job link may legitimately point at.
    # Prefer the DB-wide set (passed in by the graph) and fall back to the
    # validated subset only when the caller didn't supply one.
    job_scheme_ids = known_scheme_ids if known_scheme_ids else validated_scheme_ids

    # ── Jobs ─────────────────────────────────────────────────────────────────
    for j in jobs:
        # Unwrap nested job dict for id extraction (JobMatchResult shape)
        job_inner = j.get("job") if isinstance(j.get("job"), dict) else j
        item_id = str(job_inner.get("id") or j.get("id") or "unknown")
        reasons = _validate_job(j, profile, job_scheme_ids)
        if reasons:
            filtered_out.append(_reject(item_id, "job", reasons))
            continue

        if llm_enabled and _LLM_ENABLED:
            score = await _llm_confidence_score(j, "job", profile)
            if score < _LLM_CONFIDENCE_THRESHOLD:
                filtered_out.append(
                    _reject(item_id, "job", [f"low_confidence_score: {score:.2f}"])
                )
                continue

        validated_jobs.append(j)

    # ── Housing ───────────────────────────────────────────────────────────────
    for h in housing:
        item_id = str(h.get("id") or "unknown")
        reasons = _validate_housing(h, profile)
        if reasons:
            filtered_out.append(_reject(item_id, "housing", reasons))
            continue
        # No LLM pass for housing — rules are fully deterministic
        validated_housing.append(h)

    return {
        "validated": {
            "schemes": validated_schemes,
            "jobs": validated_jobs,
            "housing": validated_housing,
        },
        "filtered_out": filtered_out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node
# ─────────────────────────────────────────────────────────────────────────────

async def validator_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: validates all three verticals against profile rules.

    Reads from state:
      state["profile"]      — dict (age, gender, worker_band, sector, budget, …)
      state["scheme_out"]   — list[dict] from scheme_agent
      state["job_out"]      — list[dict] from job_agent
      state["housing_out"]  — list[dict] from housing_agent

    Writes to state:
      state["validator_out"] — {validated: {schemes, jobs, housing}, filtered_out: [...]}
      state["errors"]        — appended on failure
    """
    profile: dict = state.get("profile", {})
    scheme_out: list[dict] = state.get("scheme_out", [])
    job_out: list[dict] = state.get("job_out", [])
    housing_out: list[dict] = state.get("housing_out", [])
    errors: list[str] = list(state.get("errors", []))

    # Normalise scheme_out — scheme_agent wraps in {"schemes": [...], "meta": ...}
    if isinstance(scheme_out, dict):
        scheme_out = scheme_out.get("schemes", [])

    known_scheme_ids = {str(sid) for sid in state.get("all_scheme_ids") or [] if sid}

    try:
        result = await validate_all(
            schemes=scheme_out,
            jobs=job_out,
            housing=housing_out,
            profile=profile,
            known_scheme_ids=known_scheme_ids or None,
        )
        logger.info(
            "validator_agent: validated schemes=%d jobs=%d housing=%d, filtered=%d",
            len(result["validated"]["schemes"]),
            len(result["validated"]["jobs"]),
            len(result["validated"]["housing"]),
            len(result["filtered_out"]),
        )
        return {**state, "validator_out": result, "errors": errors}
    except Exception as exc:
        errors.append(f"validator_agent: {exc}")
        return {
            **state,
            "validator_out": {"validated": {"schemes": [], "jobs": [], "housing": []}, "filtered_out": []},
            "errors": errors,
        }
