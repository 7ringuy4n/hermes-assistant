# -*- coding: utf-8 -*-
"""Unit: environment switch semantics are consistent (active/inactive).

The stack standard is ``active|1|true|yes|on`` = on, everything else (including
``inactive``/``0``/``false``/``no``/``off``) = off. A falsey-set parser that
omits ``inactive`` silently turns an ``inactive`` value ON.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

import queue_history  # noqa: E402
import session_memory  # noqa: E402
import workflow_client  # noqa: E402


def _on(value: str, env: str, fn) -> bool:
    with patch.dict(os.environ, {env: value}):
        return bool(fn())


def main() -> int:
    checks: list[tuple[str, bool]] = []

    # Direct behavior checks on importable switches.
    checks.append(("ZALO_HISTORY_POSTGRES active -> on", _on("active", "ZALO_HISTORY_POSTGRES", queue_history.enabled)))
    checks.append(("ZALO_HISTORY_POSTGRES inactive -> off", not _on("inactive", "ZALO_HISTORY_POSTGRES", queue_history.enabled)))
    checks.append(("ZALO_HISTORY_POSTGRES 0 -> off", not _on("0", "ZALO_HISTORY_POSTGRES", queue_history.enabled)))

    checks.append(("ZALO_SESSION_VALKEY active -> on", _on("active", "ZALO_SESSION_VALKEY", session_memory.enabled)))
    checks.append(("ZALO_SESSION_VALKEY inactive -> off", not _on("inactive", "ZALO_SESSION_VALKEY", session_memory.enabled)))

    with patch.dict(os.environ, {"HERMES_WORKFLOW": "active", "WORKFLOW_URL": "http://workflow:8108"}):
        checks.append(("HERMES_WORKFLOW active -> on", workflow_client.workflow_enabled()))
    with patch.dict(os.environ, {"HERMES_WORKFLOW": "inactive", "WORKFLOW_URL": "http://workflow:8108"}):
        checks.append(("HERMES_WORKFLOW inactive -> off", not workflow_client.workflow_enabled()))

    # Source checks for the heavier service parsers: no bare falsey set without
    # inactive, and an explicit on-value parse is used.
    dispatcher = (ROOT / "architect" / "models" / "dispatcher" / "app.py").read_text(encoding="utf-8")
    checks.append((
        "dispatcher _timing_enabled uses on-value parse",
        'v not in {"0", "false", "no", "off"}' not in dispatcher
        and 'return v in {"1", "true", "yes", "on", "active"}' in dispatcher,
    ))
    memory = (ROOT / "architect" / "memory" / "memory-worker" / "app.py").read_text(encoding="utf-8")
    checks.append((
        "memory _timing_add uses on-value parse",
        'if v in {"0", "false", "no", "off"} or seconds' not in memory
        and 'if v not in {"1", "true", "yes", "on", "active"} or seconds' in memory,
    ))
    adapter = (ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py").read_text(encoding="utf-8")
    checks.append((
        "adapter switches accept inactive",
        adapter.count('{"0", "off", "false", "no", "inactive"}') >= 2,
    ))

    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
