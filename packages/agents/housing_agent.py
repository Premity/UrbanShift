"""Housing agent — finds affordable PG/hostel options near job locations.

Tools:
  search_housing_structured  — DB query filtered by budget + gender compat
  compute_commute            — Haversine distance → estimated commute minutes (×3 min/km)
  filter_by_commute          — attaches commute_to_jobs array, returns ranked results
"""

from __future__ import annotations

import math
import os
from typing import Any, Optional

from sqlalchemy import Float, Integer, Select, Text, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://urbanshift:urbanshift_dev@db:5432/urbanshift",
)

_engine = None
_factory = None


def _get_factory() -> async_sessionmaker:
    global _engine, _factory
    if _factory is None:
        _engine = create_async_engine(DATABASE_URL, echo=False)
        _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _factory


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------

_EARTH_KM = 6371.0
_MIN_PER_KM = 3.0


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_KM * math.asin(math.sqrt(a))


def compute_commute(housing_lat: float, housing_lng: float, job_lat: float, job_lng: float) -> float:
    """Return estimated commute in minutes using Haversine × 3 min/km."""
    return round(_haversine_km(housing_lat, housing_lng, job_lat, job_lng) * _MIN_PER_KM, 1)


# ---------------------------------------------------------------------------
# DB query tool
# ---------------------------------------------------------------------------

async def search_housing_structured(
    budget: int,
    gender: Optional[str],
    city: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> list[dict]:
    """Return housing rows where price_min ≤ budget × 1.05, gender compatible.

    gender compat: if profile gender is 'male' → accept 'male' or 'unisex'
                   if profile gender is 'female' → accept 'female' or 'unisex'
                   if None/other → accept any
    """
    import sys
    import os as _os
    _api_path = _os.path.join(_os.path.dirname(__file__), "..", "..", "apps", "api")
    if _api_path not in sys.path:
        sys.path.insert(0, _os.path.normpath(_api_path))

    from models.housing import Housing

    budget_cap = int(budget * 1.05)

    gender_values: list[str] = []
    if gender == "male":
        gender_values = ["male", "unisex"]
    elif gender == "female":
        gender_values = ["female", "unisex"]

    own_session = db is None
    if own_session:
        factory = _get_factory()
        session = factory()
        await session.__aenter__()
    else:
        session = db

    try:
        stmt: Select = select(Housing).where(Housing.price_min <= budget_cap)

        if gender_values:
            stmt = stmt.where(
                or_(
                    Housing.gender.in_(gender_values),
                    Housing.gender.is_(None),
                )
            )

        result = await session.execute(stmt)
        rows = result.scalars().all()
    finally:
        if own_session:
            await session.__aexit__(None, None, None)

    return [
        {
            "id": h.id,
            "name": h.name,
            "area": h.area,
            "lat": h.lat,
            "lng": h.lng,
            "type": h.type,
            "price_min": h.price_min,
            "price_max": h.price_max,
            "occupancy": h.occupancy,
            "gender": h.gender,
            "amenities": h.amenities or [],
            "source_url": h.source_url,
            "source_name": h.source_name,
        }
        for h in rows
    ]


# ---------------------------------------------------------------------------
# Commute attachment + ranking tool
# ---------------------------------------------------------------------------

def filter_by_commute(
    housing_options: list[dict],
    jobs: list[dict],
    occupancy_pref: Optional[str] = None,
) -> list[dict]:
    """Attach commute_to_jobs array to each housing option and rank results.

    Ranking: (price_min ascending) + (best_commute ascending) combined as
    a weighted score:  score = price_min + best_commute_minutes * 100
    (normalises commute minutes to roughly ₹-equivalent priority weight)

    Filters out housing that doesn't match occupancy_pref when explicitly set.
    """
    # Optional occupancy filter
    if occupancy_pref:
        housing_options = [
            h for h in housing_options
            if h.get("occupancy") is None or h.get("occupancy") == occupancy_pref
        ]

    enriched: list[dict] = []
    for h in housing_options:
        commute_entries: list[dict] = []

        if h.get("lat") and h.get("lng"):
            for job in jobs:
                if job.get("lat") and job.get("lng"):
                    mins = compute_commute(h["lat"], h["lng"], job["lat"], job["lng"])
                    commute_entries.append({
                        "job_id": job["id"],
                        "job_title": job.get("title", ""),
                        "area": job.get("area", ""),
                        "commute_minutes": mins,
                    })

        commute_entries.sort(key=lambda c: c["commute_minutes"])
        best_commute = commute_entries[0]["commute_minutes"] if commute_entries else 9999.0

        enriched.append({**h, "commute_to_jobs": commute_entries, "_best_commute": best_commute})

    enriched.sort(key=lambda h: h["price_min"] + h["_best_commute"] * 100)

    for h in enriched:
        del h["_best_commute"]

    return enriched


# ---------------------------------------------------------------------------
# Agent node (LangGraph-compatible)
# ---------------------------------------------------------------------------

async def housing_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node: resolves housing options from profile + job_out.

    Reads from state:
      state["profile"]  — dict with keys: budget, gender, occupancy_pref (optional)
      state["job_out"]  — list[dict] from job_agent (each with lat, lng, id, title, area)

    Writes to state:
      state["housing_out"] — list[dict] ranked housing with commute_to_jobs
      state["errors"]      — appended on failure
    """
    profile: dict = state.get("profile", {})
    job_out: list[dict] = state.get("job_out", [])
    errors: list[str] = list(state.get("errors", []))

    budget = profile.get("budget")
    gender = profile.get("gender")
    occupancy_pref = profile.get("occupancy_pref")

    if not budget:
        errors.append("housing_agent: profile missing 'budget' — skipping housing search")
        return {**state, "housing_out": [], "errors": errors}

    try:
        options = await search_housing_structured(budget=int(budget), gender=gender)
        ranked = filter_by_commute(options, job_out, occupancy_pref)
        return {**state, "housing_out": ranked, "errors": errors}
    except Exception as exc:
        errors.append(f"housing_agent: {exc}")
        return {**state, "housing_out": [], "errors": errors}
