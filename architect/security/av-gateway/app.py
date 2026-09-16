"""Antivirus gateway — async scan queue in front of ClamAV (clamd).

Session-level aggregation: upload many files → queue → CLEAN/INFECTED →
READY_FOR_PROCESSING or BLOCKED. Sits before OCR/parser/RAG.
"""
from __future__ import annotations

import asyncio
import os
import socket
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

CLAMAV_HOST = os.environ.get("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(os.environ.get("CLAMAV_PORT", "3310"))
WORKERS = max(1, int(os.environ.get("AV_QUEUE_WORKERS", "2")))
SCAN_TIMEOUT = int(os.environ.get("AV_SCAN_TIMEOUT_SECONDS", "120"))
QUARANTINE = Path(os.environ.get("AV_QUARANTINE_DIR", "/data/quarantine"))
try:
    QUARANTINE_DAYS = max(1, int(os.environ.get("AV_QUARANTINE_DAYS", "7")))
except ValueError:
    QUARANTINE_DAYS = 7

app = FastAPI(title="assistant-av-gateway", version="1.0.0")
MAX_FILE_BYTES = int(os.environ.get("AV_MAX_FILE_BYTES", str(50 * 1024 * 1024)))
MAX_PENDING_BYTES = int(os.environ.get("AV_MAX_PENDING_BYTES", str(128 * 1024 * 1024)))
MAX_QUEUE = int(os.environ.get("AV_MAX_QUEUE", "16"))
MAX_SESSIONS = int(os.environ.get("AV_MAX_SESSIONS", "2048"))
MAX_SESSION_FILES = int(os.environ.get("AV_MAX_SESSION_FILES", "64"))
SESSION_TTL = int(os.environ.get("AV_SESSION_TTL_SECONDS", "3600"))
if min(MAX_FILE_BYTES, MAX_PENDING_BYTES, MAX_QUEUE, MAX_SESSIONS, MAX_SESSION_FILES, SESSION_TTL) <= 0:
    raise ValueError("antivirus capacity limits must be positive")
if MAX_PENDING_BYTES < MAX_FILE_BYTES:
    raise ValueError("AV_MAX_PENDING_BYTES must cover one AV_MAX_FILE_BYTES upload")
_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=MAX_QUEUE)
_upload_slots = asyncio.Semaphore(WORKERS)
_request_slots = asyncio.Semaphore(WORKERS)
_pending_bytes = 0
_sessions: dict[str, dict[str, Any]] = {}
_files: dict[str, dict[str, Any]] = {}
_workers: list[asyncio.Task] = []


@app.middleware("http")
async def upload_request_limit(request, call_next):
    """Reject oversized/chunked multipart bodies before Starlette spools them."""
    path = request.url.path
    upload = request.method == "POST" and (path == "/v1/scan" or
              (path.startswith("/v1/sessions/") and path.endswith("/files")))
    if upload:
        length = request.headers.get("content-length", "")
        if not length.isascii() or not length.isdecimal() or request.headers.get("transfer-encoding"):
            return JSONResponse(status_code=411, content={"detail": "bounded content-length required for antivirus uploads"})
        if len(length) > 16 or int(length) > MAX_FILE_BYTES + 1024 * 1024:
            return JSONResponse(status_code=413, content={"detail": "antivirus request size limit exceeded"})
        if _request_slots.locked():
            return JSONResponse(status_code=429, content={"detail": "antivirus request capacity reached"})
        async with _request_slots:
            return await call_next(request)
    return await call_next(request)


def _flow(stage: str, **fields: Any) -> None:
    """Structured line for Loki: [flow] stage=... key=value ..."""
    parts = [f"[flow] stage={stage}"]
    for k, v in fields.items():
        if v is None:
            continue
        s = str(v).replace("\n", " ").replace('"', "'")
        if " " in s:
            s = f'"{s}"'
        parts.append(f"{k}={s}")
    print(" ".join(parts), flush=True)


class FileStatus(str, Enum):
    QUEUED = "QUEUED"
    SCANNING = "SCANNING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    ERROR = "ERROR"


class SessionStatus(str, Enum):
    SCANNING = "SCANNING"
    READY_FOR_PROCESSING = "READY_FOR_PROCESSING"
    BLOCKED = "BLOCKED"


def _clam_ping() -> bool:
    try:
        with socket.create_connection((CLAMAV_HOST, CLAMAV_PORT), timeout=3) as s:
            s.sendall(b"zPING\0")
            return s.recv(32).startswith(b"PONG")
    except OSError:
        return False


def _clam_scan_bytes(data: bytes) -> tuple[str, Optional[str]]:
    """INESCAN over clamd TCP. Returns (CLEAN|INFECTED|ERROR, signature?)."""
    try:
        with socket.create_connection((CLAMAV_HOST, CLAMAV_PORT), timeout=SCAN_TIMEOUT) as s:
            s.sendall(b"zINSTREAM\0")
            # chunked stream
            view = memoryview(data)
            chunk = 2048
            for i in range(0, len(view), chunk):
                part = view[i : i + chunk]
                s.sendall(len(part).to_bytes(4, "big") + part.tobytes())
            s.sendall((0).to_bytes(4, "big"))
            resp = s.recv(4096).decode("utf-8", errors="replace").strip()
    except OSError as e:
        return FileStatus.ERROR, str(e)
    if "OK" in resp and "FOUND" not in resp:
        return FileStatus.CLEAN, None
    if "FOUND" in resp:
        sig = resp.split(":", 1)[-1].replace("FOUND", "").strip()
        return FileStatus.INFECTED, sig or "unknown"
    return FileStatus.ERROR, resp or "empty clamd response"


def _recompute_session(session_id: str) -> None:
    sess = _sessions.get(session_id)
    if not sess:
        return
    files = [_files[fid] for fid in sess["file_ids"] if fid in _files]
    sess["total"] = len(files)
    sess["scanning"] = sum(1 for f in files if f["status"] in (FileStatus.QUEUED, FileStatus.SCANNING))
    sess["clean"] = sum(1 for f in files if f["status"] == FileStatus.CLEAN)
    sess["infected"] = sum(1 for f in files if f["status"] == FileStatus.INFECTED)
    sess["errors"] = sum(1 for f in files if f["status"] == FileStatus.ERROR)
    if sess["infected"] > 0:
        sess["status"] = SessionStatus.BLOCKED
    elif sess["scanning"] == 0 and sess["total"] > 0 and sess["errors"] == 0:
        sess["status"] = SessionStatus.READY_FOR_PROCESSING
    elif sess["scanning"] == 0 and sess["errors"] > 0 and sess["infected"] == 0:
        # treat scan errors as blocked for safety
        sess["status"] = SessionStatus.BLOCKED
    else:
        sess["status"] = SessionStatus.SCANNING
    sess["updated_at"] = time.time()


async def _worker(name: str) -> None:
    global _pending_bytes
    while True:
        fid = await _queue.get()
        meta = _files.get(fid)
        if not meta:
            _queue.task_done()
            continue
        meta["status"] = FileStatus.SCANNING
        _recompute_session(meta["session_id"])
        data: bytes = meta.pop("_bytes", b"")
        try:
            status, sig = await asyncio.to_thread(_clam_scan_bytes, data)
        except Exception:
            status, sig = FileStatus.ERROR, "scanner failure"
        finally:
            _pending_bytes -= len(data)
        meta["status"] = status
        meta["signature"] = sig
        meta["scanned_at"] = time.time()
        if status == FileStatus.INFECTED:
            qpath = QUARANTINE / f"{fid}_{meta.get('filename', 'file')}"
            try:
                QUARANTINE.mkdir(parents=True, exist_ok=True)
                qpath.write_bytes(data)
                meta["quarantine_path"] = str(qpath)
            except OSError:
                pass
        _recompute_session(meta["session_id"])
        sess = _sessions.get(meta["session_id"], {})
        _flow(
            "av_scan",
            session_id=meta["session_id"],
            file_id=fid,
            filename=meta.get("filename"),
            size=meta.get("size"),
            status=status,
            signature=sig or "",
            session_status=sess.get("status"),
            quarantine=meta.get("quarantine_path", ""),
        )
        del data
        _queue.task_done()


def _prune_quarantine() -> int:
    """Delete quarantine files older than AV_QUARANTINE_DAYS (default 7)."""
    if not QUARANTINE.is_dir():
        return 0
    cutoff = time.time() - QUARANTINE_DAYS * 86400
    n = 0
    try:
        for p in QUARANTINE.iterdir():
            try:
                if not p.is_file():
                    continue
                if p.stat().st_mtime < cutoff:
                    p.unlink()
                    n += 1
            except OSError:
                continue
    except OSError:
        return n
    if n:
        _flow("quarantine_prune", deleted=n, days=QUARANTINE_DAYS)
    return n


async def _prune_loop() -> None:
    while True:
        try:
            _prune_sessions()
            await asyncio.to_thread(_prune_quarantine)
        except Exception:
            pass
        await asyncio.sleep(60)


@app.on_event("startup")
async def _startup() -> None:
    try:
        QUARANTINE.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Never crash the gateway if quarantine mount is not writable yet
        pass
    await asyncio.to_thread(_prune_quarantine)
    _workers.append(asyncio.create_task(_prune_loop()))
    for i in range(WORKERS):
        _workers.append(asyncio.create_task(_worker(f"av-{i}")))


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "clamd": _clam_ping(),
        "host": CLAMAV_HOST,
        "port": CLAMAV_PORT,
        "queue": _queue.qsize(),
        "workers": WORKERS,
        "quarantine_days": QUARANTINE_DAYS,
        "pending_bytes": _pending_bytes,
        "max_file_bytes": MAX_FILE_BYTES,
        "max_pending_bytes": MAX_PENDING_BYTES,
        "max_queue": MAX_QUEUE,
        "sessions": len(_sessions),
        "max_sessions": MAX_SESSIONS,
        "max_session_files": MAX_SESSION_FILES,
        "session_ttl_seconds": SESSION_TTL,
    }


class ScanUrlReq(BaseModel):
    session_id: str = Field(..., min_length=1)
    url: str
    filename: str = "download.bin"


@app.post("/v1/sessions/{session_id}/files")
async def enqueue_upload(
    session_id: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    return await _read_and_enqueue(session_id, file)


@app.post("/v1/scan")
async def scan_upload(
    session_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    return await _read_and_enqueue(session_id, file)


def _prune_sessions() -> None:
    """Expire only completed records; never evict a queued or active scan."""
    cutoff = time.time() - SESSION_TTL
    for sid, sess in list(_sessions.items()):
        if sess.get("scanning", 0) or sess.get("updated_at", sess["created_at"]) >= cutoff:
            continue
        for fid in sess["file_ids"]:
            _files.pop(fid, None)
        _sessions.pop(sid, None)


async def _read_and_enqueue(session_id: str, file: UploadFile) -> dict[str, Any]:
    """Bound concurrent upload reads as well as bytes retained by scan jobs."""
    # Reject overload rather than holding an unbounded queue of upload coroutines.
    if _upload_slots.locked():
        await file.close()
        raise HTTPException(429, "antivirus upload capacity reached")
    async with _upload_slots:
        try:
            data = bytearray()
            while True:
                chunk = await file.read(min(1024 * 1024, MAX_FILE_BYTES - len(data) + 1))
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > MAX_FILE_BYTES:
                    raise HTTPException(413, "file exceeds antivirus size limit")
            return await _enqueue(session_id, file.filename or "upload.bin", bytes(data))
        finally:
            await file.close()


async def _enqueue(session_id: str, filename: str, data: bytes) -> dict[str, Any]:
    global _pending_bytes
    if not session_id.strip() or len(session_id) > 256:
        raise HTTPException(400, "invalid scan session")
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, "file exceeds antivirus size limit")
    _prune_sessions()
    if _queue.full() or _pending_bytes + len(data) > MAX_PENDING_BYTES:
        raise HTTPException(429, "antivirus scan capacity reached")
    if session_id not in _sessions and len(_sessions) >= MAX_SESSIONS:
        raise HTTPException(429, "antivirus session capacity reached")
    if len(_sessions.get(session_id, {}).get("file_ids", [])) >= MAX_SESSION_FILES:
        raise HTTPException(429, "antivirus session file limit reached")
    filename = Path(filename.replace("\\", "/").replace("\x00", "")).name[:180] or "upload.bin"
    if session_id not in _sessions:
        _sessions[session_id] = {
            "session_id": session_id,
            "file_ids": [],
            "status": SessionStatus.SCANNING,
            "created_at": time.time(),
        }
    fid = uuid.uuid4().hex
    _files[fid] = {
        "id": fid,
        "session_id": session_id,
        "filename": filename,
        "size": len(data),
        "status": FileStatus.QUEUED,
        "_bytes": data,
    }
    _sessions[session_id]["file_ids"].append(fid)
    _recompute_session(session_id)
    # No await between the admission checks and publication: one event-loop owner.
    _queue.put_nowait(fid)
    _pending_bytes += len(data)
    _flow(
        "av_enqueue",
        session_id=session_id,
        file_id=fid,
        filename=filename,
        size=len(data),
        queue=_queue.qsize(),
    )
    return {"ok": True, "file_id": fid, "session": _sessions[session_id]}


@app.get("/v1/sessions/{session_id}")
async def session_status(session_id: str) -> dict[str, Any]:
    _prune_sessions()
    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    files = [_files[fid] for fid in sess["file_ids"] if fid in _files]
    # strip internal bytes if any linger
    safe = []
    for f in files:
        safe.append({k: v for k, v in f.items() if not k.startswith("_")})
    return {**sess, "files": safe}


@app.get("/v1/sessions/{session_id}/ready")
async def session_ready(session_id: str) -> dict[str, Any]:
    sess = await session_status(session_id)
    return {
        "ready": sess["status"] == SessionStatus.READY_FOR_PROCESSING,
        "blocked": sess["status"] == SessionStatus.BLOCKED,
        "status": sess["status"],
        "clean": sess.get("clean", 0),
        "infected": sess.get("infected", 0),
        "scanning": sess.get("scanning", 0),
    }
