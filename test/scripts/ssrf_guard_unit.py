#!/usr/bin/env python3
"""Unit: websearch direct-extract SSRF guard (INV-SEC-002).

Exercises the real ``_validate_public_url`` guard: scheme, credentials, port,
and non-global resolved addresses are rejected; redirect targets are
re-validated.
"""
from __future__ import annotations

import asyncio
import importlib.util
import socket
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
WEBSEARCH = ROOT / "architect" / "models" / "router-worker" / "websearch.py"


def _install_stubs() -> None:
    class _Router:
        def get(self, *a, **k):
            return lambda fn: fn

        def post(self, *a, **k):
            return lambda fn: fn

    class _HTTPException(Exception):
        pass

    fastapi = types.ModuleType("fastapi")
    fastapi.APIRouter = _Router
    fastapi.HTTPException = _HTTPException
    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = type("BaseModel", (), {})
    pydantic.Field = lambda *a, **k: (a[0] if a else None)
    httpx = types.ModuleType("httpx")
    httpx.AsyncClient = object
    sys.modules["fastapi"] = fastapi
    sys.modules["pydantic"] = pydantic
    sys.modules["httpx"] = httpx


def _load():
    _install_stubs()
    spec = importlib.util.spec_from_file_location("websearch_ssrf_unit", WEBSEARCH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ADDR = {
    "public.example": "93.184.216.34",
    "localhost": "127.0.0.1",
    "metadata": "169.254.169.254",
    "lan": "10.0.0.5",
    "v6loop": "::1",
}


def _fake_getaddrinfo(host, port, *args, **kwargs):
    ip = ADDR.get(host, "93.184.216.34")
    if ":" in ip:
        return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (ip, port, 0, 0))]
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


def _rejected(mod, url: str) -> bool:
    try:
        asyncio.run(mod._validate_public_url(url))
    except ValueError:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def main() -> int:
    mod = _load()
    with patch("socket.getaddrinfo", side_effect=_fake_getaddrinfo):
        # Scheme / credential / port boundaries
        assert _rejected(mod, "ftp://public.example/x"), "non-HTTP(S) must be rejected"
        assert _rejected(mod, "file://public.example/x"), "file scheme must be rejected"
        assert _rejected(mod, "http://user:pass@public.example/x"), "URL credentials must be rejected"
        assert _rejected(mod, "http://public.example:8080/x"), "non-standard port must be rejected"
        assert _rejected(mod, ""), "empty URL must be rejected"

        # Non-global resolved addresses (SSRF)
        for host in ("localhost", "metadata", "lan", "v6loop"):
            assert _rejected(mod, f"http://{host}/x"), f"{host} must be rejected (non-global)"

        # Public host is allowed
        ok = asyncio.run(mod._validate_public_url("https://public.example/page"))
        assert ok.startswith("https://public.example/page"), ok

    # Redirect targets are re-validated before following (source contract).
    src = WEBSEARCH.read_text(encoding="utf-8")
    assert "_validate_public_url(urljoin(current, location))" in src
    assert "follow_redirects=False" in src

    print("ssrf_guard_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
