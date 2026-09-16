# -*- coding: utf-8 -*-
"""File/vision/YARA/AV matrix lab (SSH, separate from other labs).

Env: ASSISTANT_SSH_HOST, ASSISTANT_SSH_USER, ASSISTANT_SSH_PASSWORD
Reports: test/reports/run-file-pipeline-security/ (no host/account)
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_stack import LOCAL_MODE, connect, sudo_bash
from sanitize import sanitize

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOST = os.environ.get("ASSISTANT_SSH_HOST", "")
USER = os.environ.get("ASSISTANT_SSH_USER", "")
ROOT = Path(os.environ.get("ASSISTANT_REPO_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "test" / "reports" / "run-file-pipeline-security"
ROWS: list[dict] = []

EICAR = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def note(name: str, status: str, detail: str = "") -> None:
    row = {"ts": ts(), "name": name, "status": status, "detail": sanitize(detail)[:800]}
    ROWS.append(row)
    print(f"[{row['ts']}] {name} | {status} | {row['detail'][:240]}", flush=True)


def matrix_checks(output: str) -> dict[str, bool]:
    """Require actual scanner verdicts; 'infected':0 is not infection proof."""
    probes = {}
    ready = []
    for line in output.splitlines():
        if line.startswith("PROBE "):
            head, _, body = line.partition(" body=")
            fields = head.split()
            try:
                probes[fields[1]] = (fields[2] == "code=200", json.loads(body))
            except (ValueError, IndexError):
                continue
        elif line.startswith("AV_READY "):
            try:
                ready.append(json.loads(line.partition(" body=")[2]))
            except ValueError:
                continue
    def verdict(name, expected):
        valid, result = probes.get(name, (False, {}))
        av = (result.get("layers") or {}).get("antivirus") or {}
        return valid and result.get("verdict") == expected and av.get("skipped") is not True and av.get("ok") is (expected == "CLEAN")
    return {
        "security_clean_active_av": verdict("sm-clean", "CLEAN"),
        "security_eicar_active_av": verdict("sm-eicar", "RISK"),
        "av_upload_accepted": probes.get("av-eicar", (False, {}))[0],
        "av_eicar_verdict": any(row.get("ready") is False and row.get("blocked") is True
            and row.get("status") == "BLOCKED" and int(row.get("infected") or 0) > 0
            and int(row.get("scanning") or 0) == 0 for row in ready),
        "vision_route_health": "VISION_ROUTE_HEALTH=up" in output.splitlines(),
    }


def main() -> int:
    if not LOCAL_MODE and (not HOST or not USER):
        print("SKIP: set ASSISTANT_SSH_HOST, ASSISTANT_SSH_USER, ASSISTANT_SSH_PASSWORD")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    c = connect()
    script = r'''
set -euo pipefail
export LC_ALL=C.UTF-8
cd /opt/assistant
set -a; . ./.env; set +a
SM_PORT="${SECURITY_PORT:-8093}"
AV_PORT="${AV_GATEWAY_PORT:-8098}"
ROUTER_WORKER_PORT="${ROUTER_WORKER_PORT:-8096}"
lab_dir=$(mktemp -d /tmp/hermes-security-matrix.XXXXXX)
trap 'rm -f "$lab_dir"/eicar.com "$lab_dir"/clean.txt "$lab_dir"/fps-*.json; rmdir "$lab_dir"' EXIT
lab_tag="${lab_dir##*/}"
printf '%s' 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > "$lab_dir/eicar.com"
printf 'hello clean lab19\n' > "$lab_dir/clean.txt"

probe_file() {
  name="$1"; url="$2"; f="$3"
  code=$(curl -sS -m 90 -o "$lab_dir/fps-$name.json" -w "%{http_code}" \
    -X POST "$url" -F "session_id=$lab_tag-$name" -F "file=@$f" || echo 000)
  body=$(cat "$lab_dir/fps-$name.json" 2>/dev/null || true)
  echo "PROBE $name code=$code body=$body"
}

if curl -sf -m 5 "http://127.0.0.1:${SM_PORT}/health" >/dev/null 2>&1; then
  probe_file sm-clean "http://127.0.0.1:${SM_PORT}/v1/scan" "$lab_dir/clean.txt"
  probe_file sm-eicar "http://127.0.0.1:${SM_PORT}/v1/scan" "$lab_dir/eicar.com"
else
  echo "PROBE sm-clean code=SKIP body=security-manager not running"
  echo "PROBE sm-eicar code=SKIP body=security-manager not running"
fi

if curl -sf -m 5 "http://127.0.0.1:${AV_PORT}/health" >/dev/null 2>&1; then
  probe_file av-eicar "http://127.0.0.1:${AV_PORT}/v1/scan" "$lab_dir/eicar.com"
  for i in $(seq 1 24); do
    ready=$(curl -sS -m 8 "http://127.0.0.1:${AV_PORT}/v1/sessions/$lab_tag-av-eicar/ready" || true)
    echo "AV_READY i=$i body=$ready"
    echo "$ready" | python3 -c 'import json,sys; r=json.load(sys.stdin); raise SystemExit(0 if r.get("blocked") is True and int(r.get("scanning") or 0)==0 else 1)' && break
    sleep 2
  done
else
  echo "PROBE av-eicar code=SKIP body=av-gateway not running"
fi

if grep -qE '^SECURITY_URL=.+' /opt/assistant/.env /data/assistant/.env 2>/dev/null; then
  echo "INGEST_SECURITY_URL=set"
else
  echo "INGEST_SECURITY_URL=unset"
fi

if curl -sf -m 5 "http://127.0.0.1:${ROUTER_WORKER_PORT}/health" >/dev/null 2>&1; then
  echo "VISION_ROUTE_HEALTH=up"
else
  echo "VISION_ROUTE_HEALTH=down"
fi
'''
    try:
        out = sudo_bash(c, script)
    finally:
        c.close()
    checks = matrix_checks(out)
    fails = sum(not passed for passed in checks.values())
    for index, (name, passed) in enumerate(checks.items(), 1):
        print(f"running test case {index}/{len(checks)}: {name}", flush=True)
        note(name, "PASS" if passed else "FAIL")

    path = OUT / f"matrix-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps({"rows": ROWS, "fails": fails}, indent=2), encoding="utf-8")
    print(f"report={path.relative_to(ROOT)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
