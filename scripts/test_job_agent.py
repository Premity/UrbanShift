"""Test script for T13 — Job Agent.

Usage (from Docker):
    docker compose exec -e PYTHONPATH=/:/app api python /scripts/test_job_agent.py

Requires a running Postgres with seeded jobs_cache data.
"""

from __future__ import annotations

import asyncio
import json
import sys

# ── Demo Personas (from PRD §2) ──────────────────────────

RAVI_PROFILE = {
    "seeker_type": "both",
    "name": "Ravi",
    "age": 28,
    "gender": "male",
    "origin_state": "Bihar",
    "current_city": "Bengaluru",
    "native_lang": "hi",
    "languages_spoken": ["hi", "en"],
    "migrant_status": "just_moved",
    "aadhaar_available": True,
    "sector": "driving",
    "skills": ["driving", "commercial driving", "basic mechanical"],
    "education": "class10",
    "years_experience": 5,
    "employment_status": "unemployed",
    "income_range_inr": None,
    "worker_band": 2,
    "budget_inr": 6000,
    "preferred_areas": [],
    "occupancy_pref": "shared",
    "move_in_window_days": 7,
}

PRIYA_PROFILE = {
    "seeker_type": "both",
    "name": "Priya",
    "age": 23,
    "gender": "female",
    "origin_state": "Telangana",
    "current_city": "Bengaluru",
    "native_lang": "te",
    "languages_spoken": ["te", "en", "hi"],
    "migrant_status": "just_moved",
    "aadhaar_available": True,
    "sector": "bpo",
    "skills": ["customer support", "Excel", "typing"],
    "education": "grad",
    "years_experience": 0,
    "employment_status": "unemployed",
    "income_range_inr": None,
    "worker_band": 4,
    "budget_inr": 12000,
    "preferred_areas": [],
    "occupancy_pref": "single",
    "move_in_window_days": 14,
}

# Mock scheme output with a scheme that has_jobs=True
MOCK_SCHEME_OUT = [
    {
        "id": "pmkvy",
        "name": "PMKVY",
        "has_jobs": True,
        "eligibility_status": "eligible",
        "citation": "https://www.pmkvyofficial.org/",
    },
    {
        "id": "eshram",
        "name": "e-Shram",
        "has_jobs": False,
        "eligibility_status": "eligible",
        "citation": "https://eshram.gov.in/",
    },
]


def print_result(name: str, result: dict, profile: dict) -> None:
    """Pretty-print agent results and check acceptance criteria."""
    jobs = result.get("job_out", [])
    print(f"\n{'='*60}")
    print(f"  Results for {name} ({profile['sector']}, band {profile['worker_band']})")
    print(f"{'='*60}")
    print(f"  Total jobs returned: {len(jobs)}")
    print()

    for i, job_match in enumerate(jobs, 1):
        j = job_match["job"]
        print(f"  [{i}] {j['title']}")
        print(f"      Employer: {j.get('employer', 'N/A')} | Area: {j.get('area', 'N/A')}")
        print(f"      Band: {j.get('worker_band', '?')} | Pay: ₹{j.get('pay_min', '?')}–₹{j.get('pay_max', '?')}")
        print(f"      Score: {job_match['match_score']}/100 — {job_match['match_reason']}")
        if job_match.get("scheme_link"):
            print(f"      🔗 Scheme-linked: {job_match['scheme_link']}")
        print(f"      📎 {job_match['citation']}")
        print()

    # ── Acceptance checks ────────────────────────────────
    passed = True

    if len(jobs) < 3:
        print(f"  ❌ FAIL: Expected ≥3 jobs, got {len(jobs)}")
        passed = False
    else:
        print(f"  ✅ PASS: ≥3 jobs returned ({len(jobs)})")

    if name == "Ravi":
        driving_jobs = [
            j for j in jobs
            if "driv" in (j["job"].get("title", "") + " " + (j["job"].get("sector") or "")).lower()
        ]
        if driving_jobs:
            print(f"  ✅ PASS: ≥1 driving job found ({len(driving_jobs)})")
        else:
            print("  ❌ FAIL: No driving job found for Ravi")
            passed = False

    if name == "Priya":
        bpo_jobs = [
            j for j in jobs
            if any(
                kw in (j["job"].get("title", "") + " " + (j["job"].get("sector") or "")).lower()
                for kw in ["bpo", "customer", "support", "call center", "telecaller"]
            )
        ]
        if bpo_jobs:
            print(f"  ✅ PASS: ≥1 BPO/customer-support job found ({len(bpo_jobs)})")
        else:
            print("  ❌ FAIL: No BPO/customer-support job found for Priya")
            passed = False

    scheme_linked = [j for j in jobs if j.get("scheme_link")]
    if scheme_linked:
        print(f"  ✅ PASS: ≥1 scheme-linked job ({len(scheme_linked)})")
    else:
        print("  ⚠️  WARN: No scheme-linked jobs (may need seed data with scheme_link_id)")

    return passed


async def main() -> None:
    from packages.agents.job_agent import run_job_agent

    all_passed = True

    # Test Ravi
    print("\n🚀 Running Job Agent for Ravi (Band 2, driving)...")
    ravi_state = {"profile": RAVI_PROFILE, "scheme_out": MOCK_SCHEME_OUT}
    ravi_result = await run_job_agent(ravi_state)
    if not print_result("Ravi", ravi_result, RAVI_PROFILE):
        all_passed = False

    # Test Priya
    print("\n🚀 Running Job Agent for Priya (Band 4, BPO)...")
    priya_state = {"profile": PRIYA_PROFILE, "scheme_out": MOCK_SCHEME_OUT}
    priya_result = await run_job_agent(priya_state)
    if not print_result("Priya", priya_result, PRIYA_PROFILE):
        all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("  🎉 All acceptance criteria PASSED!")
    else:
        print("  ⚠️  Some acceptance criteria FAILED — review above.")
    print(f"{'='*60}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
