"""Dependency injection for FastAPI routes."""

import uuid

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Session


async def get_current_session(
    sid: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Resolve the `sid` cookie to a Session row.

    Raises 401 if cookie is missing or session not found.
    Updates ``last_seen_at`` on every successful resolution.
    """
    if sid is None:
        raise HTTPException(status_code=401, detail="Missing session cookie (sid)")

    try:
        session_id = uuid.UUID(sid)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid session id")

    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Session not found")

    # Touch last_seen_at
    session.last_seen_at = func.now()
    await db.commit()
    await db.refresh(session)

    return session
