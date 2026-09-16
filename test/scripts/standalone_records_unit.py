"""Host scope remains independent of Zalo identity and model role fields."""
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes/main/plugins/zalo"))
import notes_client


def main():
    print("running test case 1/2 standalone note creation uses host-owned namespace")
    with patch.object(notes_client, "_request", return_value={"success": True, "note": {"id": "sample"}}) as request:
        result = notes_client.execute_note_plan({"skill_action": "create", "notes": [{"title": "Sample idea", "content": "Sample content"}]}, thread_id="", thread_type="local", sender_id="hermes:sample", current_scope_id="hermes:sample")
        assert result["success"]
        assert request.call_args.args[2]["scope_id"] == "hermes:sample"
    print("running test case 2/2 model cannot broaden standalone or conversation scope")
    with patch.object(notes_client, "_request") as request:
        result = notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"scope": "all"}}, thread_id="", thread_type="local", sender_id="hermes:sample", current_scope_id="hermes:sample")
        assert not result["success"]
        request.assert_not_called()
    with patch.object(notes_client, "_find_candidates", return_value=[]) as fetch:
        notes_client.execute_note_plan({"skill_action": "lookup", "note_selector": {"scope_ids": ["zalo:group:other"]}}, thread_id="sample", thread_type="user", sender_id="sample")
        assert "scope_ids" not in fetch.call_args.args[1]
    print("PASS standalone record boundaries")


if __name__ == "__main__":
    main()
