"""Real scanner verdicts and Dispatcher scan-before-parse; no message delivery."""
import ast
import json
import os
from pathlib import Path
import tempfile
import subprocess
import time
import urllib.request
import urllib.error
import uuid


def request(url, body=None, content_type=None):
    req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type} if content_type else {})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def scan(data, label):
    sid = "av-lab-" + uuid.uuid4().hex
    boundary = "fixture" + uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="session_id"\r\n\r\n{sid}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{label}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    result = request("http://127.0.0.1:8098/v1/scan", body, "multipart/form-data; boundary=" + boundary)
    for _ in range(60):
        status = request("http://127.0.0.1:8098/v1/sessions/" + sid + "/ready")
        if status["ready"] or status["blocked"]:
            return result["file_id"], status
        time.sleep(0.25)
    raise AssertionError("scanner verdict timeout")


def main():
    checks = []
    assert request("http://127.0.0.1:8098/health")["clamd"] is True
    print("running test case 1/6 ClamAV is actually ready: PASS", flush=True)
    _, clean = scan(b"Harmless antivirus verification fixture.\n", "clean.txt")
    assert clean["ready"] and not clean["blocked"]
    print("running test case 2/6 harmless file has a clean verdict: PASS", flush=True)
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    fid, blocked = scan(eicar, "eicar-test.txt")
    assert blocked["blocked"] and blocked["infected"] == 1 and not blocked["ready"]
    print("running test case 3/6 EICAR is blocked by the actual engine: PASS", flush=True)
    _, fresh = scan(b"Clean subsequent file.\n", "clean-again.txt")
    assert fresh["ready"] and not fresh["blocked"]
    print("running test case 4/6 infected verdict does not poison a fresh file: PASS", flush=True)
    media = Path("/data/assistant/media/inbound")
    with tempfile.TemporaryDirectory(prefix="av-lab-", dir=media) as temp:
        source = Path(temp) / ("av-lab-" + uuid.uuid4().hex + ".pdf")
        source.write_bytes(eicar)
        body = json.dumps({"source_path": str(source), "output_type": "png"}).encode()
        try:
            request("http://127.0.0.1:8090/v1/file-convert", body, "application/json")
            raise AssertionError("infected conversion source accepted")
        except urllib.error.HTTPError as exc:
            assert exc.code == 403, exc.read().decode()
    print("running test case 5/6 direct conversion blocks infected input before parsing: PASS", flush=True)
    containers = subprocess.check_output(["docker", "ps", "-q", "--filter", "label=com.docker.compose.service=dispatcher", "--filter", "label=com.docker.compose.project=assistant"], text=True).split()
    assert len(containers) == 1
    code = '''import os, tempfile
from pathlib import Path
from app import _outbound_av_scan
os.environ.update(AV_SCAN="active", AV_REQUIRED="active", AV_GATEWAY_URL="http://127.0.0.1:1", SECURITY_URL="")
with tempfile.NamedTemporaryFile() as fixture:
    fixture.write(b"Harmless outage fixture"); fixture.flush()
    assert _outbound_av_scan(Path(fixture.name), "fixture", "fixture.txt") == "blocked"
'''
    subprocess.run(["docker", "exec", containers[0], "python3", "-c", code], check=True)
    print("running test case 6/6 actual outbound policy blocks an unavailable scanner: PASS", flush=True)
    # Do not delete general quarantine contents. Report the exact known fixture
    # for the lab operator's validated cleanup; no identity or credential output.
    print("EICAR_QUARANTINE_FIXTURE=" + fid + "_eicar-test.txt", flush=True)
    print("CONVERSION_QUARANTINE_FIXTURE_BASENAME=" + source.name, flush=True)


if __name__ == "__main__":
    main()
