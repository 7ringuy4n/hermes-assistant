"""Actual conversion HTTP boundary: failed batches are never partly published."""
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "architect/models/dispatcher"))
import file_convert
import office_file


def main():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "sample.pdf"
        source.write_bytes(b"isolated fixture; renderer replaced")
        delivery = Mock(side_effect=AssertionError("failed publication reached delivery"))
        app = FastAPI()
        file_convert.register_file_convert(app, root, delivery)
        def outputs(req, work):
            first = work / "page-001.png"; second = work / "page-002.png"
            first.write_bytes(b"first"); second.write_bytes(b"second")
            return [first, second], "page-raster"
        original_replace = Path.replace
        def disk_full(path, target):
            if path.name == "page-002.png":
                raise OSError("isolated disk-full fixture")
            return original_replace(path, target)
        with patch.object(office_file, "_MEDIA_ROOTS", (root,)), patch.dict(os.environ, {"OFFICE_FILE_GEN": "active"}), patch.object(file_convert, "convert_file", outputs):
            client = TestClient(app)
            payload = {"source_path": str(source), "output_type": "png"}
            print("running test case 1/4 failed second-page move leaves no published batch", flush=True)
            with patch.object(Path, "replace", disk_full):
                response = client.post("/v1/file-convert", json=payload)
            assert response.status_code == 503, response.text
            assert not list((root / "out/.conversions").iterdir())
            assert not list((root / "out/.build").iterdir())
            delivery.assert_not_called()
            print("running test case 2/4 complete batch publishes together in page order", flush=True)
            response = client.post("/v1/file-convert", json=payload)
            assert response.status_code == 200, response.text
            files = response.json()["files"]
            assert [item["file"] for item in files] == ["page-001.png", "page-002.png"]
            assert all(Path(item["path"]).is_file() for item in files)
            assert len({Path(item["path"]).parent for item in files}) == 1
            delivery.assert_not_called()
            print("running test case 3/4 conversion delivery retains exact original group source", flush=True)
            delivery.side_effect = None
            delivery.return_value = {"ok": True, "message_id": "fixture-ack"}
            response = client.post("/v1/file-convert", json={**payload, "send_zalo": True,
                                   "thread_id": "fixture-group", "thread_type": "group",
                                   "source_message_id": "original-quoted-request"})
            assert response.status_code == 200, response.text
            assert delivery.call_count == 2
            assert all(call.kwargs.get("source_message_id") == "original-quoted-request"
                       and call.kwargs["thread_type"] == "group" for call in delivery.call_args_list), "conversion dropped original delivery binding"
            delivery.reset_mock()
            print("running test case 4/4 sourceless conversion delivery fails before rendering", flush=True)
            with patch.object(file_convert, "convert_file", side_effect=AssertionError("sourceless render")):
                response = client.post("/v1/file-convert", json={**payload, "send_zalo": True,
                                       "thread_id": "fixture-group", "thread_type": "group"})
            assert response.status_code == 400, response.text
            delivery.assert_not_called()
    print("PASS atomic conversion publication")


if __name__ == "__main__":
    main()
