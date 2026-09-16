#!/usr/bin/env python3
"""Unit: idle rollover starts a new session and archives the old one.

The session service needs fastapi/pydantic/redis/httpx, which are absent in the
offline unit environment, so those modules are stubbed before loading the app.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION_APP = ROOT / "architect" / "memory" / "session" / "app.py"


class _HTTPException(Exception):
    def __init__(self, status_code: int = 0, detail=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _FastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def _route(self, *args, **kwargs):
        def deco(fn):
            return fn
        return deco

    get = post = put = delete = patch = _route


class _Field:
    def __init__(self, *args, **kwargs):
        self.default = args[0] if args else kwargs.get("default")


class _Redis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.setex_calls: list[tuple[str, int, str]] = []

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.setex_calls.append((key, ttl, value))

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                removed += 1
        return removed

    @classmethod
    def from_url(cls, *args, **kwargs):
        return cls()


class _Resp:
    status_code = 200


class _Client:
    def __init__(self, *args, **kwargs):
        self.posts: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json=None):
        self.posts.append((url, json or {}))
        return _Resp()


def _install_stubs() -> None:
    fastapi = types.ModuleType("fastapi")
    fastapi.FastAPI = _FastAPI
    fastapi.HTTPException = _HTTPException
    pydantic = types.ModuleType("pydantic")
    pydantic.BaseModel = type("BaseModel", (), {})
    pydantic.Field = _Field
    redis = types.ModuleType("redis")
    redis.Redis = _Redis
    httpx = types.ModuleType("httpx")
    httpx.Client = _Client
    sys.modules["fastapi"] = fastapi
    sys.modules["pydantic"] = pydantic
    sys.modules["redis"] = redis
    sys.modules["httpx"] = httpx


def _load_session_app():
    _install_stubs()
    spec = importlib.util.spec_from_file_location("session_app_unit", SESSION_APP)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _body(**overrides):
    base = {
        "session_id": "zalo:user:1",
        "thread_id": "1",
        "user_id": "1",
        "messages": [
            {"role": "user", "content": "new question"},
            {"role": "assistant", "content": "new answer"},
        ],
        "metadata": {"platform": "zalo"},
        "append": True,
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


def main() -> int:
    mod = _load_session_app()

    # --- pure predicate boundaries ---
    now = time.time()
    assert mod._should_rollover(now - 3600, now, 3600) is True
    assert mod._should_rollover(now - 7200, now, 3600) is True
    assert mod._should_rollover(now - 3599, now, 3600) is False
    assert mod._should_rollover(now - 10, now, 3600) is False
    assert mod._should_rollover(now - 7200, now, 0) is False
    assert mod._should_rollover(None, now, 3600) is False
    assert mod._should_rollover("bogus", now, 3600) is False
    assert mod._should_rollover(0, now, 3600) is False

    # --- env parsing is per call and bounded ---
    saved = os.environ.pop("SESSION_IDLE_ROLLOVER_SECONDS", None)
    try:
        assert mod._idle_rollover_seconds() == 3600
        os.environ["SESSION_IDLE_ROLLOVER_SECONDS"] = "0"
        assert mod._idle_rollover_seconds() == 0
        os.environ["SESSION_IDLE_ROLLOVER_SECONDS"] = "abc"
        assert mod._idle_rollover_seconds() == 3600
        os.environ["SESSION_IDLE_ROLLOVER_SECONDS"] = "999999999"
        assert mod._idle_rollover_seconds() == mod.IDLE_ROLLOVER_MAX_S
    finally:
        os.environ.pop("SESSION_IDLE_ROLLOVER_SECONDS", None)
        if saved is not None:
            os.environ["SESSION_IDLE_ROLLOVER_SECONDS"] = saved

    # --- idle session rolls over: old context archived, new session starts ---
    key = "conversation_active:zalo:user:1"
    old = {
        "session_id": "zalo:user:1",
        "thread_id": "1",
        "user_id": "1",
        "messages": [
            {"role": "user", "content": "old question " + "x" * 40},
            {"role": "assistant", "content": "old answer " + "y" * 40},
        ],
        "metadata": {},
        "created_at": now - 7200,
        "updated_at": now - 7200,
    }
    mod.r.store[key] = json.dumps(old)
    res = mod.put_session("zalo:user:1", _body())
    assert res["rolled_over"] is True, res
    assert res["archived"] is True, res
    stored = json.loads(mod.r.store[key])
    assert [m["content"] for m in stored["messages"]] == ["new question", "new answer"]
    assert stored["created_at"] > now - 60

    # --- recent session keeps context ---
    recent = dict(old, updated_at=now - 5, created_at=now - 60)
    mod.r.store[key] = json.dumps(recent)
    res = mod.put_session("zalo:user:1", _body())
    assert res["rolled_over"] is False, res
    stored = json.loads(mod.r.store[key])
    assert len(stored["messages"]) == 4
    assert stored["messages"][-1]["content"] == "new answer"

    # --- rollover disabled keeps context even when idle ---
    os.environ["SESSION_IDLE_ROLLOVER_SECONDS"] = "0"
    try:
        mod.r.store[key] = json.dumps(old)
        res = mod.put_session("zalo:user:1", _body())
        assert res["rolled_over"] is False, res
        assert len(json.loads(mod.r.store[key])["messages"]) == 4
    finally:
        os.environ.pop("SESSION_IDLE_ROLLOVER_SECONDS", None)

    # --- a read after the idle window reports the session absent (empty hydrate)
    mod.r.store[key] = json.dumps(old)
    try:
        mod.get_session("zalo:user:1")
        raise AssertionError("idle GET should report not found")
    except mod.HTTPException as exc:
        assert int(getattr(exc, "status_code", 0)) == 404, exc
    assert key not in mod.r.store

    # --- a read inside the window still returns context ---
    mod.r.store[key] = json.dumps(recent)
    got = mod.get_session("zalo:user:1")
    assert got["ok"] is True and len(got["session"]["messages"]) == 2

    # --- archive path is shared with reset-all ---
    source = SESSION_APP.read_text(encoding="utf-8")
    assert "def _archive_session_data(" in source
    assert 'source="clearsession"' in source
    assert 'source: str = "session-rollover"' in source
    assert "SESSION_IDLE_ROLLOVER_SECONDS" in source
    assert "_should_rollover(" in source
    assert "rolled_over" in source

    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    defaults_md = (ROOT / "docs" / "config" / "DEFAULTS.md").read_text(encoding="utf-8")
    assert "SESSION_IDLE_ROLLOVER_SECONDS=3600" in env_example
    assert "SESSION_IDLE_ROLLOVER_SECONDS=3600" in defaults_md

    print("session_idle_rollover_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
