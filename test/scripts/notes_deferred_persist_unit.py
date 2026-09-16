# -*- coding: utf-8 -*-
"""Unit: deferred search-then-note persist via classify plan flag."""
from __future__ import annotations

import sys
import ast
import asyncio
from contextvars import ContextVar
import logging
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

from notes_persist import (  # noqa: E402
    notes_from_assistant_body,
    plan_is_empty_note_create,
    should_defer_note_persist,
    simplify_note_query,
)
import notes_client  # noqa: E402


def deferred_source_contract() -> None:
    path = ROOT / "hermes/main/plugins/zalo/adapter.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ZaloAdapter")
    names = {"_as_mark_pending_note_persist", "_as_clear_pending_note_persist", "_as_persist_deferred_notes"}
    methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    ns = {"__name__": "deferred_source_contract", "logger": logging.getLogger(__name__)}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), ns)
    host = SimpleNamespace(_as_source_message_id=ContextVar("owned-note-source", default=""))
    mark = ns["_as_mark_pending_note_persist"]
    for source in ("schedule:owned:run", "foreground-owned"):
        host._as_source_message_id.set(source)
        mark(host, thread_id="dm", thread_type="user", sender_id="admin", user_text="research", silent=True,
             note_selector={"scope": "group", "thread_id": "target-group"}, admin_ids=["admin"])
    assert len(host._as_pending_note_persist) == 2, "same-chat requests overwrote one another"
    captured = []
    async def execute(plan, **kw):
        captured.append((plan, kw)); return {"success": True, "count": 1}
    body = "1. A concrete researched item with useful original evidence and a source https://example.com/owned-item"
    with patch.object(notes_client, "execute_note_plan_async", execute):
        untouched = asyncio.run(ns["_as_persist_deferred_notes"](host, "dm", body, {"source_message_id": "unrelated-source"}))
        assert untouched == body and not captured and len(host._as_pending_note_persist) == 2
        asyncio.run(ns["_as_persist_deferred_notes"](host, "dm", body, {"source_message_id": "schedule:owned:run"}))
        assert captured[0][0]["notes"][0]["metadata"].get("source_message_id") == "schedule:owned:run", "host source provenance lost"
        assert captured[0][0]["note_selector"] == {"scope": "group", "thread_id": "target-group"}
        assert captured[0][1]["admin_ids"] == ["admin"], "host-authenticated admin context lost"
        asyncio.run(ns["_as_persist_deferred_notes"](host, "dm", body, {"source_message_id": "foreground-owned"}))
        assert len(captured) == 2, "concurrent deferred note was overwritten"
        assert captured[1][0]["notes"][0]["metadata"]["source_message_id"] == "foreground-owned"
    for source in ("schedule:owned:later", "foreground-later"):
        host._as_source_message_id.set(source)
        mark(host, thread_id="dm", thread_type="user", sender_id="admin", user_text="research")
    ns["_as_clear_pending_note_persist"](host, "dm")
    assert len(host._as_pending_note_persist) == 1 and ("dm", "schedule:owned:later") in host._as_pending_note_persist


def main() -> int:
    print("running test case 1/8")
    assert plan_is_empty_note_create(
        {
            "task_hint": "note",
            "skill": "notes",
            "skill_action": "create",
            "notes": [],
        }
    )
    assert not plan_is_empty_note_create(
        {
            "task_hint": "note",
            "skill": "notes",
            "skill_action": "create",
            "notes": [{"content": "hello", "note_date": None, "tags": []}],
        }
    )

    print("running test case 2/8")
    assert should_defer_note_persist(
        {"task_hint": "search", "skill": "web_search", "persist_gathered_notes": True},
        "any user language",
    )
    assert not should_defer_note_persist(
        {"task_hint": "search", "skill": "web_search"},
        "tim them cac tin tuyen dung Java roi note lai",
    )
    assert should_defer_note_persist(
        {"task_hint": "note", "skill": "notes", "skill_action": "create", "notes": []},
        "x",
    )

    print("running test case 3/8")
    body = (
        "Day la cac tin:\n"
        "1. Vinsmart Future — TechLead Backend (Golang/Java) tai HCM\n"
        "2. Du an Java + ReactJS Ha Noi luong 45 trieu\n"
        "3. ITviec fullstack React .NET HCM\n\n"
        "https://example.com/a\n"
    )
    notes = notes_from_assistant_body(body, timezone="Asia/Ho_Chi_Minh")
    assert len(notes) == 3, notes
    assert "Vinsmart" in notes[0]["content"]
    assert notes[0]["note_date"]
    assert "http" in notes[0]["content"].lower() or notes[0].get("metadata", {}).get("citations")

    print("running test case 4/8")
    # Classifier owns selector wording; host does not strip fillers.
    assert "java" in simplify_note_query("java fullstack").lower()

    print("running test case 5/8")
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method: str, path: str, payload=None):
        calls.append((method, path, payload))
        if path == "/v1/notes/query":
            q = str((payload or {}).get("query") or "")
            if "java" in q.lower():
                return {
                    "success": True,
                    "items": [
                        {
                            "id": "note_j",
                            "content": "Vinsmart Future TechLead Backend Java",
                            "note_date": "2026-09-11",
                        }
                    ],
                }
            return {"success": True, "items": []}
        return {"success": True, "note": {"id": "note_x"}}

    with patch.object(notes_client, "_request", side_effect=fake_request):
        lookup = {
            "skill_action": "lookup",
            "notes": [],
            "note_selector": {"query": "java"},
        }
        result = notes_client.execute_note_plan(
            lookup, thread_id="dm", thread_type="user", sender_id="u1"
        )
        assert result["success"] and result["count"] == 1, result
        assert "Vinsmart" in result["text"]

    print("running test case 6/8")
    with patch.object(notes_client, "_request", side_effect=fake_request):
        create_plan = {
            "skill_action": "create",
            "notes": notes,
        }
        created = notes_client.execute_note_plan(
            create_plan, thread_id="dm", thread_type="user", sender_id="u1"
        )
        assert created["success"] and created["count"] == 3
        assert any(c[0] == "POST" and c[1] == "/v1/notes" for c in calls)

    print("running test case 7/8")
    adapter = (ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py").read_text(
        encoding="utf-8"
    )
    assert "_as_persist_deferred_notes" in adapter
    assert "deferred note persist" in adapter
    assert "real_thread_id" in adapter
    assert "load_search_then_note_contract" in adapter
    from turn_wait import real_thread_id  # noqa: E402

    bare = "233767886566872937"
    iso = f"{bare}::job::job_abc"
    assert real_thread_id(iso) == bare

    print("running test case 8/8: actual deferred source isolation/provenance")
    deferred_source_contract()
    print("notes_deferred_persist_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
