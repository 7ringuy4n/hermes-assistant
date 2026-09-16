"""Activation wiring and fail-closed AV: actual source methods, no transport."""
import ast
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    tree = ast.parse((ROOT / "hermes/main/plugins/zalo/adapter.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ZaloAdapter")
    names = {"_as_av_required", "_as_av_gate", "_as_enqueue_file_pipeline"}
    nodes = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    ns = {}
    module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name="Methods", bases=[], keywords=[], body=nodes, decorator_list=[])], type_ignores=[]))
    exec(compile(module, "activation-regression", "exec"), ns)
    class Adapter(ns["Methods"]):
        def __init__(self): self.messages = []; self.parsed = False
        def _as_user_secret_ask_blob(self, *args): return ""
        def _as_flow(self, *args, **kwargs): pass
        def _as_file_pipeline_enabled(self): return False
        def _as_av_activated(self): return False
        async def send(self, **kwargs): self.messages.append(kwargs)
        async def _as_security_file_allow(self, **kwargs): raise AssertionError("required AV bypassed")
    checks = []
    for value in ("active", "1", "inactive"):
        with patch.dict(os.environ, {"AV_REQUIRED": value}):
            checks.append(("AV_REQUIRED recognizes " + value, Adapter()._as_av_required() == (value != "inactive")))
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"AV_REQUIRED": "active"}):
        path = Path(temp) / "fixture.txt"
        path.write_text("harmless fixture")
        adapter = Adapter()
        aborted = asyncio.run(adapter._as_av_gate("fixture", "fixture", str(path), {"kind": "file"}))
        checks.append(("required unavailable AV blocks even with learning pipeline off", aborted and len(adapter.messages) == 1))
    text = (ROOT / "run.sh").read_text(encoding="utf-8")
    checks.append(("active optional services are not removed by legacy numeric checks", all(f'if ! _env_active "${{{key}:-}}"; then' in text for key in ("ENABLE_ANTIVIRUS", "SECURITY_SANDBOX", "ENABLE_CLOUDDRIVE"))))
    compose = (ROOT / "docker/docker-compose.yml").read_text(encoding="utf-8")
    checks.append(("antivirus activates required scanning in both senders", compose.count("- AV_REQUIRED=${ENABLE_ANTIVIRUS:-inactive}") == 2 and compose.count("- AV_SCAN=${ENABLE_ANTIVIRUS:-inactive}") == 2))
    dt = ast.parse((ROOT / "architect/models/dispatcher/app.py").read_text(encoding="utf-8"))
    fn = next(n for n in dt.body if isinstance(n, ast.FunctionDef) and n.name == "_outbound_av_scan")
    dn = {"Path": Path, "os": os}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "outbound-av", "exec"), dn)
    with patch.dict(os.environ, {"AV_SCAN": "inactive", "AV_REQUIRED": "inactive"}):
        checks.append(("inactive outbound AV does not attempt unavailable service", dn["_outbound_av_scan"](Path("missing-fixture"), "fixture", "fixture") == "skip"))
    with patch.dict(os.environ, {"AV_SCAN": "active", "AV_REQUIRED": "active"}):
        checks.append(("active required outbound AV rejects unreadable input", dn["_outbound_av_scan"](Path("missing-fixture"), "fixture", "fixture") == "blocked"))
    for i, (name, ok) in enumerate(checks, 1):
        print(f"running test case {i}/{len(checks)} {name}: {'PASS' if ok else 'FAIL'}", flush=True)
    assert all(ok for _, ok in checks)


if __name__ == "__main__":
    main()
