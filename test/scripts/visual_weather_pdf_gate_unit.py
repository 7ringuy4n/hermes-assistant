# -*- coding: utf-8 -*-
"""Regression: visual-PDF gate distinguishes positive output and audit lines."""
from __future__ import annotations

from visual_weather_pdf_gate import (
    blocking_defects_clear,
    delivered_image_count,
    extracted_pdf_text,
    new_pdf_seen,
    unrequested_current_scope_terms,
    weather_code_defects,
    model_attribution_defects,
    visual_quality_score,
)


def main() -> int:
    assert not new_pdf_seen("NO_NEW_PDF\n/old/file.pdf")
    assert new_pdf_seen("NEW_PDF /data/assistant/media/out/fresh.pdf")
    assert delivered_image_count("DELIVERED_IMAGE_COUNT 0") == 0
    assert delivered_image_count("DELIVERED_IMAGE_COUNT 2\n") == 2
    assert delivered_image_count("DELIVERED_IMAGE_COUNT_QUERY_FAILED query_error") is None
    assert visual_quality_score("QUALITY_SCORE: 8/10") == 8
    assert visual_quality_score("**Rating: 6/10**") == 6
    assert visual_quality_score("looks good") is None
    assert blocking_defects_clear("BLOCKING_DEFECTS: none")
    assert not blocking_defects_clear("BLOCKING_DEFECTS: text overlap")
    assert not blocking_defects_clear("no structured verdict")
    assert extracted_pdf_text(
        "PDF_TEXT_BEGIN\nCurrent weather\nPDF_TEXT_END\nBLOCKING_DEFECTS: none"
    ) == "Current weather"
    assert extracted_pdf_text("PDF_TEXT_CHARS 42") == ""
    assert unrequested_current_scope_terms("Trời mưa, nếu ra ngoài bạn nên mang theo ô") == [
        "nếu ra ngoài",
        "nên mang",
    ]
    assert unrequested_current_scope_terms("Nhiệt độ hiện tại 27°C") == []
    # Actual acknowledged PDF regression: WMO 55 is dense drizzle, not
    # light drizzle or a thunderstorm. Font/readability cannot certify facts.
    assert weather_code_defects("Mã thời tiết WMO\n55 — Mưa phùn dông nhẹ") == ["wmo_55_description_mismatch"]
    assert weather_code_defects("Mã thời tiết WMO\n55 — Mưa phùn dày đặc") == []
    assert weather_code_defects("Gió nhẹ\nMã thời tiết WMO: 55 — Mưa phùn dày đặc") == []
    assert weather_code_defects("Mã thời tiết WMO\n51 — Mưa phùn nhẹ") == []
    assert model_attribution_defects("Open-Meteo. Nhiệt độ thực đo 27,7°C; trời có nắng yếu") == [
        'open_meteo_model_mislabeled_measurement','is_day_does_not_establish_sunshine']
    assert model_attribution_defects("Open-Meteo — dữ liệu mô hình hiện tại, nhiệt độ 27,7°C") == []
    assert model_attribution_defects("Open-Meteo — giá trị mô hình thời tiết, không phải quan trắc trạm.") == []
    assert model_attribution_defects("Open-Meteo — không phải quan trắc trạm. Nhiệt độ thực đo 27°C") == [
        'open_meteo_model_mislabeled_measurement']
    assert model_attribution_defects("Open-Meteo — không phải dữ liệu thực đo. MƯA ĐO ĐƯỢC 1 mm") == [
        'open_meteo_model_mislabeled_measurement']
    assert model_attribution_defects("Trạm khí tượng — nhiệt độ đo được 27,7°C") == []
    # Actual live PDF disclaimer phrasing must not be a false positive.
    assert model_attribution_defects(
        "Open-Meteo — các giá trị điều kiện hiện tại do mô hình số tính toán cho toạ độ "
        "Đà Nẵng, không phải số đo từ trạm quan trắc."
    ) == []
    assert model_attribution_defects(
        "Open-Meteo — không phải số liệu từ trạm khí tượng đo được."
    ) == []
    # A positive Open-Meteo measurement claim still fails.
    assert model_attribution_defects("Open-Meteo — nhiệt độ đo được 27°C") == [
        'open_meteo_model_mislabeled_measurement']
    print("visual_weather_pdf_gate_unit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
