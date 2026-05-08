"""Intake turn engine — deterministic field sequence with i18n prompts.

The engine walks through a fixed sequence of intake fields based on
``seeker_type``.  Each turn defines the question (with EN/HI/KN translations),
input type, options, and validation rules.  The LLM layer is optional — if an
API key is available, prompts can be made conversational; otherwise the
hardcoded ``prompt_i18n`` strings are used directly.

Worker band is auto-derived via ``derive_worker_band()``.
"""

from __future__ import annotations

from typing import Any, Optional

from schemas.intake import TurnDefinition


# ── Bengaluru Areas (for housing preference chips) ───────

BENGALURU_AREAS = [
    "Whitefield",
    "HSR Layout",
    "Marathahalli",
    "Electronic City",
    "BTM Layout",
    "Koramangala",
    "Indiranagar",
    "Hebbal",
    "Jayanagar",
    "Yelahanka",
]

# ── Indian States (ISO codes for origin_state) ──────────

INDIAN_STATES = [
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "GA",
    "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH",
    "ML", "MN", "MP", "MZ", "NL", "OD", "PB", "PY", "RJ", "SK",
    "TN", "TR", "TS", "UK", "UP", "WB",
]

# ── Languages ────────────────────────────────────────────

LANGUAGES = ["hi", "en", "kn"]

# ── Sectors ──────────────────────────────────────────────

SECTORS = [
    "driving", "delivery", "construction", "domestic_work",
    "retail", "hospitality", "manufacturing", "security",
    "bpo", "data_entry", "admin", "other",
]

# ── Turn Sequence ────────────────────────────────────────
# Each turn is a dict with metadata.  The ``condition`` key (if present)
# is a callable that receives the current profile and returns True if
# the turn should be presented.

TURN_SEQUENCE: list[dict[str, Any]] = [
    # ── Turn 1: Language ─────────────────────────────────
    {
        "fields": ["native_lang", "languages_spoken"],
        "turn": TurnDefinition(
            field="native_lang",
            prompt_i18n={
                "en": "What is your native language? And which other languages do you speak?",
                "hi": "आपकी मातृभाषा क्या है? और आप कौन-कौन सी भाषाएँ बोलते हैं?",
                "kn": "ನಿಮ್ಮ ಮಾತೃಭಾಷೆ ಯಾವುದು? ಮತ್ತು ನೀವು ಯಾವ ಇತರ ಭಾಷೆಗಳನ್ನು ಮಾತನಾಡುತ್ತೀರಿ?",
            },
            input_type="multi",
            options=LANGUAGES,
            allow_free_text=False,
            multi_select=True,
        ),
    },
    # ── Turn 2: Origin + Migration ───────────────────────
    {
        "fields": ["origin_state", "migrant_status"],
        "turn": TurnDefinition(
            field="origin_state",
            prompt_i18n={
                "en": "Which state are you from? And what's your current situation — just moved, planning to move, or been here a while?",
                "hi": "आप किस राज्य से हैं? और आपकी वर्तमान स्थिति क्या है — अभी आए हैं, आने की योजना है, या काफी समय से यहाँ हैं?",
                "kn": "ನೀವು ಯಾವ ರಾಜ್ಯದಿಂದ ಬಂದಿದ್ದೀರಿ? ಮತ್ತು ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಪರಿಸ್ಥಿತಿ ಏನು — ಈಗಷ್ಟೇ ಬಂದಿದ್ದೀರಾ, ಬರಲು ಯೋಜಿಸುತ್ತಿದ್ದೀರಾ, ಅಥವಾ ಬಹಳ ಸಮಯದಿಂದ ಇಲ್ಲಿ ಇದ್ದೀರಾ?",
            },
            input_type="chips",
            options=INDIAN_STATES,
            allow_free_text=False,
            multi_select=False,
        ),
    },
    # ── Turn 3: Age + Gender ─────────────────────────────
    {
        "fields": ["age", "gender"],
        "turn": TurnDefinition(
            field="age",
            prompt_i18n={
                "en": "How old are you? And what's your gender?",
                "hi": "आपकी उम्र कितनी है? और आपका लिंग क्या है?",
                "kn": "ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು? ಮತ್ತು ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು?",
            },
            input_type="chips",
            options=["male", "female", "other", "prefer_not"],
            allow_free_text=True,  # age is free-text, gender is chips
            multi_select=False,
        ),
    },
    # ── Turn 4: Sector + Skills ──────────────────────────
    {
        "fields": ["sector", "skills"],
        "turn": TurnDefinition(
            field="sector",
            prompt_i18n={
                "en": "What kind of work are you looking for? You can also mention specific skills.",
                "hi": "आप किस तरह का काम ढूंढ रहे हैं? आप अपने विशेष कौशल भी बता सकते हैं।",
                "kn": "ನೀವು ಯಾವ ರೀತಿಯ ಕೆಲಸ ಹುಡುಕುತ್ತಿದ್ದೀರಿ? ನಿಮ್ಮ ನಿರ್ದಿಷ್ಟ ಕೌಶಲ್ಯಗಳನ್ನೂ ಹೇಳಬಹುದು.",
            },
            input_type="chips",
            options=SECTORS,
            allow_free_text=True,  # free-text for skills
            multi_select=False,
        ),
    },
    # ── Turn 5: Education + Experience ───────────────────
    {
        "fields": ["education", "years_experience"],
        "turn": TurnDefinition(
            field="education",
            prompt_i18n={
                "en": "What's your highest education? And how many years of work experience do you have?",
                "hi": "आपकी सबसे ऊँची शिक्षा क्या है? और आपके पास कितने साल का अनुभव है?",
                "kn": "ನಿಮ್ಮ ಅತ್ಯುನ್ನತ ಶಿಕ್ಷಣ ಏನು? ಮತ್ತು ನಿಮಗೆ ಎಷ್ಟು ವರ್ಷಗಳ ಕೆಲಸದ ಅನುಭವ ಇದೆ?",
            },
            input_type="chips",
            options=["none", "primary", "class10", "class12", "diploma", "grad", "postgrad"],
            allow_free_text=True,  # free-text for years
            multi_select=False,
        ),
    },
    # ── Turn 6: Employment + Income ──────────────────────
    {
        "fields": ["employment_status", "income_range_inr"],
        "turn": TurnDefinition(
            field="employment_status",
            prompt_i18n={
                "en": "What's your current employment status? And what's your monthly income range (if any)?",
                "hi": "आपकी वर्तमान रोजगार स्थिति क्या है? और आपकी मासिक आय सीमा क्या है (यदि कोई हो)?",
                "kn": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಉದ್ಯೋಗ ಸ್ಥಿತಿ ಏನು? ಮತ್ತು ನಿಮ್ಮ ಮಾಸಿಕ ಆದಾಯ ವ್ಯಾಪ್ತಿ ಎಷ್ಟು (ಯಾವುದಾದರೂ ಇದ್ದರೆ)?",
            },
            input_type="chips",
            options=["unemployed", "employed", "underemployed", "student"],
            allow_free_text=True,  # free-text for income
            multi_select=False,
        ),
    },
    # ── Turn 7: Housing Preferences (conditional) ────────
    {
        "fields": ["budget_inr", "preferred_areas", "occupancy_pref"],
        "condition": lambda profile: profile.get("seeker_type") != "job",
        "turn": TurnDefinition(
            field="budget_inr",
            prompt_i18n={
                "en": "What's your monthly budget for housing (₹)? Which areas do you prefer? And do you want a single room, shared, dorm, or any?",
                "hi": "आवास के लिए आपका मासिक बजट क्या है (₹)? आप कौन से इलाके पसंद करते हैं? और क्या आप सिंगल, शेयर्ड, डॉर्म या कोई भी कमरा चाहते हैं?",
                "kn": "ವಸತಿಗಾಗಿ ನಿಮ್ಮ ಮಾಸಿಕ ಬಜೆಟ್ ಎಷ್ಟು (₹)? ನೀವು ಯಾವ ಪ್ರದೇಶಗಳನ್ನು ಬಯಸುತ್ತೀರಿ? ಮತ್ತು ಸಿಂಗಲ್, ಶೇರ್ಡ್, ಡಾರ್ಮ್, ಅಥವಾ ಯಾವುದಾದರೂ ಬೇಕೇ?",
            },
            input_type="multi",
            options=BENGALURU_AREAS,
            allow_free_text=True,  # free-text for budget
            multi_select=True,
        ),
    },
    # ── Turn 8: Aadhaar ──────────────────────────────────
    {
        "fields": ["aadhaar_available"],
        "turn": TurnDefinition(
            field="aadhaar_available",
            prompt_i18n={
                "en": "Do you have an Aadhaar card?",
                "hi": "क्या आपके पास आधार कार्ड है?",
                "kn": "ನಿಮ್ಮ ಬಳಿ ಆಧಾರ್ ಕಾರ್ಡ್ ಇದೆಯೇ?",
            },
            input_type="chips",
            options=["yes", "no"],
            allow_free_text=False,
            multi_select=False,
        ),
    },
]


def get_completed_fields(profile: dict[str, Any]) -> set[str]:
    """Return the set of fields that have been populated in the profile."""
    completed = set()
    for key, value in profile.items():
        if key in ("seeker_type", "current_city"):
            # These are pre-populated, don't count as "completed turns"
            continue
        if value is not None and value != "" and value != []:
            completed.add(key)
    return completed


def get_next_turn(
    profile: dict[str, Any],
    current_step: int,
) -> tuple[Optional[TurnDefinition], int]:
    """Determine the next turn to present.

    Returns ``(turn_definition, new_step_index)`` or ``(None, step)`` when
    the intake is complete.
    """
    step = current_step
    while step < len(TURN_SEQUENCE):
        turn_def = TURN_SEQUENCE[step]

        # Check conditional turns (e.g. housing prefs only if seeker_type != job)
        condition = turn_def.get("condition")
        if condition is not None and not condition(profile):
            step += 1
            continue

        # Check if all fields for this turn are already populated
        fields = turn_def["fields"]
        completed = get_completed_fields(profile)
        if all(f in completed for f in fields):
            step += 1
            continue

        return turn_def["turn"], step

    return None, step


def apply_answer(
    profile: dict[str, Any],
    answer_field: str,
    answer_value: Any,
    current_step: int,
) -> dict[str, Any]:
    """Merge a user answer into the running profile.

    Handles the combined-turn pattern where one answer payload may
    contain data for multiple fields (e.g. ``age`` + ``gender``).
    """
    if current_step >= len(TURN_SEQUENCE):
        return profile

    turn_def = TURN_SEQUENCE[current_step]
    expected_field = turn_def["turn"].field
    if answer_field != expected_field:
        raise ValueError(
            f"Mismatched answer field. Expected '{expected_field}', got '{answer_field}'."
        )

    fields = turn_def["fields"]

    # The answer_value can be a dict with multiple fields or a single value
    if isinstance(answer_value, dict):
        for field in fields:
            if field in answer_value:
                profile[field] = _normalize_value(field, answer_value[field])
    else:
        # Single value — apply to the primary field
        primary_field = fields[0]
        profile[primary_field] = _normalize_value(primary_field, answer_value)

    return profile


def _normalize_value(field: str, value: Any) -> Any:
    """Normalize values to match the Profile schema."""
    if field == "age":
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    if field == "years_experience":
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    if field == "budget_inr":
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if field == "aadhaar_available":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("yes", "true", "1", "haan", "ha", "haa")
    if field == "income_range_inr":
        if isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                return [int(value[0]), int(value[1])]
            except (ValueError, TypeError):
                return None
        return None
    if field in ("languages_spoken", "preferred_areas", "skills"):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return []
    return value


# ── Worker Band Derivation ───────────────────────────────

# Worker band mapping (from PRD §1.3 + §6.1):
#   Band 1: unskilled (construction, labor, helper, cleaner)
#   Band 2: service/gig (driving, delivery, courier)
#   Band 3: semi-skilled (retail, hospitality, manufacturing, security)
#   Band 4: entry white-collar (BPO, admin, data entry, office)

SECTOR_BAND_MAP: dict[str, int] = {
    "construction": 1,
    "domestic_work": 1,
    "driving": 2,
    "delivery": 2,
    "retail": 3,
    "hospitality": 3,
    "manufacturing": 3,
    "security": 3,
    "bpo": 4,
    "data_entry": 4,
    "admin": 4,
    "other": 2,
}

EDUCATION_BAND_BOOST: dict[str, int] = {
    "none": 0,
    "primary": 0,
    "class10": 0,
    "class12": 0,
    "diploma": 1,
    "grad": 1,
    "postgrad": 2,
}


def derive_worker_band(profile: dict[str, Any]) -> int:
    """Auto-derive worker band (1-4) from sector + education + employment.

    Algorithm:
    - Start from sector-based band.
    - Boost by education level (diploma/grad → +1, postgrad → +2).
    - Clamp to 1-4 range.
    """
    sector = profile.get("sector", "other")
    education = profile.get("education", "none")
    employment = profile.get("employment_status", "unemployed")

    base_band = SECTOR_BAND_MAP.get(sector, 2)
    edu_boost = EDUCATION_BAND_BOOST.get(education, 0)

    band = base_band + edu_boost

    # Students with grad+ education get band 4
    if employment == "student" and education in ("grad", "postgrad"):
        band = max(band, 4)

    return max(1, min(4, band))


def build_finalized_profile(
    profile: dict[str, Any],
    seeker_type: str,
) -> dict[str, Any]:
    """Build the complete profile dict with derived fields."""
    profile["seeker_type"] = seeker_type
    profile["current_city"] = "Bengaluru"
    profile["worker_band"] = derive_worker_band(profile)

    # Ensure all expected fields have defaults
    defaults = {
        "name": None,
        "age": 0,
        "gender": "prefer_not",
        "origin_state": "",
        "native_lang": "",
        "languages_spoken": [],
        "migrant_status": "just_moved",
        "aadhaar_available": False,
        "sector": None,
        "skills": [],
        "education": "none",
        "years_experience": 0,
        "employment_status": "unemployed",
        "income_range_inr": None,
        "budget_inr": None,
        "preferred_areas": [],
        "occupancy_pref": None,
        "move_in_window_days": None,
    }

    for key, default in defaults.items():
        if key not in profile:
            profile[key] = default

    return profile
