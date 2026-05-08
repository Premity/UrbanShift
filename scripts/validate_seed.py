"""
Usage:
    python scripts/validate_seed.py schemes
    python scripts/validate_seed.py housing
"""

import json
import sys
from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator

ROOT = Path(__file__).resolve().parent.parent


# ── Eligibility schema (PRD §5.5) ────────────────────────────────────────────

class Eligibility(BaseModel):
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


# ── Scheme schema (PRD §5.1) ──────────────────────────────────────────────────

class Scheme(BaseModel):
    id: str
    name: str
    level: Literal["central", "state"]
    state: Optional[str] = None
    category: list[str]
    has_jobs: bool
    eligibility: Eligibility
    docs_required: Optional[list[str]] = None
    benefits_summary: str
    benefits_detail_md: Optional[str] = None
    apply_link: str
    source_url: str
    source_name: str
    scraped_at: str
    embedding: None = None  # null in seed; computed later

    @field_validator("source_url", "apply_link")
    @classmethod
    def must_be_https(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"URL must start with http(s): {v}")
        return v

    @model_validator(mode="after")
    def state_scheme_requires_state_code(self) -> "Scheme":
        if self.level == "state" and not self.state:
            raise ValueError(f"Scheme {self.id}: level=state requires a state code")
        return self


# ── Housing schema (PRD §5.1) — included for completeness ────────────────────

class Housing(BaseModel):
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
    def must_be_https(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"URL must start with http(s): {v}")
        return v


# ── Validation logic ──────────────────────────────────────────────────────────

def validate_schemes(data: list) -> None:
    errors: list[str] = []
    schemes: list[Scheme] = []

    for i, raw in enumerate(data):
        try:
            s = Scheme.model_validate(raw)
            schemes.append(s)
        except Exception as e:
            errors.append(f"[{i}] id={raw.get('id', '?')} — {e}")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" ", e)
        sys.exit(1)

    # Distribution checks
    has_jobs_count = sum(1 for s in schemes if s.has_jobs)
    all_bands = set()
    for s in schemes:
        if s.eligibility.worker_bands:
            all_bands.update(s.eligibility.worker_bands)

    missing_citations = [s.id for s in schemes if not s.source_url or not s.source_name]

    print(f"✓  Total schemes:        {len(schemes)} (required: 30)")
    print(f"✓  has_jobs=true:        {has_jobs_count} (required: ≥3)")
    print(f"✓  Worker bands covered: {sorted(all_bands)} (required: {{1,2,3,4}})")
    print(f"✓  Missing citations:    {missing_citations} (required: [])")

    failures = []
    if len(schemes) != 30:
        failures.append(f"Expected 30 schemes, got {len(schemes)}")
    if has_jobs_count < 3:
        failures.append(f"Expected ≥3 has_jobs=true, got {has_jobs_count}")
    if not {1, 2, 3, 4}.issubset(all_bands):
        failures.append(f"Missing worker bands: {({1,2,3,4} - all_bands)}")
    if missing_citations:
        failures.append(f"Missing citations on: {missing_citations}")

    if failures:
        print("\nCHECK FAILURES:")
        for f in failures:
            print(" ", f)
        sys.exit(1)

    print("\nAll checks passed.")


def validate_housing(data: list) -> None:
    errors: list[str] = []
    items: list[Housing] = []

    for i, raw in enumerate(data):
        try:
            h = Housing.model_validate(raw)
            items.append(h)
        except Exception as e:
            errors.append(f"[{i}] id={raw.get('id', '?')} — {e}")

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" ", e)
        sys.exit(1)

    missing_citations = [h.id for h in items if not h.source_url or not h.source_name]
    missing_coords = [h.id for h in items if h.lat is None or h.lng is None]

    print(f"✓  Total housing:        {len(items)} (required: 50)")
    print(f"✓  Missing citations:    {missing_citations} (required: [])")
    print(f"✓  Missing coordinates:  {len(missing_coords)} entries")

    failures = []
    if len(items) != 50:
        failures.append(f"Expected 50 housing entries, got {len(items)}")
    if missing_citations:
        failures.append(f"Missing citations on: {missing_citations}")

    if failures:
        print("\nCHECK FAILURES:")
        for f in failures:
            print(" ", f)
        sys.exit(1)

    print("\nAll checks passed.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("schemes", "housing"):
        print("Usage: python scripts/validate_seed.py schemes|housing")
        sys.exit(1)

    target = sys.argv[1]
    seed_file = ROOT / "data" / "seed" / f"{target}.json"

    if not seed_file.exists():
        print(f"File not found: {seed_file}")
        sys.exit(1)

    data = json.loads(seed_file.read_text())
    print(f"Loaded {len(data)} entries from {seed_file}\n")

    if target == "schemes":
        validate_schemes(data)
    else:
        validate_housing(data)


if __name__ == "__main__":
    main()
