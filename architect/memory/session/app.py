"""Redis conversation_active session store — Hermes live session SoT.

Keys: conversation_active:{session_id}
TTL from REDIS_CONVERSATION_TTL_SECONDS (default 1d).
"""
from __future__ import annotations

import json
import os
import time
import hashlib
from typing import Any, Optional

import httpx
import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("VALKEY_URL") or "redis://valkey:6379/0"
TTL = int(os.environ.get("REDIS_CONVERSATION_TTL_SECONDS", "86400"))
PREFIX = os.environ.get("SESSION_KEY_PREFIX", "conversation_active")
LOCK_PREFIX = os.environ.get("SESSION_LOCK_PREFIX", "session_lock")
LOCK_TTL_S = int(os.environ.get("SESSION_LOCK_TTL_SECONDS", "30"))
MEMORY_URL = os.environ.get("MEMORY_URL", "http://memory:8095").rstrip("/")
# Start a new conversation session once the previous one has been idle this long
# (default 1h). 0 disables idle rollover.
IDLE_ROLLOVER_DEFAULT_S = 3600
IDLE_ROLLOVER_MAX_S = 30 * 86400
# Comma-separated Redis key prefixes to wipe on reset-all (no trailing colon).
RESET_PREFIXES = [
    p.strip()
    for p in os.environ.get("SESSION_RESET_PREFIXES", PREFIX).split(",")
    if p.strip()
]

app = FastAPI(title="assistant-session", version="1.4.0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class SessionPut(BaseModel):
    session_id: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    append: bool = False


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        r.ping()
        return {"ok": True, "ttl": TTL, "prefix": PREFIX}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/v1/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    key = f"{PREFIX}:{session_id}"
    raw = r.get(key)
    if not raw:
        raise HTTPException(404, "not found")
    data = json.loads(raw)
    if isinstance(data, dict) and _should_rollover(
        data.get("updated_at"), time.time(), _idle_rollover_seconds()
    ):
        # Idle past the window: archive the old short-term session and report it
        # absent so the caller hydrates an empty context and starts fresh.
        _archive_best_effort(data, key)
        r.delete(key)
        raise HTTPException(404, "not found")
    return {"ok": True, "session": data}


def _idle_rollover_seconds() -> int:
    """Idle window before a live session is replaced, read per call."""
    try:
        val = int(os.environ.get("SESSION_IDLE_ROLLOVER_SECONDS") or str(IDLE_ROLLOVER_DEFAULT_S))
    except (TypeError, ValueError):
        val = IDLE_ROLLOVER_DEFAULT_S
    return max(0, min(val, IDLE_ROLLOVER_MAX_S))


def _should_rollover(updated_at: Any, now: float, idle_seconds: int) -> bool:
    """True when a live session has been idle long enough to start a new one."""
    if idle_seconds <= 0:
        return False
    try:
        prev = float(updated_at)
    except (TypeError, ValueError):
        return False
    if prev <= 0:
        return False
    return (now - prev) >= idle_seconds


@app.put("/v1/sessions/{session_id}")
def put_session(session_id: str, body: SessionPut) -> dict[str, Any]:
    key = f"{PREFIX}:{session_id}"
    cur: dict[str, Any] = {}
    if body.append:
        raw = r.get(key)
        if raw:
            cur = json.loads(raw)
    now = time.time()
    rolled_over = False
    archived = False
    if body.append and cur and _should_rollover(cur.get("updated_at"), now, _idle_rollover_seconds()):
        # The conversation rested past the idle window: archive the old
        # short-term session to long-term memory, then begin a fresh one.
        archived = _archive_best_effort(cur, key)
        cur = {}
        rolled_over = True
    messages = list(cur.get("messages") or [])
    if body.append:
        messages.extend(body.messages)
    else:
        messages = body.messages
    # keep last N messages (env SESSION_MAX_MESSAGES, default 16)
    try:
        cap = int(os.environ.get("SESSION_MAX_MESSAGES") or "16")
    except (TypeError, ValueError):
        cap = 16
    cap = max(4, min(40, cap))
    messages = messages[-cap:]
    created_at = (cur.get("created_at") if cur else None) or now
    data = {
        "session_id": session_id,
        "thread_id": body.thread_id or cur.get("thread_id"),
        "user_id": body.user_id or cur.get("user_id"),
        "messages": messages,
        "metadata": {**(cur.get("metadata") or {}), **body.metadata},
        "created_at": created_at,
        "updated_at": now,
    }
    r.setex(key, TTL, json.dumps(data, ensure_ascii=False))
    return {
        "ok": True,
        "session_id": session_id,
        "messages": len(messages),
        "ttl": TTL,
        "rolled_over": rolled_over,
        "archived": archived,
    }


class SessionLockBody(BaseModel):
    owner: str = Field(..., min_length=1, max_length=128)
    ttl_seconds: Optional[int] = None


@app.post("/v1/sessions/{session_id}/lock")
def acquire_lock(session_id: str, body: SessionLockBody) -> dict[str, Any]:
    """Per-session lock (Valkey) so Hermes×2 does not race the same chat."""
    ttl = int(body.ttl_seconds or LOCK_TTL_S)
    if ttl < 1:
        ttl = LOCK_TTL_S
    key = f"{LOCK_PREFIX}:{session_id}"
    ok = r.set(key, body.owner, nx=True, ex=ttl)
    if ok:
        return {"ok": True, "acquired": True, "owner": body.owner, "ttl": ttl}
    cur = r.get(key)
    if cur == body.owner:
        r.expire(key, ttl)
        return {"ok": True, "acquired": True, "owner": body.owner, "ttl": ttl, "renewed": True}
    raise HTTPException(status_code=409, detail={"acquired": False, "owner": cur})


@app.delete("/v1/sessions/{session_id}/lock")
def release_lock(session_id: str, owner: str) -> dict[str, Any]:
    key = f"{LOCK_PREFIX}:{session_id}"
    cur = r.get(key)
    if cur is None:
        return {"ok": True, "released": False, "reason": "absent"}
    if cur != owner:
        raise HTTPException(status_code=403, detail={"released": False, "owner": cur})
    r.delete(key)
    return {"ok": True, "released": True}


@app.delete("/v1/sessions/{session_id}")
def del_session(session_id: str) -> dict[str, Any]:
    n = r.delete(f"{PREFIX}:{session_id}")
    return {"ok": True, "deleted": int(n)}


@app.post("/v1/sessions/{session_id}/touch")
def touch(session_id: str) -> dict[str, Any]:
    key = f"{PREFIX}:{session_id}"
    if not r.exists(key):
        raise HTTPException(404, "not found")
    r.expire(key, TTL)
    return {"ok": True, "ttl": TTL}


def _scan_delete_prefix(prefix: str) -> int:
    """Delete all keys matching {prefix}:* via SCAN (safe for large keyspaces)."""
    pattern = f"{prefix}:*"
    deleted = 0
    cursor = 0
    while True:
        cursor, keys = r.scan(cursor=cursor, match=pattern, count=200)
        if keys:
            deleted += int(r.delete(*keys))
        if cursor == 0:
            break
    return deleted


def _session_blob_to_ltm(data: dict[str, Any]) -> str:
    sid = str(data.get("session_id") or "")
    tid = str(data.get("thread_id") or "")
    uid = str(data.get("user_id") or "")
    msgs = data.get("messages") or []
    lines: list[str] = []
    for m in msgs[-20:]:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or m.get("type") or "user")[:12]
        content = str(m.get("content") or m.get("text") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content[:400]}")
    body = "\n".join(lines).strip()
    if not body:
        return ""
    head = f"[archived session {sid} thread={tid} user={uid}]\n"
    return (head + body)[:3900]


def _archive_session_data(
    data: dict[str, Any],
    key: str = "",
    *,
    source: str = "session-rollover",
    tags: tuple[str, ...] = ("archived-session",),
) -> bool:
    """Store one live session blob in long-term memory. Callers handle errors."""
    if not MEMORY_URL:
        return False
    content = _session_blob_to_ltm(data)
    if len(content) < 20:
        return False
    with httpx.Client(timeout=8.0) as c:
        resp = c.post(
            f"{MEMORY_URL}/v1/remember",
            json={
                "content": content,
                "type": "event",
                "importance": 0.55,
                "source": source,
                "session_id": str(data.get("session_id") or ""),
                "thread_id": str(data.get("thread_id") or ""),
                "tags": list(tags),
                "metadata": {"from": "redis", "key": str(key)},
                "force": True,
            },
        )
    return resp.status_code < 300


def _archive_best_effort(
    data: dict[str, Any],
    key: str = "",
    *,
    source: str = "session-rollover",
    tags: tuple[str, ...] = ("archived-session",),
) -> bool:
    """Archive without ever failing the caller's turn."""
    try:
        return _archive_session_data(data, key, source=source, tags=tags)
    except Exception:
        return False


def _archive_sessions_to_ltm() -> dict[str, Any]:
    """Copy live Redis conversations into memory-worker before wipe."""
    archived = 0
    skipped = 0
    errors = 0
    if not MEMORY_URL:
        return {"archived": 0, "skipped": 0, "errors": 0, "reason": "MEMORY_URL empty"}
    for prefix in RESET_PREFIXES:
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor=cursor, match=f"{prefix}:*", count=100)
            for key in keys:
                try:
                    raw = r.get(key)
                    if not raw:
                        skipped += 1
                        continue
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        skipped += 1
                        continue
                    if _archive_session_data(
                        data, key, source="clearsession", tags=("archived-session", "clearsession")
                    ):
                        archived += 1
                    else:
                        skipped += 1
                except Exception:
                    errors += 1
            if cursor == 0:
                break
    return {"archived": archived, "skipped": skipped, "errors": errors}


@app.post("/v1/sessions/reset-all")
def reset_all_sessions() -> dict[str, Any]:
    """Archive live Redis sessions to LTM, then wipe — forces a new chat session."""
    archive = _archive_sessions_to_ltm()
    by_prefix: dict[str, int] = {}
    total = 0
    for p in RESET_PREFIXES:
        n = _scan_delete_prefix(p)
        by_prefix[p] = n
        total += n
    return {
        "ok": True,
        "deleted": total,
        "by_prefix": by_prefix,
        "prefixes": RESET_PREFIXES,
        "ltm": archive,
    }


# --- Per-turn timing (messaging footer) ---
TIMING_PREFIX = "nh:turn"
TIMING_ACTIVE = "nh:turn:active"
TIMING_TTL = 600


class TimingStart(BaseModel):
    thread_id: str
    t0: float
    t_handoff: float
    recv_s: float = 0.0


class TimingAdd(BaseModel):
    field: str  # workflow_s | llm_s
    seconds: float
    thread_id: Optional[str] = None


def _timing_key(thread_id: str) -> str:
    return f"{TIMING_PREFIX}:{thread_id}"


TIMING_CURRENT = "nh:turn:current"
TIMING_CURRENT_TYPE = "nh:turn:current_type"
TURN_SOURCE_PREFIX = "nh:turn:source"
SENTFILE_PREFIX = "nh:sentfile"
SENTFILE_TTL = 600


def _timing_current() -> Optional[str]:
    """Newest/current messaging turn, never the oldest stale one."""
    cutoff = time.time() - TIMING_TTL
    try:
        r.zremrangebyscore(TIMING_ACTIVE, "-inf", cutoff)
        cur = r.get(TIMING_CURRENT)
        if cur:
            return str(cur)
        items = r.zrange(TIMING_ACTIVE, -1, -1)
        return str(items[0]) if items else None
    except Exception:
        return None


@app.post("/v1/timing/start")
def timing_start(body: TimingStart) -> dict[str, Any]:
    tid = (body.thread_id or "").strip()
    if not tid:
        raise HTTPException(400, "thread_id required")
    key = _timing_key(tid)
    existing = r.hgetall(key) or {}
    mapping: dict[str, Any] = {
        "t0": body.t0,
        "t_handoff": body.t_handoff,
        "recv_s": body.recv_s,
    }
    # Do not zero workflow_s/llm_s — dispatcher may have already recorded.
    if not existing:
        mapping["workflow_s"] = 0
        mapping["llm_s"] = 0
    r.hset(key, mapping=mapping)
    r.expire(key, TIMING_TTL)
    r.zadd(TIMING_ACTIVE, {tid: body.t_handoff or time.time()})
    r.set(TIMING_CURRENT, tid, ex=TIMING_TTL)
    return {"ok": True, "thread_id": tid}


class TurnDest(BaseModel):
    thread_id: str
    thread_type: str = "user"
    source_message_id: str = ""


class FileClaim(BaseModel):
    key: str
    thread_id: str = ""
    thread_type: str = "user"
    source_message_id: str = ""
    token: str = ""


class FileTransition(FileClaim):
    state: str
    message_id: str = ""


def _file_receipt_key(thread_id: str, thread_type: str, source_message_id: str) -> str:
    identity = json.dumps([thread_type, thread_id, source_message_id], ensure_ascii=True)
    return f"{SENTFILE_PREFIX}:receipts:{hashlib.sha256(identity.encode()).hexdigest()}"


@app.post("/v1/turn/dest")
def turn_dest_set(body: TurnDest) -> dict[str, Any]:
    """Remember which conversation asked; outbound files must return there."""
    tid = (body.thread_id or "").strip()
    if not tid:
        raise HTTPException(400, "thread_id required")
    tt = body.thread_type if body.thread_type in {"user", "group"} else "user"
    r.set(TIMING_CURRENT, tid, ex=TIMING_TTL)
    r.set(TIMING_CURRENT_TYPE, tt, ex=TIMING_TTL)
    source = (body.source_message_id or "").strip()
    if source:
        r.set(f"{TURN_SOURCE_PREFIX}:{tt}:{tid}", source, ex=TIMING_TTL)
    return {
        "ok": True,
        "thread_id": tid,
        "thread_type": tt,
        "source_message_id": source,
    }


@app.get("/v1/turn/dest")
def turn_dest_get() -> dict[str, Any]:
    tid = r.get(TIMING_CURRENT)
    tt = r.get(TIMING_CURRENT_TYPE)
    if isinstance(tid, (bytes, bytearray)):
        tid = tid.decode()
    if isinstance(tt, (bytes, bytearray)):
        tt = tt.decode()
    return {
        "ok": bool(tid),
        "thread_id": str(tid or ""),
        "thread_type": tt if tt in {"user", "group"} else "user",
    }


@app.get("/v1/turn/source/{thread_id}")
def turn_source_get(thread_id: str, thread_type: str = "user") -> dict[str, Any]:
    """Return the source message bound to one conversation, never a global turn."""
    tid = (thread_id or "").strip()
    if not tid:
        raise HTTPException(400, "thread_id required")
    tt = thread_type if thread_type in {"user", "group"} else "user"
    source = r.get(f"{TURN_SOURCE_PREFIX}:{tt}:{tid}") or ""
    if isinstance(source, (bytes, bytearray)):
        source = source.decode()
    return {"ok": bool(source), "source_message_id": str(source)}


@app.post("/v1/files/claim")
def file_claim(body: FileClaim) -> dict[str, Any]:
    """Reserve an artifact; a pending reservation is not a delivery receipt."""
    key = (body.key or "").strip()
    if not key or len(key) > 256:
        raise HTTPException(400, "key required")
    if not body.token or not body.thread_id or body.thread_type not in {"user", "group"}:
        raise HTTPException(400, "bound destination and claim token required")
    redis_key = f"{SENTFILE_PREFIX}:v2:{key}"
    record = {"token": body.token, "state": "reserved", "message_id": "",
              "thread_id": body.thread_id, "thread_type": body.thread_type,
              "source_message_id": body.source_message_id}
    first = bool(r.set(redis_key, json.dumps(record), nx=True, ex=SENTFILE_TTL))
    current = json.loads(r.get(redis_key) or "{}")
    return {"ok": True, "first": first, "state": current.get("state", "unknown"),
            "message_id": current.get("message_id", "")}


@app.post("/v1/files/transition")
def file_transition(body: FileTransition) -> dict[str, Any]:
    """Token-checked atomic send/ACK/release; uncertain sends remain quarantined."""
    if body.state not in {"sending", "acknowledged", "release"} or not body.token:
        raise HTTPException(400, "valid transition and token required")
    if body.state == "acknowledged" and not body.message_id.strip():
        raise HTTPException(400, "bridge acknowledgement id required")
    redis_key = f"{SENTFILE_PREFIX}:v2:{body.key}"
    receipt_key = _file_receipt_key(body.thread_id, body.thread_type, body.source_message_id)
    # A sending claim cannot expire on the normal reservation timeout. Without
    # bridge idempotency, a crash/timeout needs reconciliation, not blind replay.
    script = """
local raw = redis.call('GET', KEYS[1])
if not raw then return 0 end
local record = cjson.decode(raw)
if record.token ~= ARGV[1] then return 0 end
if record.thread_id ~= ARGV[5] or record.thread_type ~= ARGV[6] or record.source_message_id ~= ARGV[7] then return 0 end
if record.state == 'acknowledged' then return 0 end
if ARGV[2] == 'release' then redis.call('DEL', KEYS[1]); return 1 end
if ARGV[2] == 'sending' and record.state ~= 'reserved' then return 0 end
if ARGV[2] == 'acknowledged' and record.state ~= 'sending' then return 0 end
record.state = ARGV[2]
record.message_id = ARGV[3]
redis.call('SET', KEYS[1], cjson.encode(record))
if ARGV[2] == 'acknowledged' then
  redis.call('EXPIRE', KEYS[1], ARGV[4])
  redis.call('HSET', KEYS[2], KEYS[1], ARGV[3])
  redis.call('EXPIRE', KEYS[2], ARGV[4])
end
return 1
"""
    changed = r.eval(script, 2, redis_key, receipt_key, body.token, body.state, body.message_id, TTL,
                     body.thread_id, body.thread_type, body.source_message_id)
    if not changed:
        raise HTTPException(409, "claim ownership or state changed")
    return {"ok": True, "state": body.state}


@app.get("/v1/files/receipts/{thread_id}")
def file_receipts(thread_id: str, thread_type: str = "user", source_message_id: str = "") -> dict[str, Any]:
    if not thread_id.strip() or not source_message_id.strip() or thread_type not in {"user", "group"}:
        raise HTTPException(400, "exact conversation source required")
    count = r.hlen(_file_receipt_key(thread_id, thread_type, source_message_id))
    return {"ok": True, "acknowledged_count": int(count)}


@app.post("/v1/timing/add")
def timing_add(body: TimingAdd) -> dict[str, Any]:
    field = (body.field or "").strip()
    if field not in {"workflow_s", "llm_s"}:
        raise HTTPException(400, "field must be workflow_s or llm_s")
    sec = float(body.seconds or 0)
    if sec < 0:
        sec = 0.0
    tid = (body.thread_id or "").strip() or _timing_current()
    if not tid:
        return {"ok": False, "error": "no active turn"}
    key = _timing_key(tid)
    r.hincrbyfloat(key, field, sec)
    r.expire(key, TIMING_TTL)
    return {"ok": True, "thread_id": tid, "field": field, "seconds": sec}


@app.post("/v1/timing/{thread_id}/finish")
def timing_finish(thread_id: str) -> dict[str, Any]:
    tid = (thread_id or "").strip()
    key = _timing_key(tid)
    raw = r.hgetall(key)
    r.delete(key)
    r.zrem(TIMING_ACTIVE, tid)
    try:
        cur = r.get(TIMING_CURRENT)
        if cur is not None and (cur.decode() if isinstance(cur, (bytes, bytearray)) else str(cur)) == tid:
            r.delete(TIMING_CURRENT)
    except Exception:
        pass
    data = {}
    for k, v in (raw or {}).items():
        kk = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
        try:
            data[kk] = float(v)
        except (TypeError, ValueError):
            continue
    return {"ok": True, "thread_id": tid, "timing": data}
