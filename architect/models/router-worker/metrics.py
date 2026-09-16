"""In-process Prometheus metrics for Router Worker (stdlib only).

Exposes the LLM routing signals the Grafana overview needs without adding a
dependency or touching the request/response contract:

- ``router_worker_llm_requests_total{capability,provider,status}``
- ``router_worker_llm_latency_seconds`` (histogram by capability)
- ``router_worker_router_selection_total{provider,model}``
- ``router_worker_provider_fallback_total{from_provider,to_provider}``

Token counters live in OmniRoute (``omnirouter_*_tokens_total``); this module
does not duplicate them.
"""
from __future__ import annotations

import threading

_LOCK = threading.Lock()
_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0, 180.0)

# key: (metric, tuple(labels)) -> value
_COUNTERS: dict[tuple, float] = {}
# capability -> list of non-cumulative bucket hits; +Inf tracked by _count
_HIST: dict[str, list[int]] = {}
_HIST_SUM: dict[str, float] = {}
_HIST_COUNT: dict[str, int] = {}


def _inc(metric: str, labels: tuple[tuple[str, str], ...]) -> None:
    key = (metric, labels)
    _COUNTERS[key] = _COUNTERS.get(key, 0.0) + 1.0


def observe(
    *,
    capability: str,
    provider: str,
    model: str = "",
    status: str = "ok",
    seconds: float = 0.0,
) -> None:
    cap = str(capability or "normal")
    prov = str(provider or "unknown")
    st = str(status or "ok")
    with _LOCK:
        _inc("llm_requests_total", (("capability", cap), ("provider", prov), ("status", st)))
        if st == "ok":
            _inc(
                "router_selection_total",
                (("provider", prov), ("model", str(model or "unknown"))),
            )
        if seconds > 0:
            buckets = _HIST.setdefault(cap, [0] * len(_BUCKETS))
            for i, bound in enumerate(_BUCKETS):
                if seconds <= bound:
                    buckets[i] += 1
                    break
            _HIST_SUM[cap] = _HIST_SUM.get(cap, 0.0) + seconds
            _HIST_COUNT[cap] = _HIST_COUNT.get(cap, 0) + 1


def fallback(*, from_provider: str, to_provider: str) -> None:
    with _LOCK:
        _inc(
            "provider_fallback_total",
            (("from_provider", str(from_provider or "unknown")), ("to_provider", str(to_provider or "unknown"))),
        )


def _labels(pairs: tuple[tuple[str, str], ...]) -> str:
    if not pairs:
        return ""
    inner = ",".join(f'{k}="{str(v).replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"' for k, v in pairs)
    return "{" + inner + "}"


def render() -> str:
    with _LOCK:
        counters = dict(_COUNTERS)
        hist = {k: list(v) for k, v in _HIST.items()}
        hist_sum = dict(_HIST_SUM)
        hist_count = dict(_HIST_COUNT)

    lines: list[str] = [
        "# HELP router_worker_llm_requests_total LLM routing attempts by capability/provider/status",
        "# TYPE router_worker_llm_requests_total counter",
        "# HELP router_worker_llm_latency_seconds LLM routing attempt latency",
        "# TYPE router_worker_llm_latency_seconds histogram",
        "# HELP router_worker_router_selection_total Successful provider/model selections",
        "# TYPE router_worker_router_selection_total counter",
        "# HELP router_worker_provider_fallback_total Fallback selections after the primary provider",
        "# TYPE router_worker_provider_fallback_total counter",
    ]
    for (metric, labels), value in sorted(counters.items(), key=lambda kv: kv[0][0]):
        lines.append(f"router_worker_{metric}{_labels(labels)} {value}")

    for cap in sorted(hist):
        cumulative = 0
        for bound, hits in zip(_BUCKETS, hist[cap]):
            cumulative += hits
            lines.append(
                f'router_worker_llm_latency_seconds_bucket{{capability="{cap}",le="{bound}"}} {cumulative}'
            )
        total = hist_count.get(cap, 0)
        lines.append(
            f'router_worker_llm_latency_seconds_bucket{{capability="{cap}",le="+Inf"}} {total}'
        )
        lines.append(
            f'router_worker_llm_latency_seconds_sum{{capability="{cap}"}} {hist_sum.get(cap, 0.0)}'
        )
        lines.append(
            f'router_worker_llm_latency_seconds_count{{capability="{cap}"}} {total}'
        )
    lines.append("")
    return "\n".join(lines)
