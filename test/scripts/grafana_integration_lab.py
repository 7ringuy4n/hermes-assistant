# -*- coding: utf-8 -*-
"""Grafana integration lab (SSH). Skip when ENABLE_GRAFANA=0.

Env: ASSISTANT_SSH_HOST, ASSISTANT_SSH_USER, ASSISTANT_SSH_PASSWORD
Reports: test/reports/run-grafana-integration/ (no host/account)
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_stack import LOCAL_MODE, connect, sudo_bash  # noqa: E402
from sanitize import sanitize

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ASSISTANT_REPO_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "test" / "reports" / "run-grafana-integration"
ROWS: list[dict] = []


def metric_not_up(line: str) -> bool:
    """Gauges serialize as 0 or 0.0; missing/invalid values fail closed."""
    try:
        return float(line.rsplit(None, 1)[-1]) != 1.0
    except (ValueError, IndexError):
        return True


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def note(name: str, status: str, detail: str = "") -> None:
    row = {"ts": ts(), "name": name, "status": status, "detail": sanitize(detail)[:800]}
    ROWS.append(row)
    print(f"[{row['ts']}] {name} | {status} | {row['detail'][:240]}", flush=True)


def main() -> int:
    if not LOCAL_MODE and not os.environ.get("ASSISTANT_SSH_HOST"):
        print("SKIP: set ASSISTANT_SSH_* to run the lab")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    c = connect()
    try:
        out = sudo_bash(
            c,
            r"""
set -euo pipefail
export LC_ALL=C.UTF-8
cd /opt/assistant
set -a; . ./.env; set +a
echo "GRAFANA=${ENABLE_GRAFANA:-0}"
echo "PROMETHEUS=${ENABLE_PROMETHEUS:-0}"
echo "OMNI=${ENABLE_OMNIROUTER:-0}"
echo "AV=${ENABLE_ANTIVIRUS:-0}"
echo "ZALO=${ENABLE_ZALO:-0}"
echo "NOTIFY=${ENABLE_NOTIFY:-1}"
echo "ALERT_WATCH=${ENABLE_ALERT_WATCH:-1}"
case "${ENABLE_GRAFANA:-0}:${ENABLE_PROMETHEUS:-0}" in
  active:*|1:*|*:active|*:1) ;;
  *)
  echo SKIP_GRAFANA_OFF
  exit 0
  ;;
esac
echo "grafana_health=$(curl -sS -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:23000/api/health || echo fail)"
curl -sS -m 8 http://127.0.0.1:23000/api/health || true
echo
echo '=== PROM_TARGETS ==='
stack_exporter=$(docker ps -q --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-assistant}" --filter label=com.docker.compose.service=stack-exporter)
test -n "$stack_exporter"
docker exec "$stack_exporter" python -c '
import json, urllib.request
d=json.loads(urllib.request.urlopen("http://prometheus:9090/api/v1/targets", timeout=8).read().decode())
for t in (d.get("data") or {}).get("activeTargets") or []:
    job=(t.get("labels") or {}).get("job","")
    health=t.get("health","")
    err=(t.get("lastError") or "")[:60]
    print(f"TARGET job={job} health={health} err={err}")
'
echo '=== SERVICE_UP ==='
docker exec "$stack_exporter" python -c '
import urllib.request
t=urllib.request.urlopen("http://127.0.0.1:9102/metrics", timeout=8).read().decode()
for line in t.splitlines():
    if line.startswith("assistant_service_up"):
        print(line)
'
if [[ "${ENABLE_OMNIROUTER:-0}" == "1" || "${ENABLE_OMNIROUTER:-0}" == "active" ]]; then
  echo '=== OMNI ==='
  omni_exporter=$(docker ps -q --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME:-assistant}" --filter label=com.docker.compose.service=omni-exporter)
  test -n "$omni_exporter"
  docker exec "$omni_exporter" python -c '
import urllib.request
t=urllib.request.urlopen("http://127.0.0.1:9104/metrics", timeout=8).read().decode()
for line in t.splitlines():
    if line.startswith("omnirouter_scrape_success"):
        print(line)
' 2>/dev/null || echo OMNI_EXPORTER_ABSENT
fi
echo GRAFANA_LAB_DONE
""",
            timeout=90,
        )
        if "SKIP_GRAFANA_OFF" in out:
            note("grafana", "SKIP", "ENABLE_GRAFANA/PROMETHEUS off")
            return 0
        fails = 0
        if "GRAFANA_LAB_DONE" not in out:
            note("lab", "FAIL", "missing GRAFANA_LAB_DONE")
            return 1
        if "grafana_health=200" not in out:
            note("grafana_ui", "FAIL", "Grafana /api/health not 200")
            fails += 1
        else:
            note("grafana_ui", "PASS", "health 200")
        down = [
            line
            for line in out.splitlines()
            if line.startswith("assistant_service_up") and metric_not_up(line)
        ]
        active = {line.partition("=")[0]: line.partition("=")[2].strip().lower() in {"1", "active", "true", "yes", "on"}
                  for line in out.splitlines() if "=" in line and line.partition("=")[0] in {"AV", "ZALO", "OMNI", "NOTIFY", "ALERT_WATCH"}}
        real_down = []
        for d in down:
            if any(name in d for name in ("av-gateway", "clamav")) and not active.get("AV"):
                continue
            if "notify" in d and not active.get("NOTIFY"):
                continue
            if "alert-watch" in d and not active.get("ALERT_WATCH"):
                continue
            if "zalo-api" in d and not active.get("ZALO"):
                continue
            if "omni-router" in d and not active.get("OMNI"):
                continue
            real_down.append(d)
        if real_down:
            note("service_up", "FAIL", "; ".join(real_down)[:400])
            fails += 1
        else:
            note("service_up", "PASS", "expected services up")
        failed_targets = [line for line in out.splitlines() if line.startswith("TARGET ") and "health=up" not in line]
        if failed_targets:
            note("prometheus_targets", "FAIL", "; ".join(failed_targets)[:400])
            fails += 1
        if active.get("OMNI"):
            gauges = [line for line in out.splitlines() if line.startswith("omnirouter_scrape_success ")]
            if len(gauges) != 1 or metric_not_up(gauges[0]):
                note("omni", "FAIL", "omni scrape missing or unhealthy")
                fails += 1
            else:
                note("omni", "PASS", "omni scrape")
        path = OUT / f"grafana-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps({"rows": ROWS, "fails": fails}, indent=2), encoding="utf-8")
        print(f"report={path.relative_to(ROOT)}")
        return 1 if fails else 0
    finally:
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())

