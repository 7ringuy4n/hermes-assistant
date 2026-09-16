"""Real office HTTP boundary: direct creation and private preview publication."""
from pathlib import Path
import os
import sys
import tempfile
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "architect/models/dispatcher"))
import office_file


def main():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"OFFICE_FILE_GEN": "active"}):
        media = Path(temp)
        app = FastAPI()
        delivery = Mock(side_effect=AssertionError("unexpected messaging dependency"))
        office_file.register_office_file(app, media, delivery)
        client = TestClient(app)
        print("running test case 1/6 direct office creation needs no Zalo destination")
        response = client.post("/v1/office-file", json={"prompt": "Sample content", "output_type": "txt", "filename": "sample.txt", "send_zalo": False})
        assert response.status_code == 200, response.text
        assert Path(response.json()["path"]).read_text().rstrip("\n") == "Sample content"
        delivery.assert_not_called()
        print("running test case 2/6 draft stays outside public watcher")
        response = client.post("/v1/office-file", json={"prompt": "Sample draft", "output_type": "txt", "filename": "draft.txt", "send_zalo": False, "draft": True})
        assert response.status_code == 200, response.text
        assert not (media / "out/draft.txt").exists()
        assert Path(response.json()["path"]).is_file()
        assert "/.drafts/" in response.json()["hermes_path"]
        delivery.assert_not_called()
        print("running test case 3/6 draft cannot trigger delivery")
        response = client.post("/v1/office-file", json={"prompt": "Sample draft", "output_type": "txt", "thread_id": "sample", "draft": True})
        assert response.status_code == 400
        delivery.assert_not_called()
        for index, (kind, body, count) in enumerate((
            ("pdf", '<html><body><h1>Thông tin hiện tại</h1><p>Nội dung tiếng Việt.</p></body></html>', 1),
            ("pptx", '# Report\n## First section\n- Required observation\n## Second section\n- Required source\n', 3),
        ), 4):
            print(f"running test case {index}/6 private {kind} review includes actual native text and every page image")
            with patch.object(office_file, "_MEDIA_ROOTS", (media / "out",)):
                response = client.post("/v1/office-file", json={"prompt": body, "output_type": kind,
                    "filename": "review." + kind, "draft": True, "send_zalo": False})
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["review"]["page_count"] == count
            assert len(result["review"]["pages"]) == count
            assert all(page["text"].strip() and "/.drafts/" in page["image_path"] for page in result["review"]["pages"])
            assert not (media / ("out/review." + kind)).exists()
            assert Path(result["path"]).is_file()
            delivery.assert_not_called()
        print("running test case 6/6 formatted authoring cannot bypass private review")
        for kind in ("pdf", "pptx", "docx", "xlsx"):
            for send in (False, True):
                response = client.post("/v1/office-file", json={"prompt": "unreviewed", "output_type": kind,
                    "filename": "unreviewed." + kind, "thread_id": "sample" if send else "", "send_zalo": send})
                assert response.status_code == 409, response.text
                assert "document_preview_required" in response.text
                assert not (media / ("out/unreviewed." + kind)).exists()
                delivery.assert_not_called()
    print("PASS office API standalone and draft boundaries")


if __name__ == "__main__":
    main()
