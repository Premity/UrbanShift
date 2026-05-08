from typing import Literal, Optional
from pydantic import BaseModel, field_validator


class HousingSchema(BaseModel):
    id: str
    name: str
    area: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    type: Optional[Literal["pg", "hostel", "shared"]] = None
    price_min: int
    price_max: int
    occupancy: Optional[Literal["single", "double", "triple", "dorm"]] = None
    gender: Optional[Literal["male", "female", "unisex"]] = None
    amenities: Optional[list[str]] = None
    source_url: str
    source_name: str
    scraped_at: str

    @field_validator("source_url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"URL must start with http(s): {v}")
        return v

    model_config = {"from_attributes": True}
