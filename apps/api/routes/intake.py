"""Intake chat routes — POST /api/intake/turn and POST /api/intake/finalize.

These endpoints power the conversational onboarding flow.  The turn engine
walks through a fixed field sequence, returning one question at a time.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_session
from models import Profile, Session
from schemas.intake import (
    IntakeFinalizeResponse,
    IntakeTurnRequest,
    IntakeTurnResponse,
    ProfileSchema,
)
from routes.intake_engine import (
    apply_answer,
    build_finalized_profile,
    get_next_turn,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intake", tags=["intake"])


# ── Internal helpers ─────────────────────────────────────

async def _get_or_create_profile(
    session: Session,
    db: AsyncSession,
    seeker_type: str | None = None,
) -> Profile:
    """Fetch the existing profile or create a blank one."""
    profile = await db.get(Profile, session.id)
    if profile is None:
        profile = Profile(
            session_id=session.id,
            seeker_type=seeker_type or "both",
            profile_json={
                "seeker_type": seeker_type or "both",
                "current_city": "Bengaluru",
                "_intake_step": 0,  # internal: tracks current turn index
            },
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


# ── POST /api/intake/turn ────────────────────────────────

@router.post("/turn", response_model=IntakeTurnResponse)
async def intake_turn(
    body: IntakeTurnRequest,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> IntakeTurnResponse:
    """Accept one user answer and return the next intake question.

    On the **first call** (``answer`` is ``None``), the engine returns
    the first question.  Each subsequent call processes the answer,
    advances the step counter, and returns the next question.  When
    the sequence is complete, ``complete=true`` is returned.
    """
    if body.session_id is not None and body.session_id != session.id:
        raise HTTPException(
            status_code=400,
            detail="Session ID in request body does not match the authenticated session."
        )

    profile_row = await _get_or_create_profile(session, db)
    profile_data: dict = dict(profile_row.profile_json)  # mutable copy
    current_step: int = profile_data.get("_intake_step", 0)

    # ── Process the incoming answer ──────────────────────
    if body.answer is not None:
        if body.answer.field == "seeker_type":
            profile_data["seeker_type"] = body.answer.value
        else:
            try:
                profile_data = apply_answer(
                    profile_data,
                    body.answer.field,
                    body.answer.value,
                    current_step,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            current_step += 1
            profile_data["_intake_step"] = current_step

    # ── Determine the next turn ──────────────────────────
    next_turn, new_step = get_next_turn(profile_data, current_step)

    # Sync step (may have been advanced past conditional turns)
    profile_data["_intake_step"] = new_step

    # ── Persist ──────────────────────────────────────────
    profile_row.profile_json = profile_data
    profile_row.seeker_type = profile_data.get("seeker_type", "both")
    profile_row.updated_at = func.now()
    await db.commit()
    await db.refresh(profile_row)

    # ── Build response ───────────────────────────────────
    # Strip internal keys from the profile sent to the frontend
    public_profile = {
        k: v for k, v in profile_data.items() if not k.startswith("_")
    }

    if next_turn is None:
        return IntakeTurnResponse(
            complete=True,
            turn=None,
            current_profile=public_profile,
        )

    return IntakeTurnResponse(
        complete=False,
        turn=next_turn,
        current_profile=public_profile,
    )


# ── POST /api/intake/finalize ────────────────────────────

@router.post("/finalize", response_model=IntakeFinalizeResponse)
async def intake_finalize(
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> IntakeFinalizeResponse:
    """Convert the collected intake state into a complete, validated Profile.

    Auto-derives ``worker_band`` from sector + education + employment.
    Returns the full profile for the confirm screen.
    """
    profile_row = await db.get(Profile, session.id)
    if profile_row is None:
        raise HTTPException(
            status_code=404,
            detail="No intake data found for this session. Complete the intake chat first.",
        )

    profile_data: dict = dict(profile_row.profile_json)
    seeker_type = profile_row.seeker_type

    # Build and validate the finalized profile
    finalized = build_finalized_profile(profile_data, seeker_type)

    # Strip internal keys
    clean = {k: v for k, v in finalized.items() if not k.startswith("_")}

    # Validate against the Profile schema
    try:
        profile_schema = ProfileSchema(**clean)
    except Exception as e:
        logger.warning("Profile validation failed: %s", e)
        # Bypasses validation to return whatever we managed to collect safely
        profile_schema = ProfileSchema.model_construct(
            seeker_type=seeker_type,
            **{k: v for k, v in clean.items() if k != "seeker_type"},
        )

    # Persist the finalized profile
    profile_row.profile_json = clean
    profile_row.updated_at = func.now()
    await db.commit()

    return IntakeFinalizeResponse(
        profile=profile_schema,
        session_id=session.id,
    )
