"""Actual short-delay schedule persists a direct note, with no Zalo delivery."""
from datetime import datetime, timedelta, timezone
import json
import subprocess
import time
import uuid


def main():
    sid = "standalone-qa-" + uuid.uuid4().hex
    marker = "Sample scheduled note " + uuid.uuid4().hex
    scope = "hermes:local"
    ids = []

    def request(service, method, path, body=None):
        code = "import json,urllib.request; body=" + repr(json.dumps(body) if body is not None else None) + "; req=urllib.request.Request(" + repr(service + path) + ",data=body.encode() if body is not None else None,method=" + repr(method) + ",headers={'Content-Type':'application/json'}); print(urllib.request.urlopen(req,timeout=15).read().decode())"
        result = subprocess.run(["docker", "exec", "assistant-hermes-1", "python", "-B", "-c", code], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError("standalone_schedule_transport_failed")
        return json.loads(result.stdout)

    try:
        print("running test case 1/2 create direct schedule without messaging destination", flush=True)
        due = datetime.now(timezone.utc) + timedelta(seconds=30)
        request("http://schedule-worker:8110", "POST", "/v1/schedules", {
            "id": sid, "name": marker, "text": "Sample direct task", "cadence": "once", "enabled": True,
            "cron_expr": f"{due.minute} {due.hour} {due.day} {due.month} *",
            "timezone": "UTC", "next_run_at": due.isoformat(),
            "origin": {"platform": "hermes"}, "context": {},
            "fire_text": "Use the notes skill direct command to save exactly one note. Title: " + marker + ". Content: Sample scheduled technical idea. Do not send anything to Zalo or run any other task."})
        print("running test case 2/2 actual due fire runs Hermes and persists direct note", flush=True)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            result = request("http://memory:8095", "POST", "/v1/notes/query", {"scope_id": scope, "query": marker, "limit": 10})
            ids = [row["id"] for row in result.get("items", [])]
            if ids:
                assert len(ids) == 1
                print("PASS actual standalone scheduled note", flush=True)
                return
            time.sleep(3)
        raise RuntimeError("standalone_scheduled_note_not_observed")
    finally:
        request("http://schedule-worker:8110", "DELETE", "/v1/schedules/" + sid)
        for note_id in ids:
            request("http://memory:8095", "DELETE", "/v1/notes/" + note_id + "?scope_id=" + scope)


if __name__ == "__main__":
    main()
