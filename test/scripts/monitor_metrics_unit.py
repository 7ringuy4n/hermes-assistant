#!/usr/bin/env python3
"""Unit: Grafana consolidation and the metrics surfaced on the overview."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "config" / "monitor" / "grafana" / "dashboards" / "json"
PROM = ROOT / "config" / "monitor" / "prometheus.yml"
TRAEFIK = ROOT / "architect" / "edge" / "traefik"
STACK_EXPORTER = ROOT / "architect" / "monitor" / "stack-exporter" / "app.py"
RW = ROOT / "architect" / "models" / "router-worker"

REQUIRED_OVERVIEW_EXPRS = [
    "traefik_entrypoint_requests_total",
    "traefik_entrypoint_request_duration_seconds_bucket",
    "router_worker_llm_latency_seconds_bucket",
    "omnirouter_prompt_tokens_total",
    "router_worker_llm_requests_total",
    "router_worker_router_selection_total",
    "router_worker_provider_fallback_total",
    "assistant_queue_depth",
    "assistant_qdrant_query_seconds",
    "assistant_schedule_lag_seconds",
]


def main() -> int:
    files = sorted(p.name for p in DASH.glob("*.json"))
    assert files == ["assistant-logs.json", "assistant-overview.json"], files

    overview = json.loads((DASH / "assistant-overview.json").read_text(encoding="utf-8"))
    logs = json.loads((DASH / "assistant-logs.json").read_text(encoding="utf-8"))
    exprs = "\n".join(
        str(t.get("expr"))
        for p in overview["panels"]
        for t in (p.get("targets") or [])
    )
    for expr in REQUIRED_OVERVIEW_EXPRS:
        assert expr in exprs, expr

    # Merged file-flow pipeline log panels now live on the logs dashboard.
    log_exprs = "\n".join(
        str(t.get("expr")) for p in logs["panels"] for t in (p.get("targets") or [])
    )
    assert "[flow]" in log_exprs

    # Layout: role sections (rows) with panels packed side by side inside each.
    section_titles = [p.get("title") for p in overview["panels"] if p.get("type") == "row"]
    for required in (
        "Stack health",
        "Traffic (Traefik)",
        "Hardware",
        "OmniRoute LLM usage",
        "Routing, queues & latency",
    ):
        assert required in section_titles, required
    types = [p.get("type") for p in overview["panels"]]
    for i, kind in enumerate(types):
        if kind == "row":
            assert i + 1 < len(types) and types[i + 1] != "row", "empty section"
    for dash in (overview, logs):
        xs = {
            p["gridPos"]["x"]
            for p in dash["panels"]
            if p.get("gridPos") and p.get("type") != "row"
        }
        assert len(xs) > 1, "panels must not be stacked in one column"
        for p in dash["panels"]:
            gp = p["gridPos"]
            assert gp["x"] + gp["w"] <= 24, p.get("title")

    # Traefik by-label series render as {label="value"} in the legend.
    legends = "\n".join(
        str(t.get("legendFormat")) for p in overview["panels"] for t in (p.get("targets") or [])
    )
    for fmt in ('{entrypoint="{{entrypoint}}"}', '{service="{{service}}"}', '{router="{{router}}"}'):
        assert fmt in legends, fmt

    prom = PROM.read_text(encoding="utf-8")
    assert "job_name: router-worker" in prom
    assert "job_name: traefik" in prom
    assert "router-worker:8096" in prom
    assert "traefik:8082" in prom

    for name in ("traefik.yml", "traefik.acme.yml"):
        text = (TRAEFIK / name).read_text(encoding="utf-8")
        assert "prometheus:" in text and "entryPoint: metrics" in text, name
        assert "address: \":8082\"" in text, name

    se = STACK_EXPORTER.read_text(encoding="utf-8")
    for metric in ("assistant_qdrant_query_seconds", "assistant_queue_depth", "assistant_schedule_lag_seconds"):
        assert metric in se, metric

    assert (RW / "metrics.py").is_file()
    app_src = (RW / "app.py").read_text(encoding="utf-8")
    assert '@app.get("/metrics")' in app_src

    print("monitor_metrics_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
