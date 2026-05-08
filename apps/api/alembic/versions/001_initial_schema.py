"""Initial schema: vector extension + 6 tables + indices per PRD §5.

Revision ID: 001
Revises: -
Create Date: 2026-05-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Sessions ─────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("lang_pref", sa.Text()),
    )

    # ── Profiles ─────────────────────────────────
    op.create_table(
        "profiles",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            primary_key=True,
        ),
        sa.Column("seeker_type", sa.Text(), nullable=False),
        sa.Column("profile_json", postgresql.JSONB(), nullable=False),
        sa.Column("resume_extract_json", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Plans ────────────────────────────────────
    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
        ),
        sa.Column("plan_json", postgresql.JSONB(), nullable=False),
        sa.Column("agent_trace_json", postgresql.JSONB()),
        sa.Column("filtered_out_json", postgresql.JSONB()),
        sa.Column("llm_profile", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Schemes ──────────────────────────────────
    op.create_table(
        "schemes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("state", sa.Text()),
        sa.Column(
            "category", postgresql.ARRAY(sa.Text()), nullable=False
        ),
        sa.Column(
            "has_jobs", sa.Boolean(), server_default=sa.text("false")
        ),
        sa.Column("eligibility_json", postgresql.JSONB(), nullable=False),
        sa.Column("docs_required", postgresql.ARRAY(sa.Text())),
        sa.Column("benefits_summary", sa.Text()),
        sa.Column("benefits_detail_md", sa.Text()),
        sa.Column("apply_link", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        # pgvector 384-dim embedding column
        sa.Column("embedding", sa.Text()),
    )

    # ── Jobs Cache ───────────────────────────────
    op.create_table(
        "jobs_cache",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_listing_id", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("employer", sa.Text()),
        sa.Column("area", sa.Text()),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("pay_min", sa.Integer()),
        sa.Column("pay_max", sa.Integer()),
        sa.Column("sector", sa.Text()),
        sa.Column("required_skills", postgresql.ARRAY(sa.Text())),
        sa.Column("worker_band", sa.SmallInteger()),
        sa.Column(
            "scheme_link_id",
            sa.Text(),
            sa.ForeignKey("schemes.id"),
        ),
        sa.Column("description_md", sa.Text()),
        sa.Column(
            "scraped_at", sa.DateTime(timezone=True), nullable=False
        ),
        # pgvector 384-dim embedding column
        sa.Column("embedding", sa.Text()),
    )

    # ── Housing ──────────────────────────────────
    op.create_table(
        "housing",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("area", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("type", sa.Text()),
        sa.Column("price_min", sa.Integer()),
        sa.Column("price_max", sa.Integer()),
        sa.Column("occupancy", sa.Text()),
        sa.Column("gender", sa.Text()),
        sa.Column("amenities", postgresql.ARRAY(sa.Text())),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # ── Indices per §5.2 ─────────────────────────
    # Vector indices (HNSW) — use raw SQL since pgvector
    # column type is handled at runtime by the extension
    op.execute(
        "ALTER TABLE schemes "
        "ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::vector(384)"
    )
    op.execute(
        "ALTER TABLE jobs_cache "
        "ALTER COLUMN embedding TYPE vector(384) "
        "USING embedding::vector(384)"
    )
    op.execute(
        "CREATE INDEX schemes_embedding_idx "
        "ON schemes USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX jobs_embedding_idx "
        "ON jobs_cache USING hnsw (embedding vector_cosine_ops)"
    )

    # GIN index on schemes.category array
    op.execute(
        "CREATE INDEX schemes_category_gin "
        "ON schemes USING gin (category)"
    )

    # B-tree indices
    op.create_index("jobs_band_idx", "jobs_cache", ["worker_band"])
    op.create_index("jobs_area_idx", "jobs_cache", ["area"])
    op.create_index(
        "housing_price_idx", "housing", ["price_min", "price_max"]
    )
    op.create_index("housing_area_idx", "housing", ["area"])


def downgrade() -> None:
    # Drop indices
    op.drop_index("housing_area_idx", table_name="housing")
    op.drop_index("housing_price_idx", table_name="housing")
    op.drop_index("jobs_area_idx", table_name="jobs_cache")
    op.drop_index("jobs_band_idx", table_name="jobs_cache")
    op.execute("DROP INDEX IF EXISTS schemes_category_gin")
    op.execute("DROP INDEX IF EXISTS jobs_embedding_idx")
    op.execute("DROP INDEX IF EXISTS schemes_embedding_idx")

    # Drop tables in reverse dependency order
    op.drop_table("housing")
    op.drop_table("jobs_cache")
    op.drop_table("schemes")
    op.drop_table("plans")
    op.drop_table("profiles")
    op.drop_table("sessions")

    op.execute("DROP EXTENSION IF EXISTS vector")
