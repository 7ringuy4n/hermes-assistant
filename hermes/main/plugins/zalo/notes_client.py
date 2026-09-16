"""Typed client for scoped, durable notes in Memory Worker."""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from pathlib import Path


def memory_url() -> str:
    return (os.environ.get("MEMORY_URL") or "http://memory:8095").rstrip("/")


def note_scope(*, thread_id: str, thread_type: str, sender_id: str) -> str:
    if str(thread_type or "").strip().lower() == "group":
        return f"zalo:group:{str(thread_id).strip()}"
    return f"zalo:user:{str(sender_id).strip()}"


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        memory_url() + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    timeout = max(2.0, min(float(os.environ.get("NOTES_HTTP_TIMEOUT_S") or "8"), 30.0))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
        return data if isinstance(data, dict) else {"success": False, "error": "invalid_response"}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "error": f"http_{exc.code}", "detail": detail}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"success": False, "error": type(exc).__name__}


def _selector_payload(scope_id: str, selector: dict[str, Any]) -> dict[str, Any]:
    try:
        limit = int(selector.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    return {
        "scope_id": scope_id,
        "scope_ids": list(selector.get("scope_ids") or []),
        "id": str(selector.get("id") or "").strip() or None,
        "query": str(selector.get("query") or "").strip(),
        "date_from": selector.get("date_from"),
        "date_to": selector.get("date_to"),
        "tags": list(selector.get("tags") or []),
        "limit": max(1, min(limit, 1000)),
    }


def _find_candidates(scope_id: str, selector: dict[str, Any]) -> list[dict[str, Any]]:
    data = _request("POST", "/v1/notes/query", _selector_payload(scope_id, selector))
    if data.get("success") is not True:
        raise ValueError("note_service_unavailable")
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return [item for item in items if isinstance(item, dict)]


def _semantic_candidates(items: list[dict[str, Any]], predicate: str) -> list[dict[str, Any]]:
    try:
        from .media_shortcuts import _omni_json_plan
    except ImportError:
        from media_shortcuts import _omni_json_plan
    asset = Path(__file__).resolve().parents[2] / "skills/notes/prompts/select_records.txt"
    system = asset.read_text(encoding="utf-8")
    # Do not send internal metadata or unbounded record sets to the planner.
    records = [{key: item.get(key) for key in ("id", "title", "content", "note_date")}
               for item in items]
    payload = json.dumps({"predicate": predicate, "candidates": records}, ensure_ascii=False)
    try:
        budget = int(os.environ.get("NOTES_SELECTION_MAX_BYTES") or "131072")
    except ValueError:
        raise ValueError("invalid_note_selection_budget") from None
    if not 4096 <= budget <= 1048576 or len(payload.encode("utf-8")) > budget:
        raise ValueError("note_selection_window_exceeded")
    result = _omni_json_plan(system, payload, max_tokens=4096)
    ids = result.get("matches")
    allowed = {str(item.get("id")) for item in items}
    if result.get("uncertain") is not False or not isinstance(ids, list) or any(
        not isinstance(value, str) or value not in allowed for value in ids
    ):
        raise ValueError("note_selection_uncertain")
    return [item for item in items if str(item.get("id")) in set(ids)]


def list_existing_note_contents(
    *,
    thread_id: str,
    thread_type: str,
    sender_id: str,
    query: str = "",
    tags: list[str] | None = None,
    limit: int = 50,
) -> list[str]:
    """Return prior note bodies for soft dedupe before deferred create."""
    scope_id = note_scope(thread_id=thread_id, thread_type=thread_type, sender_id=sender_id)
    selector = {
        "query": str(query or "").strip(),
        "tags": list(tags or [])[:12],
        "limit": max(1, min(int(limit or 50), 100)),
    }
    items = _find_candidates(scope_id, selector)
    # Broad fallback: scope-wide recent notes when the topic query is empty/misses.
    if not items and (selector["query"] or selector["tags"]):
        items = _find_candidates(scope_id, {"query": "", "tags": [], "limit": selector["limit"]})
    out: list[str] = []
    for item in items:
        content = str(item.get("content") or "").strip()
        if content and content not in out:
            out.append(content)
    return out


def _candidate_lines(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(items[:10], start=1):
        prefix = str(item.get("note_date") or "—")
        title = str(item.get("title") or "").strip()
        if not title:
            title = str(item.get("content") or "").strip().splitlines()[0][:120]
        lines.append(f"{index}. [{prefix}] {title[:160]} (id: {item.get('id')})")
    return "\n".join(lines)


def _detail_text(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    content = str(item.get("content") or "").strip()
    if not title:
        title = content.splitlines()[0][:160] if content else "Note"
    date_text = str(item.get("note_date") or "—")
    meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    citations = [str(x).strip() for x in (meta.get("citations") or []) if str(x).strip()]
    cite_line = "\n\nSources: " + " | ".join(citations[:5]) if citations else ""
    return f"{title}\n[{date_text}]\n\n{content}{cite_line}".strip()


def execute_note_plan(
    plan: dict[str, Any],
    *,
    thread_id: str,
    thread_type: str,
    sender_id: str,
    admin_ids: set[str] | None = None,
    current_scope_id: str | None = None,
    override_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a validated note plan; never select an ambiguous mutation target.

    ``override_ids`` executes a previously previewed bulk mutation on the exact
    confirmed record ids instead of re-running model selection. A destructive
    bulk mutation is never applied from a single unconfirmed model pass.
    """
    scope_id = note_scope(thread_id=thread_id, thread_type=thread_type, sender_id=sender_id)
    action = str(plan.get("skill_action") or "").strip().lower()
    notes = [item for item in (plan.get("notes") or []) if isinstance(item, dict)]
    selector = plan.get("note_selector") if isinstance(plan.get("note_selector"), dict) else {}
    selector = dict(selector)
    # Multi-scope access is derived only from host authorization, never from
    # fields supplied by a model or standalone caller's plan.
    selector.pop("scope_ids", None)
    if current_scope_id is not None:
        if not current_scope_id.startswith("hermes:") or len(current_scope_id) > 256:
            return {"success": False, "error": "invalid_host_scope"}
        if selector.get("scope", "current") != "current" or selector.get("scope_ref"):
            return {"success": False, "error": "cross_scope_not_allowed"}
        scope_id = current_scope_id
    try:
        try:
            from .record_scope import resolve_record_target, registered_note_scopes
        except ImportError:
            from record_scope import resolve_record_target, registered_note_scopes
        target, target_type = resolve_record_target(
            selector, thread_id=thread_id, thread_type=thread_type,
            is_admin=str(sender_id) in (admin_ids or set()))
        if target is None:
            if action != "lookup":
                return {"success": False, "error": "all_scope_read_only"}
            selector["scope_ids"] = list(dict.fromkeys([scope_id, *registered_note_scopes()]))
        elif selector.get("scope", "current") != "current":
            scope_id = note_scope(thread_id=target, thread_type=target_type, sender_id=target)
            thread_id, thread_type = target, target_type
    except (ValueError, PermissionError) as exc:
        return {"success": False, "error": str(exc)}

    if action == "create":
        if not notes:
            return {"success": False, "error": "missing_notes"}
        created: list[dict[str, Any]] = []
        for item in notes:
            result = _request(
                "POST",
                "/v1/notes",
                {
                    "scope_id": scope_id,
                    "title": item.get("title"),
                    "content": item.get("content"),
                    "note_date": item.get("note_date"),
                    "thread_id": thread_id,
                    "thread_type": thread_type,
                    "owner_id": sender_id,
                    "tags": list(item.get("tags") or []),
                    "metadata": (
                        dict(item.get("metadata"))
                        if isinstance(item.get("metadata"), dict)
                        else {"source": "hermes" if current_scope_id is not None else "zalo"}
                    ),
                },
            )
            if not result.get("success"):
                return result
            created.append(result.get("note") or {})
        return {"success": True, "action": action, "count": len(created), "items": created}

    mutation = action in {"update", "delete"}
    if mutation or selector.get("view") == "count":
        selector = dict(selector)
        selector["limit"] = 1000
    if override_ids is not None:
        # Confirmed bulk mutation: trust exactly the previewed ids.
        candidates = [{"id": str(value)} for value in override_ids if str(value).strip()]
    else:
        predicate = str(selector.get("semantic_query") or "").strip()
        fetch_selector = dict(selector)
        if predicate:
            # SQL enforces scope/date; the model evaluates the complete predicate.
            fetch_selector.update(query="", tags=[], limit=1000)
        try:
            candidates = _find_candidates(scope_id, fetch_selector)
        except (ValueError, OSError) as exc:
            return {"success": False, "error": str(exc)}
        if (mutation or selector.get("view") == "count") and len(candidates) >= 1000:
            return {"success": False, "error": "note_selection_window_exceeded"}
        if predicate:
            if len(candidates) >= 1000:
                return {"success": False, "error": "note_selection_window_exceeded"}
            try:
                candidates = _semantic_candidates(candidates, predicate) if candidates else []
            except (ValueError, OSError) as exc:
                return {"success": False, "error": str(exc)}
    if action == "lookup":
        view = str(selector.get("view") or "list").strip().lower()
        if view == "count":
            text = f"{len(candidates)} note(s)."
        elif view == "detail" and len(candidates) == 1:
            text = _detail_text(candidates[0])
        else:
            text = _candidate_lines(candidates)
        return {
            "success": True,
            "action": action,
            "count": len(candidates),
            "items": candidates,
            "text": text,
        }

    if action not in {"update", "delete"}:
        return {"success": False, "error": "unsupported_action"}
    if not candidates:
        return {"success": False, "error": "not_found"}
    bulk_authorized = selector.get("match_all") is True or selector.get("bulk") is True
    if (len(candidates) != 1 and not bulk_authorized) or plan.get("uncertain") is True:
        return {
            "success": False,
            "error": "ambiguous",
            "count": len(candidates),
            "text": _candidate_lines(candidates),
        }
    # A destructive bulk mutation must never be applied from one unconfirmed
    # model pass. Return a preview; the host asks the user to confirm the exact
    # record ids before any delete/update runs.
    if override_ids is None and len(candidates) > 1 and plan.get("confirmed") is not True:
        return {
            "success": False,
            "error": "confirm",
            "action": action,
            "count": len(candidates),
            "ids": [str(candidate.get("id") or "") for candidate in candidates],
            "text": _candidate_lines(candidates),
        }

    if action == "delete":
        deleted: list[str] = []
        for candidate in candidates:
            note_id = str(candidate.get("id") or "")
            if not note_id:
                continue
            path = "/v1/notes/" + urllib.parse.quote(note_id, safe="")
            path += "?scope_id=" + urllib.parse.quote(scope_id, safe="")
            result = _request("DELETE", path)
            if not result.get("success"):
                return {**result, "count": len(deleted)}
            deleted.append(note_id)
        return {"success": True, "action": action, "count": len(deleted), "ids": deleted}
    if len(notes) != 1:
        return {"success": False, "error": "missing_update"}
    replacement = notes[0]
    updated: list[dict[str, Any]] = []
    for candidate in candidates:
        note_id = str(candidate.get("id") or "")
        if not note_id:
            continue
        result = _request(
            "PATCH",
            "/v1/notes/" + urllib.parse.quote(note_id, safe=""),
            {
                "scope_id": scope_id,
                "title": replacement.get("title"),
                "content": replacement.get("content"),
                "note_date": replacement.get("note_date"),
                "tags": list(replacement.get("tags") or []),
            },
        )
        if not result.get("success"):
            return {**result, "count": len(updated)}
        updated.append(result.get("note") or {})
    return {"success": True, "action": action, "count": len(updated), "items": updated}


async def execute_note_plan_async(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return await asyncio.to_thread(execute_note_plan, *args, **kwargs)
