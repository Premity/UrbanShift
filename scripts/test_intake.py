"""Extended tests: job-only path + Priya persona (band 4)."""
import requests

BASE = "http://localhost:8000"

def run_intake(persona_name, seeker_type, answers, expected_band):
    s = requests.Session()
    
    # Create session
    r = s.post(f"{BASE}/api/session/start", json={"lang_pref": "en"})
    assert r.status_code == 200, f"Session failed: {r.text}"
    sid = r.json()["session_id"]
    
    # Set seeker_type by creating profile first
    # The intake engine uses profile_json.seeker_type for conditional routing
    # First turn creates the profile with default seeker_type
    r = s.post(f"{BASE}/api/intake/turn", json={"session_id": sid})
    assert r.status_code == 200
    
    # Manually set seeker_type in the profile via the profile endpoint
    r = s.post(f"{BASE}/api/profile", json={
        "seeker_type": seeker_type,
        "profile_json": {"seeker_type": seeker_type, "current_city": "Bengaluru", "_intake_step": 0}
    })
    assert r.status_code == 200, f"Profile update failed: {r.text}"
    
    # Now re-fetch first turn
    r = s.post(f"{BASE}/api/intake/turn", json={"session_id": sid})
    assert r.status_code == 200
    
    turn_count = 0
    for answer in answers:
        r = s.post(f"{BASE}/api/intake/turn", json={
            "session_id": sid,
            "answer": answer
        })
        assert r.status_code == 200, f"Turn failed: {r.text}"
        d = r.json()
        turn_count += 1
        if d["complete"]:
            break
    
    # Finalize
    r = s.post(f"{BASE}/api/intake/finalize")
    assert r.status_code == 200, f"Finalize failed: {r.text}"
    profile = r.json()["profile"]
    
    actual_band = profile["worker_band"]
    status = "✅" if actual_band == expected_band else "❌"
    print(f"{status} {persona_name}: {turn_count} turns, worker_band={actual_band} (expected {expected_band}), seeker_type={seeker_type}")
    
    if actual_band != expected_band:
        print(f"   Profile: sector={profile.get('sector')}, education={profile.get('education')}, employment={profile.get('employment_status')}")
    
    return actual_band == expected_band


if __name__ == "__main__":
    # ── Test 1: Ravi (band 2, seeker_type=both) ──────────────
    ok1 = run_intake("Ravi (both)", "both", [
        {"field": "native_lang", "value": {"native_lang": "hi", "languages_spoken": ["hi", "en"]}},
        {"field": "origin_state", "value": {"origin_state": "Bihar", "migrant_status": "just_moved"}},
        {"field": "age", "value": {"age": 28, "gender": "male"}},
        {"field": "sector", "value": {"sector": "driving", "skills": ["driving", "basic mechanical"]}},
        {"field": "education", "value": {"education": "class10", "years_experience": 5}},
        {"field": "employment_status", "value": {"employment_status": "unemployed", "income_range_inr": [0, 0]}},
        {"field": "budget_inr", "value": {"budget_inr": 6000, "preferred_areas": ["Whitefield"], "occupancy_pref": "shared"}},
        {"field": "aadhaar_available", "value": "yes"},
    ], expected_band=2)

    # ── Test 2: Ravi (band 2, seeker_type=job — skip housing) ─
    ok2 = run_intake("Ravi (job-only)", "job", [
        {"field": "native_lang", "value": {"native_lang": "hi", "languages_spoken": ["hi"]}},
        {"field": "origin_state", "value": {"origin_state": "Bihar", "migrant_status": "just_moved"}},
        {"field": "age", "value": {"age": 28, "gender": "male"}},
        {"field": "sector", "value": {"sector": "driving", "skills": ["driving"]}},
        {"field": "education", "value": {"education": "class10", "years_experience": 5}},
        {"field": "employment_status", "value": {"employment_status": "unemployed", "income_range_inr": [0, 0]}},
        {"field": "aadhaar_available", "value": "yes"},
    ], expected_band=2)

    # ── Test 3: Priya (band 4, seeker_type=both) ─────────────
    ok3 = run_intake("Priya (both)", "both", [
        {"field": "native_lang", "value": {"native_lang": "te", "languages_spoken": ["te", "en", "hi"]}},
        {"field": "origin_state", "value": {"origin_state": "Telangana", "migrant_status": "planning"}},
        {"field": "age", "value": {"age": 23, "gender": "female"}},
        {"field": "sector", "value": {"sector": "bpo", "skills": ["customer support", "Excel", "typing"]}},
        {"field": "education", "value": {"education": "grad", "years_experience": 0}},
        {"field": "employment_status", "value": {"employment_status": "unemployed", "income_range_inr": [0, 0]}},
        {"field": "budget_inr", "value": {"budget_inr": 12000, "preferred_areas": ["Koramangala", "HSR Layout"], "occupancy_pref": "single"}},
        {"field": "aadhaar_available", "value": "yes"},
    ], expected_band=4)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{'='*50}")
    all_ok = ok1 and ok2 and ok3
    print(f"{'✅ All tests passed!' if all_ok else '❌ Some tests failed.'}")
