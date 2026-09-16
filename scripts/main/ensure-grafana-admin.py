#!/usr/bin/env python3
"""Ensure a real Grafana admin password when Grafana is enabled.

Grafana's Compose fallback (``changeme-set-in-env``) is insecure, so an enabled
monitor must never run on it. This is the durable first-setup/install hook:

- If ``GRAFANA_ADMIN_PASSWORD`` is already a real value (OpenBao-injected
  environment or host ``.env``), it is printed unchanged (idempotent).
- Otherwise a strong random password is written to ``.env`` so
  ``first-setup-openbao`` seeds it into OpenBao, then the value is printed.

The caller (``run.sh``) exports the printed value for the current Compose
invocation. Nothing is written for a placeholder-free host, and no secret is
ever logged in full by the caller.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

KEY = "GRAFANA_ADMIN_PASSWORD"
ON_VALUES = {"1", "true", "yes", "on", "active"}
PLACEHOLDERS = {"changeme-set-in-env"}


def active(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ON_VALUES


def is_placeholder(value: str) -> bool:
    text = (value or "").strip()
    if not text:
        return True
    low = text.lower()
    if low in PLACEHOLDERS:
        return True
    return low.startswith("change_me")


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip().strip("'").strip('"')
    return out


def upsert(path: Path, key: str, value: str) -> None:
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> int:
    if not active("ENABLE_GRAFANA"):
        return 0
    root = Path(os.environ.get("STACK_ROOT") or Path(__file__).resolve().parents[2])
    env_path = root / ".env"
    current = (os.environ.get(KEY) or "").strip()
    if is_placeholder(current):
        current = read_env(env_path).get(KEY, "")
    if is_placeholder(current):
        current = secrets.token_urlsafe(18)
        try:
            upsert(env_path, KEY, current)
        except OSError as exc:
            print(f"ERROR: cannot write {env_path}: {exc}", file=sys.stderr)
            return 1
    print(current)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
