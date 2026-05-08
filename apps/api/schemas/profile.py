"""Pydantic schemas for profile endpoints."""

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ProfileUpsertRequest(BaseModel):
    seeker_type: str
    profile_json: dict[str, Any]
    resume_extract_json: Optional[dict[str, Any]] = None


class ProfileResponse(BaseModel):
    session_id: uuid.UUID
    seeker_type: str
    profile_json: dict[str, Any]
    resume_extract_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
