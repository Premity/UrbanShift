"""Pydantic schemas for session endpoints."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    lang_pref: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: uuid.UUID
    lang_pref: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
