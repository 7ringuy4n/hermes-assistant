"""Actual gateway admission/worker methods with isolated state; no live malware."""
import ast
import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        super().__init__(detail)


def load_gateway():
    tree = ast.parse((ROOT / "architect/security/av-gateway/app.py").read_text(encoding="utf-8"))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module in {"fastapi", "fastapi.responses", "pydantic"}:
            continue
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets):
            continue
        if isinstance(node, ast.ClassDef) and node.name == "ScanUrlReq":
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.decorator_list = []
        nodes.append(node)
    ns = {"HTTPException": HTTPException, "UploadFile": object,
          "JSONResponse": lambda **kwargs: SimpleNamespace(**kwargs),
          "File": lambda *args, **kwargs: None, "Form": lambda *args, **kwargs: None}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "actual-av-gateway", "exec"), ns)
    return ns


async def rejected(call, expected):
    try:
        await call
    except HTTPException as exc:
        assert exc.status_code == expected, str(exc)
    else:
        raise AssertionError("unsafe admission succeeded")


async def cases():
    ns = load_gateway()
    checks = []

    def reset():
        ns["_sessions"].clear(); ns["_files"].clear()
        ns["_pending_bytes"] = 0
        ns["_queue"] = asyncio.Queue(maxsize=2)
        ns.update(MAX_FILE_BYTES=8, MAX_PENDING_BYTES=12, MAX_SESSIONS=2, MAX_SESSION_FILES=2, SESSION_TTL=10)

    reset()
    async def next_handler(request): return "accepted"
    request = SimpleNamespace(method="POST", url=SimpleNamespace(path="/v1/scan"), headers={})
    assert (await ns["upload_request_limit"](request, next_handler)).status_code == 411
    request.headers = {"content-length": str(1024 * 1024 + 9)}
    assert (await ns["upload_request_limit"](request, next_handler)).status_code == 413
    request.headers = {"content-length": "8", "transfer-encoding": "chunked"}
    assert (await ns["upload_request_limit"](request, next_handler)).status_code == 411
    request.headers = {"content-length": "8"}
    assert await ns["upload_request_limit"](request, next_handler) == "accepted"
    ns["_request_slots"] = asyncio.Semaphore(0)
    assert (await ns["upload_request_limit"](request, next_handler)).status_code == 429
    ns["_request_slots"] = asyncio.Semaphore(2)
    checks.append("multipart request limits apply before parser spooling")
    await rejected(ns["_enqueue"]("fixture", "test.bin", b"x" * 9), 413)
    await rejected(ns["_enqueue"]("fixture", "test.bin", b""), 400)
    await rejected(ns["_enqueue"](" ", "test.bin", b"x"), 400)
    assert not ns["_files"] and ns["_pending_bytes"] == 0
    checks.append("invalid, empty and oversize uploads leave no scan state")
    first = await ns["_enqueue"]("fixture", "../../escape\\payload.bin", b"x" * 7)
    assert ns["_files"][first["file_id"]]["filename"] == "payload.bin"
    checks.append("quarantine filename cannot escape its directory")
    await rejected(ns["_enqueue"]("other", "test.bin", b"x" * 6), 429)
    assert len(ns["_files"]) == 1 and ns["_pending_bytes"] == 7
    checks.append("pending-byte overload is atomic and fail closed")
    reset()
    await ns["_enqueue"]("one", "test.bin", b"x")
    await ns["_enqueue"]("two", "test.bin", b"x")
    await rejected(ns["_enqueue"]("three", "test.bin", b"x"), 429)
    assert len(ns["_files"]) == 2
    checks.append("bounded queue rejects instead of retaining more work")
    reset(); ns["_queue"] = asyncio.Queue(maxsize=8)
    await ns["_enqueue"]("one", "test.bin", b"x")
    await ns["_enqueue"]("two", "test.bin", b"x")
    await rejected(ns["_enqueue"]("three", "test.bin", b"x"), 429)
    await ns["_enqueue"]("one", "test.bin", b"x")
    await rejected(ns["_enqueue"]("one", "test.bin", b"x"), 429)
    checks.append("session and per-session file counts are bounded")
    for sess in ns["_sessions"].values():
        sess["updated_at"] = time.time() - 100
    ns["_prune_sessions"]()
    assert len(ns["_sessions"]) == 2
    ns["_sessions"]["one"]["scanning"] = 0
    ns["_prune_sessions"]()
    assert list(ns["_sessions"]) == ["two"] and len(ns["_files"]) == 1
    checks.append("retention expires completed records but preserves active work")
    reset()
    class Upload:
        filename = "test.bin"
        def __init__(self): self.stream = BytesIO(b"x" * 20); self.closed = False
        async def read(self, size): return self.stream.read(size)
        async def close(self): self.closed = True
    upload = Upload()
    await rejected(ns["_read_and_enqueue"]("fixture", upload), 413)
    assert upload.closed and upload.stream.tell() == 9 and not ns["_files"]
    checks.append("upload reading stops at limit plus one and closes the stream")
    upload = Upload(); ns["_upload_slots"] = asyncio.Semaphore(0)
    await rejected(ns["_read_and_enqueue"]("fixture", upload), 429)
    assert upload.closed and upload.stream.tell() == 0
    checks.append("concurrent-upload saturation rejects before reading bytes")
    reset()
    first = await ns["_enqueue"]("fixture", "test.bin", b"clean")
    def broken_scanner(data): raise RuntimeError("isolated scanner exception")
    ns["_clam_scan_bytes"] = broken_scanner
    with tempfile.TemporaryDirectory() as directory:
        ns["QUARANTINE"] = Path(directory)
        task = asyncio.create_task(ns["_worker"]("fixture"))
        await asyncio.wait_for(ns["_queue"].join(), 5)
        assert ns["_files"][first["file_id"]]["status"] == "ERROR"
        assert ns["_sessions"]["fixture"]["status"] == "BLOCKED" and ns["_pending_bytes"] == 0
        assert "data" not in task.get_stack()[0].f_locals
        ns["_clam_scan_bytes"] = lambda data: (ns["FileStatus"].CLEAN, None)
        await ns["_enqueue"]("later", "test.bin", b"clean")
        await asyncio.wait_for(ns["_queue"].join(), 5)
        assert ns["_sessions"]["later"]["status"] == "READY_FOR_PROCESSING"
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    checks.append("scanner failure blocks, releases capacity and preserves the worker")
    for index, name in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: PASS", flush=True)


if __name__ == "__main__":
    asyncio.run(cases())
