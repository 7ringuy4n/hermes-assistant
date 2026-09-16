#!/usr/bin/env python3
"""Unit: security alerts remain concise and hide internal scanner envelopes."""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "architect" / "security" / "security-manager" / "app.py"
tree = ast.parse(path.read_text(encoding="utf-8"))
node = next(
    item for item in tree.body
    if isinstance(item, ast.FunctionDef) and item.name == "_risk_notice"
)
namespace = {"os": os, "re": re, "Any": Any}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)

notice = namespace["_risk_notice"](
    "eicar.com",
    {
        "archive": {"ok": True},
        "yara": {"ok": False, "reason": "yara_hit", "hits": ["eicar"]},
        "llm_judge": {"ok": True, "skipped": True, "reason": "llm_judge_disabled"},
    },
)
assert "File: eicar.com" in notice
assert "malware signature (EICAR)" in notice
assert "quarantined" in notice
assert "{" not in notice and "yara_hit" not in notice and "llm_judge" not in notice
print("OK security_alert_format_unit")

# The live scanner oracle must not turn missing services or zero infection
# counters into a release PASS just because their keys appear in JSON.
import json
lab_path = ROOT / "test/scripts/file_pipeline_security_lab.py"
lab_tree = ast.parse(lab_path.read_text(encoding="utf-8"))
parser = next(item for item in lab_tree.body if isinstance(item, ast.FunctionDef) and item.name == "matrix_checks")
oracle = {"json": json}
exec(compile(ast.Module(body=[parser], type_ignores=[]), str(lab_path), "exec"), oracle)
scan = lambda verdict, ok: json.dumps({"verdict": verdict, "layers": {"antivirus": {"ok": ok}}})
fixture = "\n".join([
    "PROBE sm-clean code=200 body=" + scan("CLEAN", True),
    "PROBE sm-eicar code=200 body=" + scan("RISK", False),
    'PROBE av-eicar code=200 body={"ok":true}',
    'AV_READY i=1 body={"ready":false,"blocked":true,"status":"BLOCKED","infected":1,"scanning":0}',
    "VISION_ROUTE_HEALTH=up",
])
print("running test case 1/4 security matrix requires actual complete verdicts")
assert all(oracle["matrix_checks"](fixture).values())
print("running test case 2/4 zero infection does not prove EICAR detection")
assert not oracle["matrix_checks"](fixture.replace('"infected":1', '"infected":0'))["av_eicar_verdict"]
print("running test case 3/4 absent services and malformed responses fail closed")
assert not any(oracle["matrix_checks"]("PROBE sm-clean code=SKIP body=unavailable").values())
print("running test case 4/4 inactive antivirus cannot be accepted as active")
inactive = fixture.replace('"antivirus": {"ok": true}', '"antivirus": {"ok": true, "skipped": true}')
assert not oracle["matrix_checks"](inactive)["security_clean_active_av"]
print("OK security_matrix_oracle")

from types import SimpleNamespace
from unittest.mock import Mock
av_node = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == "_clam_via_gateway")
ticks = {"now": 0.0}
clock = SimpleNamespace(monotonic=lambda: ticks["now"], sleep=lambda seconds: ticks.update(now=ticks["now"] + seconds))
pending = {"ready": False, "blocked": False, "status": "SCANNING", "clean": 0, "infected": 0, "scanning": 1}
clean = {"ready": True, "blocked": False, "status": "READY_FOR_PROCESSING", "clean": 1, "infected": 0, "scanning": 0}
infected = {"ready": False, "blocked": True, "status": "BLOCKED", "clean": 0, "infected": 1, "scanning": 0}
def response(data=None, status=200):
    return SimpleNamespace(status_code=status, json=lambda: data or {})
def client_for(verdicts):
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.post.return_value = response({"ok": True, "file_id": "fixture"})
    states = iter(verdicts)
    client.get.side_effect = lambda url, **kwargs: response() if url.endswith("/health") else response(next(states))
    return client
av_ns = {"Any": Any, "ENABLE_AV": True, "AV_URL": "http://fake-av", "time": clock,
         "_unavailable": lambda reason: {"ok": True, "reason": reason}}
exec(compile(ast.Module(body=[av_node], type_ignores=[]), str(path), "exec"), av_ns)
print("running test case 1/4 active antivirus waits through SCANNING for CLEAN")
client = client_for([pending, clean])
av_ns["httpx"] = SimpleNamespace(Client=lambda **kwargs: client)
result = av_ns["_clam_via_gateway"](b"clean", "fixture.txt", "fixture-session")
assert result["ok"] is True and result.get("detail", {}).get("ready") is True
print("running test case 2/4 pending EICAR cannot receive an early clean verdict")
client = client_for([pending, infected])
av_ns["httpx"] = SimpleNamespace(Client=lambda **kwargs: client)
assert av_ns["_clam_via_gateway"](b"fixture", "fixture.bin", "fixture-session")["ok"] is False
print("running test case 3/4 enabled scanner outage cannot use isolation fail-open")
client = client_for([]); client.get.side_effect = ConnectionError("fixture outage")
av_ns["httpx"] = SimpleNamespace(Client=lambda **kwargs: client)
assert av_ns["_clam_via_gateway"](b"fixture", "fixture.bin", "fixture-session")["ok"] is False
print("running test case 4/4 nonterminal scan exhausts bounded wait without allowing")
client = client_for([])
client.get.side_effect = lambda url, **kwargs: response() if url.endswith("/health") else response(pending)
av_ns["httpx"] = SimpleNamespace(Client=lambda **kwargs: client)
ticks["now"] = 0.0
assert av_ns["_clam_via_gateway"](b"fixture", "fixture.bin", "fixture-session")["ok"] is False
assert ticks["now"] <= 121
print("OK security_terminal_av")
