#!/usr/bin/env python3
"""Unit: the invariant registry is complete and points at real tests.

Implements the TEST_STRATEGY invariant-first coverage index: every listed
invariant must map to existing evidence and the runner must report progress.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "test" / "README.md"
RUNNER = ROOT / "test" / "scripts" / "run_case_index_lab.py"

REQUIRED = {
    "INV-CONV-001", "INV-CONV-002", "INV-CONV-003",
    "INV-QUEUE-001", "INV-QUEUE-002",
    "INV-SEC-001", "INV-SEC-002", "INV-SEC-003", "INV-SEC-004",
    "INV-SEC-005", "INV-SEC-006", "INV-SEC-007",
    "INV-MEM-001", "INV-ROUTER-001", "INV-FAIL-001",
}


def main() -> int:
    assert REGISTRY.is_file(), "test/README.md missing"
    text = REGISTRY.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.strip().startswith("| INV-")]
    assert rows, "no invariant rows found"

    seen: set[str] = set()
    missing: list[str] = []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        inv = cells[0]
        seen.add(inv)
        evidence = "|".join(cells[4:])
        for path in re.findall(r"`([^`]+)`", evidence):
            if path.startswith("test/") and not (ROOT / path).exists():
                missing.append(f"{inv} -> {path}")
    assert not missing, f"registry points at missing tests: {missing}"

    missing_ids = REQUIRED - seen
    assert not missing_ids, f"invariants not registered: {sorted(missing_ids)}"

    runner = RUNNER.read_text(encoding="utf-8")
    assert "running test case" in runner, "runner must report N/TOTAL progress"

    print(f"invariant_registry_unit: PASS ({len(seen)} invariants, {len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
