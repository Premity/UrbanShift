"""Session routes — POST /api/session/start."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Session
from schemas.session import SessionStartRequest, SessionStartResponse

router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start", response_model=SessionStartResponse)
async def start_session(
    body: SessionStartRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionStartResponse:
    """Create a new anonymous session and set the ``sid`` httpOnly cookie."""

    session = Session(lang_pref=body.lang_pref)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Set httpOnly cookie (SameSite=Lax, 30-day expiry)
    response.set_cookie(
        key="sid",
        value=str(session.id),
        httponly=True,
        samesite="lax",
        path="/",
        max_age=86400 * 30,  # 30 days
    )

    return SessionStartResponse(
        session_id=session.id,
        lang_pref=session.lang_pref,
        created_at=session.created_at,
    )
