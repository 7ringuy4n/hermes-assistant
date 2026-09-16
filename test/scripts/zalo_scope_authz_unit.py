# -*- coding: utf-8 -*-
"""Unit: Zalo role-based record scope isolation.

A group member may only read the records of the group they are in; any DM user
may only read their own DM; only the operator admin may read another registered
group/DM or the whole scope.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

import record_scope  # noqa: E402
import schedule_client  # noqa: E402


def main() -> int:
    checks: list[tuple[str, bool]] = []

    # current scope resolves to the member's own conversation only.
    target, kind = record_scope.resolve_record_target({}, thread_id="groupB", thread_type="group", is_admin=False)
    checks.append(("group member current scope is own group (group)", target == "groupB" and kind == "group"))
    target, kind = record_scope.resolve_record_target({}, thread_id="userB", thread_type="user", is_admin=False)
    checks.append(("dm user current scope is own dm (user)", target == "userB" and kind == "user"))

    # non-admin cannot read another group, another dm, or all.
    for scope in ("group", "dm", "all"):
        selector = {"scope": scope}
        if scope != "all":
            selector["scope_ref"] = "Sample Other"
        try:
            record_scope.resolve_record_target(selector, thread_id="userB", thread_type="user", is_admin=False)
            forbidden = False
        except PermissionError:
            forbidden = True
        except ValueError:
            forbidden = False
        checks.append((f"non-admin {scope} cross-scope forbidden", forbidden))

    # unknown scope is rejected for everyone.
    try:
        record_scope.resolve_record_target({"scope": "planet"}, thread_id="u", thread_type="user", is_admin=True)
        checks.append(("unknown scope rejected", False))
    except ValueError:
        checks.append(("unknown scope rejected", True))

    # admin resolves a registered group / dm by reference.
    with patch("channels_client.resolve_channel", return_value={"kind": "group", "external_id": "groupA"}):
        target, kind = record_scope.resolve_record_target(
            {"scope": "group", "scope_ref": "Sample Group"}, thread_id="admin", thread_type="user", is_admin=True
        )
        checks.append(("admin group cross-scope resolves", target == "groupA" and kind == "group"))
    with patch("channels_client.resolve_channel", return_value={"kind": "dm", "external_id": "userA"}):
        target, kind = record_scope.resolve_record_target(
            {"scope": "dm", "scope_ref": "Sample User"}, thread_id="admin", thread_type="user", is_admin=True
        )
        checks.append(("admin dm cross-scope resolves", target == "userA" and kind == "user"))
    target, kind = record_scope.resolve_record_target(
        {"scope": "all"}, thread_id="admin", thread_type="user", is_admin=True
    )
    checks.append(("admin all resolves", target is None and kind == "all"))

    # admin referencing an unknown conversation fails closed.
    with patch("channels_client.resolve_channel", return_value=None):
        try:
            record_scope.resolve_record_target(
                {"scope": "group", "scope_ref": "Missing"}, thread_id="admin", thread_type="user", is_admin=True
            )
            checks.append(("admin unknown ref fails closed", False))
        except ValueError:
            checks.append(("admin unknown ref fails closed", True))

    # schedule visibility: a group schedule never appears in a member's DM list.
    rows = [
        {"id": "g1", "origin": {"thread_id": "groupA", "user_id": "u"}, "context": {"thread_id": "groupA", "thread_type": "group"}},
        {"id": "d1", "origin": {"thread_id": "u"}, "context": {"thread_id": "u", "thread_type": "user"}},
    ]
    with patch.object(schedule_client, "list_schedules", return_value=rows):
        checks.append(("member DM sees only own schedules", [r["id"] for r in schedule_client.schedules_for_thread("u", "user")] == ["d1"]))
        checks.append(("member group sees only that group", [r["id"] for r in schedule_client.schedules_for_thread("groupA", "group")] == ["g1"]))
        checks.append(("admin all sees both", len(schedule_client.schedules_for_record_scope(
            {"scope": "all"}, thread_id="admin", thread_type="user", is_admin=True)) == 2))

    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
