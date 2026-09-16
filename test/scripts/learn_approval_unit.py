# -*- coding: utf-8 -*-
"""Unit: knowledge-learn approval wiring.

A channel (Zalo/Message worker) user's learn ask must wait for admin approval,
while with no messaging channel active the default Hermes operator learns
without an approval step.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INGEST = ROOT / "architect" / "tools" / "ingest" / "app.py"
INSTALL = ROOT / "scripts" / "main" / "install-component.sh"
ENV_EXAMPLE = ROOT / ".env.example"
ADAPTER = ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py"
COMPOSE = ROOT / "docker" / "docker-compose.yml"


def main() -> int:
    checks: list[tuple[str, bool]] = []

    ingest = INGEST.read_text(encoding="utf-8")
    checks.append((
        "ingest parses require-approve flag",
        'os.environ.get("LEARN_REQUIRE_APPROVE") or "0"' in ingest,
    ))
    checks.append((
        "inactive is off (on-value parse, not falsey-set)",
        '"active",' in ingest and 'not in {' not in ingest.split("LEARN_REQUIRE_APPROVE = ")[1][:160],
    ))
    checks.append((
        "zalo learn submit always stages pending",
        "def learn_submit" in ingest
        and "_pending_put(item)" in ingest
        and '_learn_notify(\n        "pending"' in ingest.replace("\r\n", "\n"),
    ))
    checks.append((
        "scan auto-ingests only when approval is off",
        "if not LEARN_REQUIRE_APPROVE:" in ingest and "_ingest_pending_item(item)" in ingest,
    ))
    checks.append((
        "scan notifies admin only when approval is on",
        "if n and LEARN_REQUIRE_APPROVE:" in ingest and '_learn_notify("scan"' in ingest,
    ))

    install = INSTALL.read_text(encoding="utf-8")
    checks.append((
        "installing message/zalo enables learn approval",
        "message|zalo)" in install and "LEARN_REQUIRE_APPROVE=active" in install,
    ))
    checks.append((
        "removing message/zalo disables learn approval",
        "LEARN_REQUIRE_APPROVE=inactive" in install,
    ))

    env = ENV_EXAMPLE.read_text(encoding="utf-8")
    checks.append(("env template documents learn approval", "LEARN_REQUIRE_APPROVE=" in env))

    compose = COMPOSE.read_text(encoding="utf-8")
    checks.append((
        "compose derives approval from the channel state",
        "LEARN_REQUIRE_APPROVE=${LEARN_REQUIRE_APPROVE:-${ENABLE_ZALO:-inactive}}" in compose,
    ))

    adapter = ADAPTER.read_text(encoding="utf-8")
    checks.append((
        "zalo learn ask routes to submit (approval), not scan",
        "/v1/learn/submit" in adapter and "/v1/learn/scan" not in adapter,
    ))

    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
