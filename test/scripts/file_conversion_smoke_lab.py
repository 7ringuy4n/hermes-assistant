"""Natural attachment conversions through the real plugin and shared renderer."""
import json
import argparse
import subprocess
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from scoped_documents_smoke_lab import acknowledged_artifact, delivered, docker_python, ensure_ready, thread_terminal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quotes-only', action='store_true')
    parser.add_argument('--case', action='append', default=[], help='Run only named cases; reject unknown names.')
    options = parser.parse_args()
    ensure_ready()
    admin = next(line.partition("|")[0].strip() for line in Path("/data/assistant/zalo_admin_users.txt").read_text().splitlines()
                 if line.strip() and not line.startswith("#"))
    tag = "conversion-" + uuid.uuid4().hex
    report_dir = Path(__file__).resolve().parents[2] / "test/reports/run-scoped-notes-documents"
    with tempfile.TemporaryDirectory(prefix=tag + "-", dir="/data/assistant/media/inbound") as temp:
        host = Path(temp)
        relative = host.relative_to("/data/assistant/media")
        worker = Path("/data/media") / relative
        hermes = Path("/opt/data/media") / relative
        code = "from pathlib import Path; from pptx import Presentation; from PIL import Image; p=Path(" + repr(str(worker)) + "); d=Presentation();\n"
        code += "for text in ('First source slide','Second source slide','Third source slide'): d.slides.add_slide(d.slide_layouts[5]).shapes.title.text=text\n"
        code += "d.save(p/'source.pptx'); Image.new('RGB',(640,360),(30,110,175)).save(p/'source.png'); from file_convert import _to_pdf; _to_pdf(p/'source.pptx',p); from openpyxl import Workbook; w=Workbook(); w.remove(w.active);\n"
        code += "for name in ('Alpha','Beta','Gamma'): w.create_sheet(name).append([name+' source value','=1+2'])\n"
        code += "w.save(p/'source.xlsx')"
        subprocess.run(["docker", "exec", "assistant-dispatcher-1", "python", "-B", "-c", code], check=True, capture_output=True)
        cases = [
            ("pptx-to-pdf", "source.pptx", "file", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "chuyển file pptx này thành pdf, giữ nguyên 3 trang; chỉ gửi file pdf", ".pdf", 1, 3),
            ("image-to-pdf", "source.png", "image", "image/png", "chuyển hình này thành một file pdf, giữ nguyên hình; chỉ gửi file pdf", ".pdf", 1, 1),
            ("selected-pdf-pages", "source.pdf", "file", "application/pdf", "chuyển riêng trang 1 và 3 của pdf này thành ảnh PNG, chỉ gửi hai ảnh", ".png", 2, 2),
            ("workbook-to-word", "source.xlsx", "file", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "chuyển tất cả sheet của Excel này sang DOCX. Tôi đồng ý chuyển đổi nội dung, không cần giữ layout, hình hay biểu đồ; giữ công thức dạng văn bản. Chỉ gửi file DOCX", ".docx", 1, None),
            ("quote-pptx-to-pdf", "source.pptx", "file", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "convert this pptx file to pdf; keep its 3 slides and send only the pdf", ".pdf", 1, 3),
            ("quote-workbook-to-word", "source.xlsx", "file", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "chuyển file Excel được trích dẫn này sang DOCX, tất cả sheet. Đồng ý chuyển đổi nội dung và giữ công thức dạng văn bản, không giữ layout hay biểu đồ; chỉ gửi DOCX", ".docx", 1, None),
            ("quote-pptx-to-images", "source.pptx", "file", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "chuyển PPTX được trích dẫn này thành ảnh PNG, mỗi slide một ảnh, đủ cả 3 slide theo đúng thứ tự; chỉ gửi ba ảnh PNG", ".png", 3, 3),
            ("pdf-to-images", "source.pdf", "file", "application/pdf", "chuyển tất cả 3 trang PDF này thành ảnh PNG, mỗi trang một ảnh theo đúng thứ tự; chỉ gửi ba ảnh PNG", ".png", 3, 3),
        ]
        if set(options.case) - {case[0] for case in cases}:
            raise ValueError('unknown conversion case')
        records = []
        for index, (name, filename, kind, mime, text, extension, files_count, pages) in enumerate(cases, 1):
            if options.quotes_only and not name.startswith('quote-'):
                continue
            if options.case and name not in options.case:
                continue
            print(f"running test case {index}/{len(cases)} {name} natural attachment conversion", flush=True)
            source = tag + "-" + str(index)
            event = {"type": "message", "threadId": admin, "threadType": "user", "senderId": admin,
                "senderName": "test-user", "text": text, "messageId": source,
                "media": {"kind": kind, "url": str(hermes / filename), "fileName": filename, "mime": mime}}
            if name.startswith("quote-"):
                # Publish the exact fixture as a separate precondition and use
                # its real acknowledgement ID, not a fabricated quote ID.
                fixture_source = source + "-fixture"
                bind = {"thread_id": admin, "thread_type": "user", "source_message_id": fixture_source}
                send = {"path": str(worker / filename), "thread_id": admin, "thread_type": "user",
                        "source_message_id": fixture_source, "lock_thread": True}
                code = "import json,urllib.request;"
                for url, payload in (("http://session:8107/v1/turn/dest", bind), ("http://dispatcher:8090/v1/send-file", send)):
                    code += "p=" + repr(json.dumps(payload)) + ";q=urllib.request.Request(" + repr(url) + ",data=p.encode(),headers={'Content-Type':'application/json'},method='POST');json.load(urllib.request.urlopen(q));"
                docker_python(code + "print('FIXTURE_ACKNOWLEDGED')")
                fixture_rows = delivered(fixture_source)
                assert len(fixture_rows) == 1 and fixture_rows[0].get("message_id"), "quote_fixture_ack_missing"
                with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=10) as response:
                    own_id = str(json.load(response).get("ownId") or "")
                assert own_id, "quote_fixture_author_missing"
                quoted_id = fixture_rows[0]["message_id"]
                event.pop("media")
                event["quoted"] = {"msgType": "share.file", "uidFrom": own_id, "msgId": quoted_id,
                    "content": {"title": filename, "href": str(hermes / filename), "params": {"fileExt": Path(filename).suffix.lstrip('.') }}}
                # There is no direct attachment. Verify the quoted source's
                # full converted contents below, rather than merely its suffix.
            started = time.time()
            request = urllib.request.Request("http://127.0.0.1:8787/inject-event", data=json.dumps(event, ensure_ascii=False).encode(),
                method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                assert json.load(response).get("ok") is True
            deadline = time.monotonic() + 900
            terminal = False
            settled_since = None
            while time.monotonic() < deadline:
                rows = delivered(source)
                if rows and thread_terminal(admin):
                    settled_since = settled_since or time.monotonic()
                    if time.monotonic() - settled_since >= 6:
                        terminal = True
                        break
                else:
                    settled_since = None
                time.sleep(3)
            rows = delivered(source)
            attachments = [row.get("meta", {}).get("file_name", "") for row in rows if row.get("meta", {}).get("file_name")]
            ok = terminal and len(rows) == files_count and len(attachments) == files_count and all(path.lower().endswith(extension) for path in attachments)
            # Locate only this fixture's private conversion, never an arbitrary
            # newer weather PDF from the same destination.
            pattern = "*/source.pdf" if extension == ".pdf" else "*/page-*.png" if extension == ".png" else "*/converted.docx"
            outputs = list(Path("/data/assistant/media/out/.conversions").glob(pattern))
            outputs = [path for path in outputs if path.stat().st_mtime >= started]
            if ok:
                selected=[]
                for row in rows:
                    receipt_name=str((row.get('meta') or {}).get('file_name') or '')
                    assert receipt_name and Path(receipt_name).name==receipt_name, 'invalid conversion receipt filename'
                    candidates=[path for path in outputs if path.name==receipt_name]
                    selected.append(acknowledged_artifact(candidates,(admin,'user',source),row['message_id']))
                outputs=selected
            if ok and len(outputs) == files_count and extension == ".pdf":
                check = "import pymupdf;d=pymupdf.open(" + repr(str(Path('/data/media') / outputs[0].relative_to('/data/assistant/media'))) + ");print(len(d));print(chr(10).join(p.get_text() for p in d))"
                result = subprocess.run(["docker", "exec", "assistant-dispatcher-1", "python", "-B", "-c", check], text=True, capture_output=True, check=True).stdout
                ok = int(result.splitlines()[0]) == pages
                if name in {"pptx-to-pdf", "quote-pptx-to-pdf"}:
                    ok = ok and all(word in result for word in ("First source slide", "Second source slide", "Third source slide"))
                else:
                    image_check = "import pymupdf;d=pymupdf.open(" + repr(str(Path('/data/media') / outputs[0].relative_to('/data/assistant/media'))) + ");print(int(bool(d[0].get_image_info())))"
                    ok = ok and subprocess.check_output(["docker", "exec", "assistant-dispatcher-1", "python", "-B", "-c", image_check], text=True).strip() == "1"
            elif ok and len(outputs) == files_count and extension == ".png":
                expected_names = {"page-001.png", "page-003.png"} if name == "selected-pdf-pages" else {"page-001.png", "page-002.png", "page-003.png"}
                ok = {path.name for path in outputs} == expected_names and attachments == sorted(expected_names)
                # Compare the pixels against the selected original PDF pages
                # at each output's actual size. Correct names alone do not
                # establish that the right pages were converted.
                for output in outputs:
                    page_index = int(output.stem.split('-')[-1]) - 1
                    path = str(Path('/data/media') / output.relative_to('/data/assistant/media'))
                    check = "import pymupdf;from PIL import Image,ImageChops;d=pymupdf.open(" + repr(str(worker / 'source.pdf')) + ");a=Image.open(" + repr(path) + ").convert('RGB');p=d[" + str(page_index) + "];b=p.get_pixmap(matrix=pymupdf.Matrix(a.width/p.rect.width,a.height/p.rect.height),alpha=False);b=Image.frombytes('RGB',(b.width,b.height),b.samples);print(int(a.size==b.size and ImageChops.difference(a,b).getbbox() is None))"
                    ok = ok and subprocess.check_output(["docker", "exec", "assistant-dispatcher-1", "python", "-B", "-c", check], text=True).strip() == "1"
            elif ok and len(outputs) == files_count and extension == ".docx":
                path = str(Path('/data/media') / outputs[0].relative_to('/data/assistant/media'))
                check = "from docx import Document;d=Document(" + repr(path) + ");print(chr(10).join([p.text for p in d.paragraphs]+[c.text for t in d.tables for r in t.rows for c in r.cells]))"
                result = subprocess.check_output(["docker", "exec", "assistant-dispatcher-1", "python", "-B", "-c", check], text=True)
                ok = all(word in result for word in ("Alpha source value", "Beta source value", "Gamma source value", "=1+2"))
            else:
                ok = False
            record = {"name": name, "source": source, "terminal": terminal, "delivery_count": len(rows),
                "attachments": attachments, "expected_pages": pages, "result": "PASS" if ok else "FAIL"}
            if name.startswith("quote-"):
                record["quoted_fixture_acknowledged"] = True
                record["quoted_only_input"] = True
                record["incoming_quote_context"] = "injected"
                record["native_client_quote_input_verified"] = False
                record["outbound_file_quoted"] = any(row.get("meta", {}).get("quoted") is True for row in rows)
            records.append(record)
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "conversion-chat-report.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(record), flush=True)
            if not ok:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
