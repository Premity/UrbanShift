from typing import Optional
from pydantic import BaseModel


class JobSchema(BaseModel):
    id: str
    source: str
    source_url: str
    source_listing_id: Optional[str] = None
    title: str
    employer: Optional[str] = None
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    pay_min: Optional[int] = None
    pay_max: Optional[int] = None
    sector: Optional[str] = None
    required_skills: Optional[list[str]] = None
    worker_band: Optional[int] = None
    scheme_link_id: Optional[str] = None
    description_md: Optional[str] = None
    scraped_at: str

    model_config = {"from_attributes": True}
