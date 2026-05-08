"""Profile routes — POST /api/profile."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_session
from models import Profile, Session
from schemas.profile import ProfileUpsertRequest, ProfileResponse

router = APIRouter(prefix="/api", tags=["profile"])


@router.post("/profile", response_model=ProfileResponse)
async def upsert_profile(
    body: ProfileUpsertRequest,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    """Create or update the profile for the current session."""

    existing = await db.get(Profile, session.id)

    if existing is not None:
        # Update existing profile
        existing.seeker_type = body.seeker_type
        existing.profile_json = body.profile_json
        existing.resume_extract_json = body.resume_extract_json
        existing.updated_at = func.now()
        await db.commit()
        await db.refresh(existing)
        profile = existing
    else:
        # Create new profile
        profile = Profile(
            session_id=session.id,
            seeker_type=body.seeker_type,
            profile_json=body.profile_json,
            resume_extract_json=body.resume_extract_json,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return ProfileResponse(
        session_id=profile.session_id,
        seeker_type=profile.seeker_type,
        profile_json=profile.profile_json,
        resume_extract_json=profile.resume_extract_json,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )
