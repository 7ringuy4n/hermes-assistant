"""Regression: semantic exclusions, scope permissions, and schedule audit IDs."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes/main/plugins/zalo"))
import notes_client
import schedule_client
import record_scope
import classify_client
import media_shortcuts


def main() -> int:
    fixtures = [
        {"id": "java", "title": "Backend Java — Sample Company", "content": "Recruitment opening", "scope_id": "zalo:user:u"},
        {"id": "idea", "title": "Java concurrency idea", "content": "Personal implementation notes", "scope_id": "zalo:user:u"},
        {"id": "handover", "title": "Work handover", "content": "Send project documents", "scope_id": "zalo:user:u"},
    ]
    def select(_system, payload, **_kwargs):
        import json
        data = json.loads(payload)
        assert data["predicate"] == "notes that are not recruitment"
        assert {item["id"] for item in data["candidates"]} == {"java", "idea", "handover"}
        return {"matches": ["idea", "handover"], "uncertain": False}
    print("running test case 1/8 semantic exclusion retains non-recruitment Java note")
    with patch.object(notes_client, "_find_candidates", return_value=fixtures), patch.object(media_shortcuts, "_omni_json_plan", side_effect=select):
        result = notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"semantic_query": "notes that are not recruitment"}}, thread_id="u", thread_type="user", sender_id="u")
        assert result["success"] and [row["id"] for row in result["items"]] == ["idea", "handover"]
    print("running test case 2/8 planner cannot invent IDs or authorize uncertain mutation")
    for output in ({"matches": ["unknown"], "uncertain": False}, {"matches": ["java"], "uncertain": True}):
        with patch.object(media_shortcuts, "_omni_json_plan", return_value=output):
            try:
                notes_client._semantic_candidates(fixtures, "exclude recruitment")
                raise AssertionError("unverified selection accepted")
            except ValueError:
                pass
    print("running test case 3/8 failed lookup never retries individual positive words")
    with patch.object(notes_client, "_find_candidates", return_value=[]) as fetch:
        notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"query": "not recruitment Java"}}, thread_id="u", thread_type="user", sender_id="u")
        assert fetch.call_count == 1
    print("running test case 4/8 non-admin cannot request other group/DM/all")
    for kind in ("group", "dm", "all"):
        with patch.object(notes_client, "_request") as transport:
            result = notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"scope": kind, "scope_ref": "Sample Group" if kind != "all" else ""}}, thread_id="u", thread_type="user", sender_id="u", admin_ids={"admin"})
            assert not result["success"] and result["error"] == "record_scope_forbidden"
            transport.assert_not_called()
    print("running test case 5/8 requester ID cannot leak group schedule into DM")
    rows = [{"id": "group", "origin": {"thread_id": "g", "user_id": "u"}, "context": {"thread_id": "g", "thread_type": "group", "sender_id": "u"}}, {"id": "dm", "origin": {"thread_id": "u"}, "context": {"thread_id": "u", "thread_type": "user"}}]
    with patch.object(schedule_client, "list_schedules", return_value=rows):
        assert [row["id"] for row in schedule_client.schedules_for_thread("u", "user")] == ["dm"]
        assert [row["id"] for row in schedule_client.schedules_for_thread("g", "group")] == ["group"]
        assert len(schedule_client.schedules_for_record_scope({"scope": "all"}, thread_id="admin", thread_type="user", is_admin=True)) == 2
    print("running test case 6/8 typed classifier preserves predicates and scope")
    raw = {"semantic_query": "not recruitment", "scope": "dm", "scope_ref": "Sample User", "view": "detail"}
    normalized = classify_client._coerce_note_selector(raw)
    assert normalized["semantic_query"] == raw["semantic_query"] and normalized["scope"] == "dm"
    assert classify_client._coerce_schedule_selector({"scope": "all"})["scope"] == "all"
    print("running test case 7/8 admin group/DM creation uses the selected scope and trusted owner")
    import channels_client
    for kind, protocol_kind in (("group", "group"), ("dm", "user"), ("dm", "dm")):
        calls = []
        def create(method, path, payload):
            calls.append(payload)
            return {"success": True, "note": {"id": "created"}}
        with patch.object(channels_client, "resolve_channel", return_value={"kind": protocol_kind, "external_id": "selected"}), patch.object(notes_client, "_request", side_effect=create):
            result = notes_client.execute_note_plan({"skill_action": "create", "note_selector": {"scope": kind, "scope_ref": "Sample"}, "notes": [{"title": "Title", "content": "Content"}]}, thread_id="admin", thread_type="user", sender_id="admin", admin_ids={"admin"})
            assert result["success"] and calls[0]["scope_id"] == f"zalo:{'group' if protocol_kind == 'group' else 'user'}:selected"
            assert calls[0]["owner_id"] == "admin" and calls[0]["thread_id"] == "selected"
    print("running test case 8/8 all-scope admin query is batched and all-scope writes are denied")
    with patch.object(record_scope, "registered_note_scopes", return_value=["zalo:group:g", "zalo:user:u"]), patch.object(notes_client, "_request", return_value={"success": True, "items": []}) as transport:
        result = notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"scope": "all", "view": "count"}}, thread_id="admin", thread_type="user", sender_id="admin", admin_ids={"admin"})
        assert result["success"] and transport.call_count == 1
        assert set(transport.call_args.args[2]["scope_ids"]) == {"zalo:user:admin", "zalo:group:g", "zalo:user:u"}
        result = notes_client.execute_note_plan({"skill_action": "delete", "note_selector": {"scope": "all", "match_all": True}}, thread_id="admin", thread_type="user", sender_id="admin", admin_ids={"admin"})
        assert result["error"] == "all_scope_read_only" and transport.call_count == 1
    print("PASS scoped records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
