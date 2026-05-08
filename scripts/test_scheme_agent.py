"""T12 Scheme Agent — offline test (no Docker/API needed).

Run: python3 scripts/test_scheme_agent.py
"""
import json
import sys
import asyncio
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.agents.scheme_agent import run_scheme_agent

# Load seed data directly from JSON
SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "seed", "schemes.json")

RAVI = {
    "seeker_type": "both", "age": 28, "gender": "male",
    "origin_state": "BR", "current_city": "Bengaluru",
    "sector": "driving", "skills": ["driving", "basic mechanical"],
    "education": "class10", "worker_band": 2,
    "employment_status": "unemployed", "aadhaar_available": True,
    "migrant_status": "just_moved", "budget_inr": 6000,
    "income_range_inr": [0, 0],
}

PRIYA = {
    "seeker_type": "both", "age": 23, "gender": "female",
    "origin_state": "TS", "current_city": "Bengaluru",
    "sector": "bpo", "skills": ["customer support", "Excel", "typing"],
    "education": "grad", "worker_band": 4,
    "employment_status": "unemployed", "aadhaar_available": True,
    "migrant_status": "planning", "budget_inr": 12000,
    "income_range_inr": [0, 0],
}


async def test_persona(name, profile, expected_min, must_include_ids, must_have_jobs):
    schemes = json.load(open(SEED))
    result = await run_scheme_agent(schemes, profile, profile["seeker_type"])

    matched = result["schemes"]
    ids = [s["scheme_id"] for s in matched]

    print(f"\n{'='*60}")
    print(f"  {name} — worker_band={profile['worker_band']}, sector={profile['sector']}")
    print(f"{'='*60}")
    print(f"  Meta: {json.dumps(result['meta'])}")
    print()

    for s in matched:
        tags = []
        if s["scheme_id"] in must_include_ids:
            tags.append("⭐ REQUIRED")
        if s["has_jobs"]:
            tags.append("🎯 has_jobs")
        tag_str = f"  [{', '.join(tags)}]" if tags else ""
        print(f"  {s['scheme_id']}: {s['scheme_name']}{tag_str}")
        print(f"    reasons: {s['eligibility_status']['reasons'][:2]}")
        print(f"    citation: {s['citation'][:70]}")
    print()

    # Checks
    ok_count = len(matched) >= expected_min
    ok_ids = all(mid in ids for mid in must_include_ids)
    ok_jobs = any(s["has_jobs"] for s in matched) if must_have_jobs else True
    ok_cite = all(s["citation"] for s in matched)

    checks = [
        (f"≥{expected_min} eligible schemes ({len(matched)})", ok_count),
        (f"includes {must_include_ids}", ok_ids),
        (f"has_jobs scheme present", ok_jobs),
        (f"all have citations", ok_cite),
    ]

    all_ok = True
    for label, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {label}")
        if not passed:
            all_ok = False

    return all_ok


async def main():
    ok1 = await test_persona(
        "Ravi (band 2, driving)", RAVI,
        expected_min=3,
        must_include_ids=["eshram"],
        must_have_jobs=True,
    )
    ok2 = await test_persona(
        "Priya (band 4, BPO)", PRIYA,
        expected_min=3,
        must_include_ids=["ncs-portal"],  # e-Shram excludes band 4; NCS covers all bands
        must_have_jobs=False,
    )

    print(f"\n{'='*60}")
    if ok1 and ok2:
        print("  ✅ ALL T12 ACCEPTANCE CHECKS PASSED")
    else:
        print("  ❌ SOME CHECKS FAILED")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
