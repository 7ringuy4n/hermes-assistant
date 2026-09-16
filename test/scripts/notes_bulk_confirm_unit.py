# -*- coding: utf-8 -*-
"""Unit: destructive bulk note mutations require confirmation; exact ids apply.

Covers the class where a single model selection pass could silently delete or
overwrite several durable notes (including records the user asked to keep).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

import notes_client  # noqa: E402

STORE: dict[str, dict] = {}
SCOPE = "zalo:user:u1"


def fake_request(method: str, path: str, payload=None):
    payload = payload or {}
    if method == "POST" and path == "/v1/notes/query":
        wanted = str(payload.get("id") or "")
        items = [
            note
            for note in STORE.values()
            if (not payload.get("scope_id") or note.get("scope_id") == payload.get("scope_id"))
            and (not wanted or note.get("id") == wanted)
        ]
        return {"success": True, "items": items, "count": len(items)}
    if method == "DELETE":
        note_id = path.rsplit("/", 1)[-1].split("?", 1)[0]
        if note_id in STORE:
            STORE.pop(note_id)
            return {"success": True}
        return {"success": False, "error": "not_found"}
    return {"success": False, "error": "unhandled"}


def seed() -> None:
    STORE.clear()
    for index in range(3):
        note_id = f"note_{index}"
        STORE[note_id] = {
            "id": note_id,
            "title": f"Java vacancy {index}",
            "content": "Java recruitment posting",
            "tags": ["java"],
            "scope_id": SCOPE,
        }
    for index in range(2):
        note_id = f"note_other_{index}"
        STORE[note_id] = {
            "id": note_id,
            "title": f"Personal note {index}",
            "content": "buy milk and check passport",
            "tags": ["personal"],
            "scope_id": SCOPE,
        }


def main() -> int:
    checks: list[tuple[str, bool]] = []

    seed()
    with patch.object(notes_client, "_request", side_effect=fake_request), patch.object(
        notes_client, "_semantic_candidates", side_effect=lambda items, predicate: list(items)
    ):
        preview = notes_client.execute_note_plan(
            {
                "skill_action": "delete",
                "note_selector": {"semantic_query": "notes that are not java recruitment", "bulk": True},
            },
            thread_id="u1",
            thread_type="user",
            sender_id="u1",
        )
        checks.append(("bulk delete previews without deleting", preview.get("error") == "confirm"))
        checks.append(("preview lists every matched id", len(preview.get("ids") or []) == 5))
        checks.append(("no record removed before confirmation", len(STORE) == 5))

    with patch.object(notes_client, "_request", side_effect=fake_request), patch.object(
        notes_client, "_semantic_candidates", side_effect=AssertionError("selection must not run")
    ):
        confirmed = notes_client.execute_note_plan(
            {
                "skill_action": "delete",
                "confirmed": True,
                "note_selector": {"semantic_query": "notes that are not java recruitment", "bulk": True},
            },
            thread_id="u1",
            thread_type="user",
            sender_id="u1",
            override_ids=["note_other_0", "note_other_1"],
        )
        checks.append(("confirmed delete applies exact previewed ids", confirmed.get("success") and confirmed.get("count") == 2))
        checks.append(("wanted records survive", all(f"note_{i}" in STORE for i in range(3))))
        checks.append(("confirmed records are gone", not any(k.startswith("note_other") for k in STORE)))

    seed()
    with patch.object(notes_client, "_request", side_effect=fake_request):
        single = notes_client.execute_note_plan(
            {"skill_action": "delete", "note_selector": {"id": "note_0"}},
            thread_id="u1",
            thread_type="user",
            sender_id="u1",
        )
        checks.append(("single-record delete proceeds directly", single.get("success") and single.get("count") == 1))

    ux = json.loads(
        (ROOT / "hermes" / "main" / "messages" / "ux.json").read_text(encoding="utf-8")
    )
    notes_ux = ux.get("notes") or {}
    checks.append(("delete reply is distinct from saved", "deleted" in notes_ux and "saved" in notes_ux))
    checks.append(("update reply is distinct", "updated" in notes_ux))
    checks.append(("confirmation copy exists", "confirm" in notes_ux))
    adapter = (ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py").read_text(encoding="utf-8")
    checks.append(("adapter emits delete copy", "ZALO_NOTES_DELETED_MSG" in adapter))
    checks.append(("adapter emits update copy", "ZALO_NOTES_UPDATED_MSG" in adapter))
    checks.append(("adapter emits confirm copy", "ZALO_NOTES_CONFIRM_MSG" in adapter))

    canonical = (ROOT / "architect" / "lib" / "artifact_delivery.py").read_text(encoding="utf-8")
    vendored = (
        ROOT / "hermes" / "main" / "plugins" / "zalo" / "artifact_delivery.py"
    ).read_text(encoding="utf-8")
    normalize = lambda text: text.replace("\r\n", "\n").strip()
    checks.append(("vendored artifact_delivery matches canonical", normalize(canonical) == normalize(vendored)))

    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
