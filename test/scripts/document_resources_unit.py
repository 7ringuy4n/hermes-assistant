"""Real HTML renderer: embedded media, missing/corrupt resources, SSRF guard."""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "architect/models/dispatcher"))
import office_file


def main() -> int:
    from PIL import Image
    import pymupdf
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        Image.new("RGB", (320, 180), (30, 110, 175)).save(root / "fixture.png")
        (root / "corrupt.png").write_bytes(b"not an image")
        with patch.object(office_file, "_MEDIA_ROOTS", (root,)):
            print("running test case 1/9 HTML embeds real image with whitespace in src")
            pdf = office_file.write_pdf_from_html(root / "valid.pdf", f'<!DOCTYPE html><html><body><h1>Thông tin hiện tại</h1><img src = "{(root / "fixture.png").as_uri()}" width="320"><p>Độ ẩm và nhiệt độ</p></body></html>')
            with pymupdf.open(pdf) as document:
                assert document[0].get_image_info()
                assert "Thông tin" in document[0].get_text()
                assert document[0].rect.height > 800
            for index, src in enumerate((str(root / "missing.png"), str(root / "corrupt.png"), "http://127.0.0.1:8095/v1/notes", "file:///etc/passwd"), start=2):
                print(f"running test case {index}/9 reject unavailable or unsafe resource")
                destination = root / f"reject-{index}.pdf"
                try:
                    office_file.write_pdf_from_html(destination, f'<html><body><h1>Report</h1><img src="{src}"></body></html>')
                    raise AssertionError("blank or unsafe image accepted")
                except ValueError:
                    assert not destination.exists()
            import zipfile
            for index, kind in enumerate(("docx", "xlsx", "pptx"), start=6):
                print(f"running test case {index}/9 {kind} embeds image and rejects missing asset")
                body = f'# Thông tin hiện tại\nIMAGE: {root / "fixture.png"}\nLAYOUT: full-bleed\n## Chi tiết\n- Nhiệt độ: 28°C\n'
                output = office_file.write_office(root / f"visual.{kind}", f".{kind}", body)
                with zipfile.ZipFile(output) as archive:
                    assert any("/media/" in name for name in archive.namelist())
                try:
                    office_file.write_office(root / f"missing.{kind}", f".{kind}", body.replace("fixture.png", "missing.png"))
                    raise AssertionError("missing office visual accepted")
                except ValueError:
                    pass
            print("running test case 9/9 translate Hermes shared-volume alias in every office format")
            (root / "out").mkdir()
            Image.new("RGB", (320, 180), (30, 110, 175)).save(root / "out/alias.png")
            with patch.dict("os.environ", {"MEDIA_CACHE_DIR": str(root)}):
                alias = "/opt/data/media/out/alias.png"
                assert office_file._resolve_media_path(alias) == root / "out/alias.png"
                translated = office_file.write_pdf_from_html(root / "alias.pdf", f'<html><body><h1>Shared volume</h1><img src = "{alias}"></body></html>')
                with pymupdf.open(translated) as document:
                    assert document[0].get_image_info()
                for kind in ("docx", "xlsx", "pptx"):
                    output = office_file.write_office(root / f"alias.{kind}", f".{kind}", f"# Shared volume\nIMAGE: {alias}\nLAYOUT: full-bleed\n## Details\n- Observation: Verified\n")
                    with zipfile.ZipFile(output) as archive:
                        assert any("/media/" in name for name in archive.namelist())
    print("PASS document resources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
