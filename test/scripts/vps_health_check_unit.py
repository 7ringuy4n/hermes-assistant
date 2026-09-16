#!/usr/bin/env python3
"""Static regression checks for the post-deploy health gate."""

from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "test" / "scripts" / "vps_health_check.py").read_text(
    encoding="utf-8"
)


def main() -> int:
    assert '${OMNIROUTER_HOST_PORT:-20129}' in SOURCE
    assert "127.0.0.1:20128" not in SOURCE
    assert 'docker exec -e "OMNIROUTER_API_KEY=' not in SOURCE
    assert 'docker exec "${cid}" python3' in SOURCE
    assert "2>/dev/null || echo fail" not in SOURCE
    monitor = (ROOT / "test/scripts/grafana_integration_lab.py").read_text(encoding="utf-8")
    helper = next(node for node in ast.parse(monitor).body if isinstance(node, ast.FunctionDef) and node.name == "metric_not_up")
    namespace = {}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), "actual-monitoring-gate", "exec"), namespace)
    failed = namespace["metric_not_up"]
    assert all(failed(value) for value in ("gauge 0", "gauge 0.0", "gauge NaN", "gauge invalid", ""))
    assert not failed("gauge 1.0") and not failed("gauge 1")
    assert "label=com.docker.compose.service=stack-exporter" in monitor
    assert 'active.get("AV")' in monitor and 'active.get("OMNI")' in monitor
    print("PASS vps_health_check_unit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
