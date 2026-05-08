from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


class EligibilitySchema(BaseModel):
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender: Optional[list[Literal["male", "female", "other"]]] = None
    income_max_inr: Optional[int] = None
    sectors: Optional[list[str]] = None
    worker_bands: Optional[list[int]] = None
    migrant_only: bool = False
    state_residency: Optional[str] = None
    requires_aadhaar: bool = False
    extra_rules_md: Optional[str] = None


class SchemeSchema(BaseModel):
    id: str
    name: str
    level: Literal["central", "state"]
    state: Optional[str] = None
    category: list[str]
    has_jobs: bool
    eligibility: EligibilitySchema
    docs_required: Optional[list[str]] = None
    benefits_summary: str
    benefits_detail_md: Optional[str] = None
    apply_link: str
    source_url: str
    source_name: str
    scraped_at: str
    embedding: None = None

    @field_validator("source_url", "apply_link")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"URL must start with http(s): {v}")
        return v

    @model_validator(mode="after")
    def state_requires_state_code(self) -> "SchemeSchema":
        if self.level == "state" and not self.state:
            raise ValueError(f"Scheme {self.id}: level=state requires a state code")
        return self

    model_config = {"from_attributes": True}
