"""Manual test: validator_agent rules pass.

Run (no live API needed — pure unit execution):
    python scripts/test_validator_agent.py

Covers all acceptance criteria from T15:
    - bad age (scheme age_max=25, profile age=28)  → filtered, correct reason
    - citation missing (scheme source_url=None)    → filtered, reason: missing_source_url
    - broken_scheme_link (job references scheme not in output) → filtered, correct reason
"""
from __future__ import annotations

import asyncio
import sys
import os

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Disable LLM pass so tests are deterministic
os.environ["VALIDATOR_LLM_ENABLED"] = "0"

from packages.agents.validator_agent import validate_all  # noqa: E402

PROFILE = {
    "age": 28,
    "gender": "male",
    "worker_band": 2,
    "sector": "construction",
    "budget_inr": 6000,
    "aadhaar_available": True,
    "migrant_status": "migrant",
}


def _scheme(id: str, **kwargs) -> dict:
    base = {
        "scheme_id": id,
        "scheme_name": f"Scheme {id}",
        "source_url": "https://example.gov/scheme",
        "citation": "https://example.gov/scheme",
        "eligibility_json": {},
        "category": ["welfare"],
    }
    base.update(kwargs)
    return base


def _job(id: str, scheme_link_id: str | None = None, **kwargs) -> dict:
    base = {
        "id": id,
        "title": f"Job {id}",
        "source_url": "https://example.com/job",
        "worker_band": 2,
        "sector": "construction",
        "scheme_link_id": scheme_link_id,
    }
    base.update(kwargs)
    return base


def _housing(id: str, **kwargs) -> dict:
    base = {
        "id": id,
        "name": f"PG {id}",
        "source_url": "https://example.com/pg",
        "gender": "male",
        "price_min": 5000,
    }
    base.update(kwargs)
    return base


async def run_tests() -> None:
    failures: list[str] = []

    # ── T1: scheme with age_max=25, profile age=28  → must be filtered ──────
    bad_age_scheme = _scheme(
        "S-AGE",
        eligibility_json={"age_max": 25},
    )
    good_scheme = _scheme("S-GOOD")

    result = await validate_all(
        schemes=[bad_age_scheme, good_scheme],
        jobs=[],
        housing=[],
        profile=PROFILE,
        llm_enabled=False,
    )

    fo_ids = {f["item_id"] for f in result["filtered_out"]}
    if "S-AGE" not in fo_ids:
        failures.append("T1 FAIL: age-max scheme not filtered")
    else:
        age_reasons = next(f["reasons"] for f in result["filtered_out"] if f["item_id"] == "S-AGE")
        if not any("above maximum" in r for r in age_reasons):
            failures.append(f"T1 FAIL: wrong reason for age filter: {age_reasons}")
        else:
            print("T1 PASS: age_max scheme filtered with correct reason")

    if "S-GOOD" not in {str(s.get("scheme_id") or s.get("id")) for s in result["validated"]["schemes"]}:
        failures.append("T1 FAIL: good scheme incorrectly filtered")

    # ── T2: scheme with missing source_url  → reason: missing_source_url ────
    no_citation = _scheme("S-NOCITE", source_url=None, citation=None)

    result2 = await validate_all(
        schemes=[no_citation],
        jobs=[],
        housing=[],
        profile=PROFILE,
        llm_enabled=False,
    )

    fo2 = result2["filtered_out"]
    if not fo2 or fo2[0]["item_id"] != "S-NOCITE":
        failures.append("T2 FAIL: no-citation scheme not filtered")
    elif not any("missing_source_url" in r for r in fo2[0]["reasons"]):
        failures.append(f"T2 FAIL: wrong reason: {fo2[0]['reasons']}")
    else:
        print("T2 PASS: missing_source_url scheme filtered with correct reason")

    # ── T3: job referencing scheme not in validated output  → broken_scheme_link
    orphan_job = _job("J-ORPHAN", scheme_link_id="S-DOES-NOT-EXIST")
    linked_job = _job("J-LINKED", scheme_link_id="S-GOOD2")
    anchor_scheme = _scheme("S-GOOD2")

    result3 = await validate_all(
        schemes=[anchor_scheme],
        jobs=[orphan_job, linked_job],
        housing=[],
        profile=PROFILE,
        llm_enabled=False,
    )

    fo3_ids = {f["item_id"] for f in result3["filtered_out"]}
    if "J-ORPHAN" not in fo3_ids:
        failures.append("T3 FAIL: orphan job (broken_scheme_link) not filtered")
    else:
        orphan_reasons = next(
            f["reasons"] for f in result3["filtered_out"] if f["item_id"] == "J-ORPHAN"
        )
        if not any("broken_scheme_link" in r for r in orphan_reasons):
            failures.append(f"T3 FAIL: wrong reason for orphan job: {orphan_reasons}")
        else:
            print("T3 PASS: broken_scheme_link job filtered with correct reason")

    if "J-LINKED" in fo3_ids:
        failures.append("T3 FAIL: linked job incorrectly filtered")
    else:
        print("T3 PASS: linked job retained")

    # ── T4: housing gender incompatible  → filtered ──────────────────────────
    female_only = _housing("H-FEMALE", gender="female")
    unisex = _housing("H-UNISEX", gender="unisex")

    result4 = await validate_all(
        schemes=[],
        jobs=[],
        housing=[female_only, unisex],
        profile=PROFILE,  # profile.gender = "male"
        llm_enabled=False,
    )

    fo4_ids = {f["item_id"] for f in result4["filtered_out"]}
    if "H-FEMALE" not in fo4_ids:
        failures.append("T4 FAIL: female-only housing not filtered for male profile")
    else:
        print("T4 PASS: female-only housing filtered for male profile")

    if "H-UNISEX" in fo4_ids:
        failures.append("T4 FAIL: unisex housing incorrectly filtered")
    else:
        print("T4 PASS: unisex housing retained for male profile")

    # ── T5: housing over budget cap  → filtered ──────────────────────────────
    over_budget = _housing("H-OVER", price_min=7000)  # 7000 > 6000*1.05=6300

    result5 = await validate_all(
        schemes=[],
        jobs=[],
        housing=[over_budget],
        profile=PROFILE,
        llm_enabled=False,
    )

    if not result5["filtered_out"] or result5["filtered_out"][0]["item_id"] != "H-OVER":
        failures.append("T5 FAIL: over-budget housing not filtered")
    else:
        print("T5 PASS: over-budget housing filtered")

    # ── Summary ──────────────────────────────────────────────────────────────
    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("All validator_agent tests passed.")


if __name__ == "__main__":
    asyncio.run(run_tests())
