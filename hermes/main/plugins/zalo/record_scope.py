"""Trusted conversation boundaries for notes and schedule administration."""
from __future__ import annotations

from typing import Any


def resolve_record_target(selector: dict[str, Any], *, thread_id: str,
                          thread_type: str, is_admin: bool) -> tuple[str | None, str]:
    kind = str(selector.get("scope") or "current").strip().lower()
    ref = str(selector.get("scope_ref") or "").strip()
    if kind == "current" and not ref:
        return str(thread_id), "group" if thread_type == "group" else "user"
    if kind not in {"all", "group", "dm"}:
        raise ValueError("invalid_record_scope")
    # Identity comes from the inbound principal, never a model-provided role.
    if not is_admin:
        raise PermissionError("record_scope_forbidden")
    if kind == "all":
        if ref:
            raise ValueError("invalid_record_scope")
        return None, "all"
    if not ref:
        raise ValueError("missing_record_scope_reference")
    try:
        from .channels_client import resolve_channel
    except ImportError:
        from channels_client import resolve_channel
    channel = resolve_channel(ref)
    expected = "group" if kind == "group" else "user"
    resolved_kind = "user" if channel and channel.get("kind") == "dm" else (channel or {}).get("kind")
    if not channel or resolved_kind != expected or not channel.get("external_id"):
        raise ValueError("record_scope_not_found")
    return str(channel["external_id"]), expected


def registered_note_scopes() -> list[str]:
    """Enumerate known conversations through the authenticated registry API."""
    try:
        from .channels_client import _req
    except ImportError:
        from channels_client import _req
    data = _req("GET", "/v1/channels?platform=zalo")
    if data.get("ok") is not True or not isinstance(data.get("channels"), list):
        raise ValueError("record_scope_registry_unavailable")
    return list(dict.fromkeys(
        f"zalo:{'group' if row.get('kind') == 'group' else 'user'}:{row['external_id']}"
        for row in data["channels"] if isinstance(row, dict)
        and row.get("kind") in {"group", "user", "dm"} and row.get("external_id")
    ))
