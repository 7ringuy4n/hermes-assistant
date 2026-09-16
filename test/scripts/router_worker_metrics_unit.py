#!/usr/bin/env python3
"""Unit: Router Worker Prometheus metrics surface."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RW = ROOT / "architect" / "models" / "router-worker"


def _load():
    spec = importlib.util.spec_from_file_location("rw_metrics_unit", RW / "metrics.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    m = _load()
    m.observe(capability="normal", provider="omni-router", model="hermes", status="ok", seconds=0.3)
    m.observe(capability="normal", provider="fallback-openai", model="gpt-4o-mini", status="ok", seconds=1.5)
    m.observe(capability="classify", provider="omni-router", model="classifier", status="error", seconds=0.05)
    m.fallback(from_provider="omni-router", to_provider="fallback-openai")
    out = m.render()

    assert "# TYPE router_worker_llm_latency_seconds histogram" in out
    assert 'router_worker_llm_requests_total{capability="normal",provider="omni-router",status="ok"} 1' in out
    assert 'router_worker_llm_requests_total{capability="classify",provider="omni-router",status="error"} 1' in out
    assert 'router_worker_router_selection_total{provider="omni-router",model="hermes"} 1' in out
    assert 'router_worker_provider_fallback_total{from_provider="omni-router",to_provider="fallback-openai"} 1' in out
    # histogram cumulative buckets end at +Inf == count, and exclude the error sample
    assert 'router_worker_llm_latency_seconds_bucket{capability="normal",le="0.5"} 1' in out
    assert 'router_worker_llm_latency_seconds_bucket{capability="normal",le="+Inf"} 2' in out
    assert 'router_worker_llm_latency_seconds_count{capability="normal"} 2' in out
    assert 'router_worker_llm_latency_seconds_count{capability="classify"} 1' in out

    app_src = (RW / "app.py").read_text(encoding="utf-8")
    assert "import metrics as metrics_mod" in app_src
    assert '@app.get("/metrics")' in app_src
    assert '@app.middleware("http")' in app_src
    # /metrics must be registered before the path catch-all.
    assert app_src.index('@app.get("/metrics")') < app_src.index('@app.api_route("/{path:path}"')
    # The image must ship the metrics module or the app crash-loops on import.
    dockerfile = (RW / "Dockerfile").read_text(encoding="utf-8")
    assert "metrics.py" in dockerfile
    assert 'capability="classify"' in app_src
    assert 'capability="outbound"' in app_src

    print("router_worker_metrics_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
