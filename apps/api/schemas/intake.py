"""Pydantic schemas for the intake chat endpoints (§7.3)."""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────

class IntakeAnswer(BaseModel):
    """A single user answer submitted during an intake turn."""
    field: str
    value: Any  # str | list[str] | int | bool | tuple[int, int]


class IntakeTurnRequest(BaseModel):
    """Request body for POST /api/intake/turn."""
    session_id: Optional[uuid.UUID] = None
    answer: Optional[IntakeAnswer] = None  # None for the very first turn


# ── Response ─────────────────────────────────────────────

class TurnDefinition(BaseModel):
    """Describes the next question the frontend should render."""
    field: str
    prompt_i18n: dict[str, str]  # {"en": "...", "hi": "...", "kn": "..."}
    input_type: Literal["text", "chips", "multi", "slider", "range", "date"]
    options: list[str] = Field(default_factory=list)
    allow_free_text: bool = False
    multi_select: bool = False


class IntakeTurnResponse(BaseModel):
    """Response body for POST /api/intake/turn."""
    complete: bool = False
    turn: Optional[TurnDefinition] = None
    current_profile: dict[str, Any] = Field(default_factory=dict)


# ── Profile Schema (§5.4) ───────────────────────────────

class ProfileSchema(BaseModel):
    """Full profile schema matching PRD §5.4.

    Used by POST /api/intake/finalize to return the complete
    validated profile for the confirm screen.
    """
    seeker_type: Literal["job", "housing", "both"]
    name: Optional[str] = None
    age: int = 0
    gender: Literal["male", "female", "other", "prefer_not"] = "prefer_not"
    origin_state: str = ""
    current_city: Literal["Bengaluru"] = "Bengaluru"
    native_lang: str = ""
    languages_spoken: list[str] = Field(default_factory=list)
    migrant_status: Literal["just_moved", "planning", "long_term"] = "just_moved"
    aadhaar_available: bool = False

    # Work
    sector: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: Literal[
        "none", "primary", "class10", "class12", "diploma", "grad", "postgrad"
    ] = "none"
    years_experience: int = 0
    employment_status: Literal[
        "unemployed", "employed", "underemployed", "student"
    ] = "unemployed"
    income_range_inr: Optional[list[int]] = None
    worker_band: int = 1  # auto-derived

    # Housing (only when seeker_type != "job")
    budget_inr: Optional[int] = None
    preferred_areas: list[str] = Field(default_factory=list)
    occupancy_pref: Optional[Literal["single", "shared", "dorm", "any"]] = None
    move_in_window_days: Optional[int] = None


class IntakeFinalizeResponse(BaseModel):
    """Response body for POST /api/intake/finalize."""
    profile: ProfileSchema
    session_id: uuid.UUID
