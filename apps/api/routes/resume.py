"""Resume upload + parse endpoint — POST /api/resume/parse.

Accepts a multipart PDF or DOCX file (≤ 5 MB).
Extracts text in-memory (never written to disk), then calls the LLM
with a structured-output prompt to fill as many Profile fields as possible.
Returns a partial Profile JSON; the frontend navigates directly to the
Confirm screen so the user can review and fill any missing fields.
"""

from __future__ import annotations

import io
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",  # Some browsers send this for .docx
}

_EXTRACT_SYSTEM_PROMPT = """\
You are a structured data extractor. Given resume text, extract profile \
information for an Indian urban migrant job/housing seeker and return ONLY \
valid JSON with these optional fields (omit or set to null if not present or \
unclear):

{
  "name": "string | null",
  "age": "integer | null",
  "gender": "male | female | other | prefer_not | null",
  "origin_state": "state name string | null",
  "native_lang": "ISO 639-1 code e.g. hi, kn, en, ta | null",
  "languages_spoken": ["ISO code", ...],
  "sector": "driving | construction | domestic_work | retail | hospitality | manufacturing | security | bpo | data_entry | admin | null",
  "skills": ["skill string", ...],
  "education": "none | primary | class10 | class12 | diploma | grad | postgrad | null",
  "years_experience": "integer | null",
  "employment_status": "unemployed | employed | underemployed | student | null",
  "income_range_inr": [min_int, max_int] or null
}

Rules:
- Return ONLY the JSON object, no markdown, no explanation.
- Use ISO 639-1 language codes (en, hi, kn, ta, te, ml, mr, gu, pa, bn).
- For origin_state use full state name in English (e.g. "Bihar", "Uttar Pradesh").
- If a value cannot be reliably inferred, set it to null.
- For sector, pick the closest match from the allowed values only.
- Skills should be lowercase, short phrases.
"""


def _extract_text_pdf(data: bytes) -> str:
    """Extract text from a PDF using pdfplumber."""
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF support not installed.")

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise HTTPException(
                status_code=400,
                detail="resume.error_no_text",
            )
        return text
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        raise HTTPException(status_code=400, detail="resume.error_parse")


def _extract_text_docx(data: bytes) -> str:
    """Extract text from a DOCX using python-docx."""
    try:
        from docx import Document  # type: ignore
    except ImportError:
        raise HTTPException(status_code=500, detail="DOCX support not installed.")

    try:
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        if not text:
            raise HTTPException(status_code=400, detail="resume.error_no_text")
        return text
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("DOCX extraction failed: %s", e)
        raise HTTPException(status_code=400, detail="resume.error_parse")


def _llm_extract(text: str) -> dict[str, Any]:
    """Call the LLM to extract structured profile fields from resume text."""
    try:
        import litellm  # type: ignore
    except ImportError:
        raise HTTPException(status_code=500, detail="LLM client not installed.")

    llm_profile = os.getenv("LLM_PROFILE", "dev")
    if llm_profile == "demo":
        model = "gemini/gemini-2.5-flash"
    else:
        # dev profile: Groq Llama
        model = "groq/llama-3.3-70b-versatile"

    # Truncate to avoid token limits — 4000 chars is plenty for a resume
    truncated = text[:4000]

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Resume text:\n\n{truncated}\n\nExtract profile fields as JSON.",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError as e:
        logger.warning("LLM returned invalid JSON: %s", e)
        return {}
    except Exception as e:
        logger.warning("LLM extraction failed: %s", e)
        return {}


def _clean_profile(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate and clean the LLM output; return (clean_dict, missing_fields)."""
    allowed_education = {"none", "primary", "class10", "class12", "diploma", "grad", "postgrad"}
    allowed_gender = {"male", "female", "other", "prefer_not"}
    allowed_status = {"unemployed", "employed", "underemployed", "student"}
    allowed_sector = {
        "driving", "construction", "domestic_work", "retail", "hospitality",
        "manufacturing", "security", "bpo", "data_entry", "admin",
    }

    clean: dict[str, Any] = {}

    def _set(key: str, value: Any) -> None:
        if value is not None:
            clean[key] = value

    _STATE_MAP = {
        "ap": "Andhra Pradesh", "ar": "Arunachal Pradesh", "as": "Assam", "br": "Bihar",
        "cg": "Chhattisgarh", "ch": "Chhattisgarh", "ga": "Goa", "gj": "Gujarat", 
        "hr": "Haryana", "hp": "Himachal Pradesh", "jh": "Jharkhand", "ka": "Karnataka",
        "kl": "Kerala", "mp": "Madhya Pradesh", "mh": "Maharashtra", "mn": "Manipur",
        "ml": "Meghalaya", "mz": "Mizoram", "nl": "Nagaland", "od": "Odisha", "or": "Odisha",
        "pb": "Punjab", "rj": "Rajasthan", "sk": "Sikkim", "tn": "Tamil Nadu",
        "tg": "Telangana", "ts": "Telangana", "tr": "Tripura", "up": "Uttar Pradesh",
        "uk": "Uttarakhand", "wb": "West Bengal", "dl": "Delhi",
    }

    _set("name", raw.get("name") if isinstance(raw.get("name"), str) else None)
    _set("age", raw.get("age") if isinstance(raw.get("age"), int) and 10 <= raw["age"] <= 120 else None)

    gender = raw.get("gender")
    _set("gender", gender if gender in allowed_gender else None)

    state = raw.get("origin_state")
    if isinstance(state, str):
        state_clean = state.lower().replace(".", "").strip()
        if state_clean in _STATE_MAP:
            state = _STATE_MAP[state_clean]
    _set("origin_state", state if isinstance(state, str) else None)

    _set("native_lang", raw.get("native_lang") if isinstance(raw.get("native_lang"), str) else None)

    langs = raw.get("languages_spoken")
    _set("languages_spoken", [l for l in langs if isinstance(l, str)] if isinstance(langs, list) else None)

    sector = raw.get("sector")
    _set("sector", sector if sector in allowed_sector else None)

    skills = raw.get("skills")
    _set("skills", [s for s in skills if isinstance(s, str)] if isinstance(skills, list) else None)

    edu = raw.get("education")
    _set("education", edu if edu in allowed_education else None)

    _set("years_experience", raw.get("years_experience") if isinstance(raw.get("years_experience"), int) else None)

    status = raw.get("employment_status")
    _set("employment_status", status if status in allowed_status else None)

    inc = raw.get("income_range_inr")
    if isinstance(inc, list) and len(inc) == 2 and all(isinstance(i, int) for i in inc):
        clean["income_range_inr"] = inc

    # Determine which key profile fields are still missing
    important_fields = ["name", "age", "gender", "origin_state", "native_lang", "sector", "education"]
    missing = [f for f in important_fields if f not in clean or clean[f] is None]

    return clean, missing


# ── Route ─────────────────────────────────────────────────

@router.post("/parse")
async def parse_resume(file: UploadFile = File(...)) -> dict[str, Any]:
    """Accept a PDF or DOCX resume, extract text in-memory, call LLM for
    structured profile fields, and return partial profile JSON.

    The file is NEVER written to disk.
    """
    # Size check
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail="resume.error_too_large",
        )

    filename = (file.filename or "").lower()
    content_type = file.content_type or ""

    # Determine format by extension first, then content-type
    if filename.endswith(".pdf") or content_type == "application/pdf":
        text = _extract_text_pdf(data)
    elif filename.endswith(".docx") or "wordprocessingml" in content_type:
        text = _extract_text_docx(data)
    else:
        raise HTTPException(
            status_code=400,
            detail="resume.error_unsupported_type",
        )

    # LLM extraction
    raw_extracted = _llm_extract(text)

    # Clean + validate
    profile_fields, missing_fields = _clean_profile(raw_extracted)

    logger.info(
        "Resume parsed: extracted_fields=%d missing=%s",
        len(profile_fields),
        missing_fields,
    )

    return {
        "profile": profile_fields,
        "missing_fields": missing_fields,
        "parsed_ok": len(profile_fields) > 0,
    }
