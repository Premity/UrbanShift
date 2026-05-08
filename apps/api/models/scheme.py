from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from .base import Base


class Scheme(Base):
    __tablename__ = "schemes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str | None] = mapped_column(Text)
    category: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    has_jobs: Mapped[bool] = mapped_column(Boolean, server_default="false")
    eligibility_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    docs_required: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    benefits_summary: Mapped[str | None] = mapped_column(Text)
    benefits_detail_md: Mapped[str | None] = mapped_column(Text)
    apply_link: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384))
