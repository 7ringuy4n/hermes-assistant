# -*- coding: utf-8 -*-
"""Pure result parsing shared by the visual-weather PDF live gate and unit."""
from __future__ import annotations

import re


def new_pdf_seen(text: str) -> bool:
    """Require the positive line token; ``NO_NEW_PDF`` must never match."""
    return bool(re.search(r"(?m)^NEW_PDF\s+\S+", text or ""))


def delivered_image_count(text: str) -> int | None:
    """Return the durable delivery count, or None when the audit failed."""
    match = re.search(r"(?m)^DELIVERED_IMAGE_COUNT\s+(\d+)\s*$", text or "")
    return int(match.group(1)) if match else None


def visual_quality_score(text: str) -> float | None:
    """Read the judge's explicit score, accepting the legacy Rating label."""
    match = re.search(
        r"(?im)(?:QUALITY_SCORE\s*:|Rating\s*:)\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*/\s*10",
        text or "",
    )
    return float(match.group(1)) if match else None


def blocking_defects_clear(text: str) -> bool:
    """Require the structured visual judge to explicitly report no blocker."""
    match = re.search(r"(?im)^BLOCKING_DEFECTS\s*:\s*(.+?)\s*$", text or "")
    return bool(match and match.group(1).strip().lower() == "none")


def extracted_pdf_text(text: str) -> str:
    """Return only rendered-PDF text, excluding judge and runtime commentary."""
    if "PDF_TEXT_BEGIN" not in text or "PDF_TEXT_END" not in text:
        return ""
    return text.split("PDF_TEXT_BEGIN", 1)[1].split("PDF_TEXT_END", 1)[0].strip()


def unrequested_current_scope_terms(text: str) -> list[str]:
    """Identify forecast/recommendation copy forbidden in a current-only PDF."""
    lower = (text or "").lower()
    forbidden = (
        "dự báo 4 ngày",
        "khả năng mưa",
        "khuyến nghị",
        "nếu ra ngoài",
        "nên mang",
        "hãy mang",
        "mang theo áo mưa",
    )
    return [phrase for phrase in forbidden if phrase in lower]


def weather_code_defects(text: str) -> list[str]:
    """Known factual regression oracle, not a complete weather fact checker.

    Source: https://open-meteo.com/en/docs#weathervariables (WMO table).
    Match the labeled code row only; unrelated light-wind prose is not a defect.
    Other codes and missing code rows still require evidence-based review.
    """
    row = re.search(r"(?im)\bWMO\s*[:：]?\s*55\s*[—–:-]\s*([^\r\n]+)", text or "")
    if row and re.search(r"\b(?:dông|giông|nhẹ|thunderstorm|light)\b", row.group(1), re.I):
        return ["wmo_55_description_mismatch"]
    return []


def model_attribution_defects(text: str) -> list[str]:
    """Known current-only Open-Meteo model-vs-measurement regression oracle."""
    lower=(text or '').casefold()
    if 'open-meteo' not in lower:
        return []
    found=[]
    # An explicit disclaimer is correct attribution, not a positive claim.
    # Remove only the negated occurrence; another positive measurement label
    # elsewhere in the same document must still fail. The disclaimer may read
    # "không phải số đo từ trạm quan trắc" or "không phải dữ liệu thực đo".
    positive = re.sub(
        r'\bkhông\s+(?:phải\s+)?(?:là\s+)?'
        r'(?:(?:dữ\s+liệu|số\s+liệu|số\s+đo|kết\s+quả)\s+)?'
        r'(?:từ\s+trạm(?:\s+khí\s+tượng)?\s+)?'
        r'(?:quan\s+trắc(?:\s+trạm)?|thực\s+đo|đo\s+được|đo\s+trực\s+tiếp)\b',
        '', lower,
    )
    if any(term in positive for term in ('thực đo','đo được','quan trắc')):
        found.append('open_meteo_model_mislabeled_measurement')
    if 'trời có nắng yếu' in lower:
        found.append('is_day_does_not_establish_sunshine')
    return found
