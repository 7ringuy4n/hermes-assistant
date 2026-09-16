"""VPS-local real-plugin gate; artifact quality still requires visual review.

Run on the authorized lab host. Uses the existing admin identity at runtime,
creates three marker-bound note fixtures, and removes only those exact records.
No provider/combo changes. Reports omit conversation and account identifiers.
"""
from __future__ import annotations
import json
import argparse
import os
import subprocess
import time
import urllib.request
import uuid
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "test/reports/run-scoped-notes-documents"


def acknowledged_artifact(candidates, binding, message_id):
    """Read-only content-bound wire receipt; never select arbitrary newer drafts."""
    sys.path.insert(0, str(ROOT / "architect/lib"))
    from artifact_delivery import artifact_key
    thread_id, thread_type, source_id = binding
    keyed = {artifact_key(path, thread_id, thread_type, source_id): path for path in sorted(candidates)}
    names = subprocess.check_output(['docker', 'ps', '--filter', 'label=com.docker.compose.service=session',
                                     '--format', '{{.Names}}'], text=True).splitlines()
    if len(names) != 1:
        raise RuntimeError('delivery_receipt_service_ambiguous')
    probe = '''
import app,json,os
selected=[]
for key in json.loads(os.environ['LAB_KEYS']):
 record=json.loads(app.r.get(app.SENTFILE_PREFIX+':v2:'+key) or '{}')
 if (record.get('state')=='acknowledged' and str(record.get('message_id'))==os.environ['LAB_MESSAGE']
     and record.get('thread_id')==os.environ['LAB_THREAD'] and record.get('thread_type')==os.environ['LAB_TYPE']
     and record.get('source_message_id')==os.environ['LAB_SOURCE']):
  selected.append(key)
print(json.dumps(selected))
'''
    raw = subprocess.check_output(['docker','exec','-e','LAB_KEYS='+json.dumps(list(keyed)),
        '-e','LAB_THREAD='+thread_id,'-e','LAB_TYPE='+thread_type,'-e','LAB_SOURCE='+source_id,
        '-e','LAB_MESSAGE='+str(message_id),names[0],'python3','-c',probe],text=True)
    selected = json.loads(raw)
    if len(selected) != 1:
        raise RuntimeError('delivered_artifact_identity_unproven')
    return keyed[selected[0]]


def docker_python(code: str) -> str:
    result = subprocess.run(["docker", "exec", "assistant-hermes-1", "python", "-B", "-c", code],
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("lab_container_probe_failed")
    return result.stdout.strip()


def delivered(marker: str) -> list[dict]:
    sql = "SELECT coalesce(json_agg(t),'[]'::json) FROM (SELECT content,meta,message_id FROM zalo_message_history WHERE event='delivered' AND meta->>'source_message_id'='" + marker + "' ORDER BY id) t;"
    result = subprocess.run(["docker", "exec", "postgres", "psql", "-U", "hermes", "-d", "hermes_memory", "-At", "-c", sql], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("lab_delivery_audit_unavailable")
    return json.loads(result.stdout.strip() or "[]")


def thread_terminal(thread_id: str) -> bool:
    """Queue ACK alone is not completion of a delegated gateway job."""
    code = "import sys; sys.path.insert(0,'/opt/data/plugins/zalo'); from gate_valkey import GateStore; s=GateStore.from_env(); t=" + repr(thread_id) + "; print(int(s is not None and s.queue_len(t)==0 and int(s._r.call('LLEN',s._k('qinflight',t)) or 0)==0))"
    if docker_python(code) != "1":
        return False
    # Query each currently running replica, not archived hostname directories.
    probe = "import sys,socket; from pathlib import Path; sys.path.insert(0,'/opt/hermes'); from hermes_cli.active_sessions import active_session_registry_snapshot; t=" + repr(thread_id) + "; entries=active_session_registry_snapshot(Path('/opt/data/replicas')/socket.gethostname(),strict=True); print(int(not any(str((e.get('metadata') or {}).get('chat_id') or '').split('::job::',1)[0]==t for e in entries)))"
    for replica in ("assistant-hermes-1", "assistant-hermes-2"):
        result = subprocess.run(["docker", "exec", replica, "python", "-B", "-c", probe], text=True, capture_output=True)
        if result.returncode or result.stdout.strip() != "1":
            return False
    return True


def ensure_ready() -> None:
    """Reject an invalid bridge lab instead of counting injection as execution."""
    with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=10) as response:
        state = json.load(response)
    if state.get("ok") is not True or state.get("loggedIn") is not True or int(state.get("sseClients") or 0) < 1:
        raise RuntimeError("lab_bridge_not_ready")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents-only", action="store_true")
    parser.add_argument("--pdf-only", action="store_true")
    parser.add_argument("--pptx-only", action="store_true")
    options = parser.parse_args()
    ensure_ready()
    OUT.mkdir(parents=True, exist_ok=True)
    admin = ""
    for line in Path("/data/assistant/zalo_admin_users.txt").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            admin = line.partition("|")[0].strip()
            break
    if not admin:
        raise RuntimeError("lab_admin_identity_unavailable")
    marker = "scope-docs-" + uuid.uuid4().hex
    scope = "zalo:user:" + admin
    fixtures = [
        {"title": "Sample Java vacancy", "content": marker + " Recruitment for backend Java at Sample Company."},
        {"title": "Sample TypeScript vacancy", "content": marker + " Recruitment for frontend TypeScript at Sample Company."},
        {"title": "Sample Java design idea", "content": marker + " Personal technical idea about Java concurrency; not a job opening."},
    ]
    ids = []
    report = {"baseline": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cases": []}
    try:
        for fixture in ([] if options.documents_only or options.pdf_only or options.pptx_only else fixtures):
            payload = {**fixture, "scope_id": scope, "owner_id": admin, "thread_id": admin, "thread_type": "user", "metadata": {"test_marker": marker}}
            code = "import json,urllib.request; p=" + repr(json.dumps(payload)) + "; q=urllib.request.Request('http://memory:8095/v1/notes',data=p.encode(),headers={'Content-Type':'application/json'},method='POST'); d=json.load(urllib.request.urlopen(q)); print(d['note']['id'])"
            ids.append(docker_python(code))
        cases = [
            ("exclude-java-recruitment", f"tìm các note có marker {marker} không phải tin tuyển dụng Java", {fixtures[1]["title"], fixtures[2]["title"]}, {fixtures[0]["title"]}),
            ("exclude-all-recruitment", f"tìm các note có marker {marker} không phải tin tuyển dụng", {fixtures[2]["title"]}, {fixtures[0]["title"], fixtures[1]["title"]}),
            ("visual-pdf", "tạo file pdf về thời tiết hồ chí minh hiện tại, font đẹp, background hợp lý có hình ảnh minh họa và icon, nội dung tiếng Việt", set(), set()),
            ("visual-pptx", "tạo file thuyết trình pptx 3 trang về thời tiết hồ chí minh hiện tại, font đẹp và background hợp lý có hình ảnh, nội dung tiếng Việt; chỉ gửi một file pptx", set(), set()),
        ]
        if options.documents_only:
            cases = cases[2:]
        if options.pdf_only:
            cases = [case for case in cases if case[0] == "visual-pdf"]
        if options.pptx_only:
            cases = [case for case in cases if case[0] == "visual-pptx"]
        for index, (name, text, required, forbidden) in enumerate(cases, 1):
            print(f"running test case {index}/{len(cases)} {name}", flush=True)
            source = marker + "-" + str(index)
            event = {"type": "message", "threadId": admin, "threadType": "user", "senderId": admin, "senderName": "test-user", "text": text, "messageId": source}
            request = urllib.request.Request("http://127.0.0.1:8787/inject-event", data=json.dumps(event, ensure_ascii=False).encode(), method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if json.load(response).get("ok") is not True:
                    raise RuntimeError("lab_plugin_injection_failed")
            rows = []
            deadline = time.monotonic() + int(os.environ.get("LAB_CASE_TIMEOUT_S", "900"))
            terminal = False
            settled_since = None
            while time.monotonic() < deadline:
                rows = delivered(source)
                # The first attachment is not terminal: an agent may still
                # generate drafts or send additional artifacts afterwards.
                if rows and thread_terminal(admin):
                    settled_since = settled_since or time.monotonic()
                    if time.monotonic() - settled_since >= 6:
                        terminal = True
                        break
                else:
                    settled_since = None
                time.sleep(3)
            rows = delivered(source)
            bodies = "\n".join(str(row.get("content") or "") for row in rows)
            attachments = [str(row.get("meta", {}).get("file_name") or "") for row in rows if row.get("meta", {}).get("file_name")]
            visual = name.startswith("visual-")
            ok = terminal and bool(rows) and all(word in bodies for word in required) and not any(word in bodies for word in forbidden)
            if visual:
                extension = ".pdf" if name == "visual-pdf" else ".pptx"
                ok = terminal and len(rows) == 1 and len(attachments) == 1 and attachments[0].lower().endswith(extension)
            record = {"name": name, "source": source, "delivery_count": len(rows), "attachments": attachments,
                      "terminal": terminal, "result": "DELIVERY_PASS_VISUAL_PENDING" if ok and visual else "PASS" if ok else "FAIL"}
            if not visual:
                record["reply"] = bodies.replace(admin, "<runtime-admin>")
            report["cases"].append(record)
            (OUT / "live-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(record, ensure_ascii=False), flush=True)
            if not ok:
                return 1
        return 0
    finally:
        for note_id in ids:
            code = "import urllib.request,urllib.parse; u='http://memory:8095/v1/notes/'+" + repr(note_id) + "+'?scope_id='+urllib.parse.quote(" + repr(scope) + ",safe=''); urllib.request.urlopen(urllib.request.Request(u,method='DELETE')).close()"
            docker_python(code)


if __name__ == "__main__":
    raise SystemExit(main())
