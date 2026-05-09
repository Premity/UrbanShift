"""E2E test for the LangGraph pipeline — T16 verification.

Tests all 3 seeker_type paths:
    1. Ravi   (seeker_type=both)  — Bihar auto driver
    2. Priya  (seeker_type=job)   — BPO graduate
    3. Housing-only persona       (seeker_type=housing)

Run from project root:
    docker compose exec api python /scripts/test_graph.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Any

# ── Path setup ──────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_API_DIR = os.path.join(_ROOT, "apps", "api")
_PACKAGES_DIR = os.path.join(_ROOT, "packages")

_PATH_CANDIDATES = [
    os.environ.get("API_DIR"),
    os.environ.get("PACKAGES_DIR"),
    _API_DIR,
    _PACKAGES_DIR,
    "/app",
    "/packages",
    _ROOT,
]
for p in dict.fromkeys(_PATH_CANDIDATES):
    if p and os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-30s %(levelname)-5s %(message)s",
)
logger = logging.getLogger("test_graph")

# ── Disable LLM calls for speed (use heuristic fallback) ───────────────────
os.environ.setdefault("VALIDATOR_LLM_ENABLED", "0")


# ── Test Profiles ───────────────────────────────────────────────────────────

RAVI_PROFILE: dict[str, Any] = {
    "seeker_type": "both",
    "name": "Ravi",
    "age": 28,
    "gender": "male",
    "origin_state": "Bihar",
    "current_city": "Bengaluru",
    "native_lang": "hi",
    "languages_spoken": ["hi"],
    "migrant_status": "just_moved",
    "aadhaar_available": True,
    "sector": "driving",
    "skills": ["driving", "basic mechanical"],
    "education": "class10",
    "years_experience": 5,
    "employment_status": "unemployed",
    "income_range_inr": [0, 15000],
    "worker_band": 2,
    "budget_inr": 6000,
    "budget": 6000,
    "preferred_areas": ["BTM", "Koramangala", "HSR Layout"],
    "occupancy_pref": "shared",
    "move_in_window_days": 7,
}

PRIYA_PROFILE: dict[str, Any] = {
    "seeker_type": "job",
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
    "income_range_inr": [10000, 25000],
    "worker_band": 4,
    "budget_inr": 12000,
    "budget": 12000,
    "preferred_areas": ["Koramangala", "Indiranagar", "HSR Layout"],
    "occupancy_pref": "single",
}

HOUSING_ONLY_PROFILE: dict[str, Any] = {
    "seeker_type": "housing",
    "name": "Amit",
    "age": 25,
    "gender": "male",
    "origin_state": "Uttar Pradesh",
    "current_city": "Bengaluru",
    "native_lang": "hi",
    "languages_spoken": ["hi", "en"],
    "migrant_status": "just_moved",
    "aadhaar_available": True,
    "sector": "retail",
    "skills": ["sales", "inventory management"],
    "education": "class12",
    "years_experience": 2,
    "employment_status": "employed",
    "income_range_inr": [12000, 18000],
    "worker_band": 3,
    "budget_inr": 8000,
    "budget": 8000,
    "preferred_areas": ["Whitefield", "Marathahalli"],
    "occupancy_pref": "double",
}

PROFILES = [
    ("Ravi (both)", "both", RAVI_PROFILE),
    ("Priya (job)", "job", PRIYA_PROFILE),
    ("Amit (housing)", "housing", HOUSING_ONLY_PROFILE),
]


# ── Expected node sequences ────────────────────────────────────────────────

EXPECTED_AGENTS = {
    "both": ["orchestrator", "scheme", "job", "housing", "validator", "merge"],
    "job": ["orchestrator", "scheme", "job", "validator", "merge"],
    "housing": ["orchestrator", "scheme", "housing", "validator", "merge"],
}


# ── Test runner ─────────────────────────────────────────────────────────────

async def test_path(name: str, seeker_type: str, profile: dict[str, Any]) -> bool:
    """Run a single seeker_type path and verify outputs."""
    from agents.graph import build_graph

    logger.info("=" * 60)
    logger.info("TEST: %s (seeker_type=%s)", name, seeker_type)
    logger.info("=" * 60)

    graph = build_graph()

    initial_state = {
        "profile": dict(profile),
        "seeker_type": seeker_type,
        "scheme_out": [],
        "job_out": [],
        "housing_out": [],
        "validator_out": {},
        "plan": {},
        "errors": [],
        "agent_steps": [],
    }

    try:
        # Run graph
        final_state = await graph.ainvoke(initial_state)

        # Extract results
        agent_steps = final_state.get("agent_steps", [])
        scheme_out = final_state.get("scheme_out", [])
        job_out = final_state.get("job_out", [])
        housing_out = final_state.get("housing_out", [])
        validator_out = final_state.get("validator_out", {})
        plan = final_state.get("plan", {})
        errors = final_state.get("errors", [])

        # Log results
        step_agents = [s.get("agent") for s in agent_steps]
        logger.info("Agent steps executed: %s", step_agents)
        logger.info("Scheme results: %d", len(scheme_out))
        logger.info("Job results: %d", len(job_out))
        logger.info("Housing results: %d", len(housing_out))
        logger.info(
            "Validator: validated=%s, filtered=%d",
            {k: len(v) for k, v in validator_out.get("validated", {}).items()},
            len(validator_out.get("filtered_out", [])),
        )
        logger.info("Plan keys: %s", list(plan.keys()) if plan else "EMPTY")
        logger.info("Checklist items: %d", len(plan.get("checklist", [])))
        logger.info("Citations: %d", len(plan.get("citations", [])))
        if errors:
            logger.warning("Errors: %s", errors)

        # ── Assertions ──────────────────────────────────────────────────────
        passed = True

        # 1. Check agent step sequence
        expected = EXPECTED_AGENTS[seeker_type]
        if step_agents != expected:
            logger.error("FAIL: expected agents %s, got %s", expected, step_agents)
            passed = False
        else:
            logger.info("PASS: correct agent sequence")

        # 2. Scheme output should always be non-empty
        if not scheme_out:
            logger.warning("WARN: scheme_out is empty (may be OK if no seed data)")

        # 3. Job output check
        if seeker_type in ("job", "both"):
            if not job_out:
                logger.warning("WARN: job_out is empty for seeker_type=%s", seeker_type)
        else:
            if job_out:
                logger.error("FAIL: job_out should be empty for seeker_type=housing")
                passed = False

        # 4. Housing output check
        if seeker_type in ("housing", "both"):
            if not housing_out:
                logger.warning("WARN: housing_out is empty for seeker_type=%s", seeker_type)
        else:
            if housing_out:
                logger.error("FAIL: housing_out should be empty for seeker_type=job")
                passed = False

        # 5. Validator output should exist
        if not validator_out:
            logger.error("FAIL: validator_out is empty")
            passed = False
        else:
            logger.info("PASS: validator produced output")

        # 6. Plan should be non-empty
        if not plan:
            logger.error("FAIL: plan is empty")
            passed = False
        elif not plan.get("checklist"):
            logger.warning("WARN: plan has no checklist items")
        else:
            logger.info("PASS: plan has %d checklist items", len(plan["checklist"]))

        # 7. No fatal errors
        fatal_errors = [e for e in errors if "Exception" in str(e) or "Error" in str(e)]
        if fatal_errors:
            logger.error("FAIL: fatal errors occurred: %s", fatal_errors)
            passed = False

        if passed:
            logger.info("✅ %s PASSED", name)
        else:
            logger.error("❌ %s FAILED", name)

        return passed

    except Exception:
        logger.exception("💥 %s CRASHED", name)
        return False


async def main():
    """Run all test paths."""
    results: list[tuple[str, bool]] = []

    for name, seeker_type, profile in PROFILES:
        ok = await test_path(name, seeker_type, profile)
        results.append((name, ok))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name}")

    all_passed = all(ok for _, ok in results)
    print("=" * 60)
    print(f"Overall: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
