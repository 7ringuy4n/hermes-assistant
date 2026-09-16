"""Real Memory CRUD via the direct skill command, with no messaging identity."""
import json
import argparse
import subprocess
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--without-messaging", action="store_true")
    options = parser.parse_args()
    scope = "hermes:qa:" + uuid.uuid4().hex
    note_id = ""

    def execute(plan, namespace=None):
        command = ["docker", "exec", "-i", "-e", "HERMES_RECORD_SCOPE=" + (namespace or scope)]
        if options.without_messaging:
            # Child-process fault injection only; operator configuration is untouched.
            command += ["-e", "ENABLE_ZALO=inactive", "-e", "ZALO_API_URL=http://127.0.0.1:1",
                        "-e", "ZALO_BRIDGE_URL=http://127.0.0.1:1"]
        result = subprocess.run(command + ["assistant-hermes-1", "python", "-B", "/opt/data/skills/notes/scripts/notes.py"],
                                input=json.dumps(plan), text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError("standalone_note_command_failed")
        data = json.loads(result.stdout)
        assert data.get("success") is True
        return data

    try:
        print("running test case 1/4 direct note create", flush=True)
        created = execute({"skill_action": "create", "notes": [{"title": "Sample idea", "content": "Sample technical idea"}]})
        note_id = created["items"][0]["id"]
        assert created["count"] == 1
        print("running test case 2/4 direct count and detail", flush=True)
        assert execute({"skill_action": "lookup", "note_selector": {"view": "count"}})["count"] == 1
        assert execute({"skill_action": "lookup", "note_selector": {"view": "count"}}, scope + ":other")["count"] == 0
        assert execute({"skill_action": "lookup", "note_selector": {"id": note_id, "view": "detail"}})["items"][0]["content"] == "Sample technical idea"
        print("running test case 3/4 direct selected update", flush=True)
        updated = execute({"skill_action": "update", "note_selector": {"id": note_id}, "notes": [{"title": "Sample revised idea", "content": "Sample revised content"}]})
        assert updated["items"][0]["content"] == "Sample revised content"
        print("running test case 4/4 direct selected delete", flush=True)
        assert execute({"skill_action": "delete", "note_selector": {"id": note_id}})["count"] == 1
        note_id = ""
        assert execute({"skill_action": "lookup", "note_selector": {"view": "count"}})["count"] == 0
        print("PASS standalone live note CRUD", flush=True)
    finally:
        if note_id:
            execute({"skill_action": "delete", "note_selector": {"id": note_id}})


if __name__ == "__main__":
    main()
