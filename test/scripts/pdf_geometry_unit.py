"""Real HTML print geometry rejects clipped text and orphan trailing pages."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "architect/models/dispatcher"))
import office_file


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        print("running test case 1/3 coherent multipage text remains valid")
        paragraph = "Sample useful content with readable native text. " * 25
        office_file.write_pdf_from_html(root / "valid.pdf", f'<html><body><h1>Sample report</h1><p>{paragraph}</p><div style="break-before:page"><h2>Sample details</h2><p>{paragraph}</p></div></body></html>')
        for index, html in enumerate((
            '<html><body><p style="margin-left:900px;width:500px">Sample clipped content</p></body></html>',
            f'<html><body><h1>Sample report</h1><p>{paragraph}</p><p style="break-before:page">Sample source</p></body></html>',
        ), 2):
            print(f"running test case {index}/3 reject invalid print geometry")
            dest = root / f"invalid-{index}.pdf"
            try:
                office_file.write_pdf_from_html(dest, html)
                raise AssertionError("invalid geometry accepted")
            except ValueError:
                assert not dest.exists()
    print("PASS PDF print geometry")


if __name__ == "__main__":
    main()
