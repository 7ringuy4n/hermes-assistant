# -*- coding: utf-8 -*-
"""Unit: quote-reply context survives the search-contract rebuild.

Regression for the case where a short resend request ("gửi lại") quoting a prior
message was classified as a new web search and the rebuiled prompt dropped the
[Quoted message] block, so the model claimed it saw no earlier content.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py"
CORE = ROOT / "hermes" / "main" / "skills" / "classify" / "parts" / "core.txt"
BAKED = ROOT / "architect" / "models" / "router-worker" / "config" / "classify.json"


def main() -> int:
    checks: list[tuple[str, bool]] = []

    adapter = ADAPTER.read_text(encoding="utf-8")
    checks.append(("quote_block builder present", 'quote_block = f"\\n\\n[Quoted message]\\n{quote_text}"' in adapter))
    # Both search-contract rebuilds must keep the quoted block.
    checks.append(("search contract keeps quote block", adapter.count('f"{bare_q}{quote_block}') >= 2))
    checks.append(("no bare_q-only search contract", 'f"{bare_q}\\n\\n[Current lookup execution contract]' not in adapter))

    core = CORE.read_text(encoding="utf-8")
    checks.append(("core prompt has resend rule", "resend, repeat, re-send" in core))
    checks.append(("core prompt forbids quoted-topic routing", "never by the topic of the quoted text" in core))

    baked = json.loads(BAKED.read_text(encoding="utf-8"))
    system = str(baked.get("system") or "")
    checks.append(("classify bake includes resend rule", "resend, repeat, re-send" in system))
    checks.append(("classify bake forbids quoted-topic routing", "never by the topic of the quoted text" in system))

    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
