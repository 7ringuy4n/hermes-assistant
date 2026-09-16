#!/usr/bin/env python3
"""Unit: daily memory compact is core (not media-gated) and env-driven config."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")

    # Memory housekeeping must run without the optional media worker.
    assert "need_media compact" not in run_sh
    assert "need_media optimize-memory" not in run_sh
    assert 'curl -fsS -m 30 -X POST "${mem}/v1/compact"' in run_sh

    # The compact timer is always installed (never disabled by a media gate).
    assert "systemctl enable --now assistant-compact.timer" in run_sh
    assert "disable --now assistant-compact.timer" not in run_sh
    assert "Description=Assistant daily memory compact" in run_sh

    # Retention is host configuration with a default of 7.
    backup_sh = (ROOT / "architect" / "backup-restore" / "lib" / "backup.sh").read_text(
        encoding="utf-8"
    )
    assert ": \"${BACKUP_RETENTION_DAYS:=7}\"" in backup_sh

    # Scheduled units load .env so operators can change the windows there.
    def _unit_block(name: str) -> str:
        marker = f'{name}" >/dev/null <<EOF'
        assert marker in run_sh, name
        return run_sh.split(marker, 1)[1].split("\nEOF", 1)[0]

    assert "EnvironmentFile=-${STACK_ROOT}/.env" in _unit_block("assistant-backup.service")
    assert "EnvironmentFile=-${STACK_ROOT}/.env" in _unit_block("assistant-compact.service")

    compose = (ROOT / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "MEMORY_STAGED_RETENTION_DAYS=${MEMORY_STAGED_RETENTION_DAYS:-7}" in compose

    print("compact_daily_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
