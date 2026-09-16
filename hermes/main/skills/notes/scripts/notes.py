"""Execute a structured note plan for the trusted local Hermes operator.

No Zalo adapter, bridge, message queue, or chat identity is required. The scope
comes from deployment configuration, not the model-authored stdin plan.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    plugins = Path(__file__).resolve().parents[3] / "plugins/zalo"
    sys.path.insert(0, str(plugins))
    from notes_client import execute_note_plan

    scope = os.environ.get("HERMES_RECORD_SCOPE", "hermes:local").strip()
    plan = json.load(sys.stdin)
    if not isinstance(plan, dict):
        raise ValueError("note_plan_must_be_object")
    result = execute_note_plan(plan, thread_id="", thread_type="local",
                               sender_id=scope, current_scope_id=scope)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
