"""Late gateway completion cannot borrow the next conversation turn's receipts."""
import ast
import asyncio
import logging
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Dict, Optional
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes/main/plugins/zalo"))


def main():
    tree = ast.parse((ROOT / "hermes/main/plugins/zalo/adapter.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ZaloAdapter")
    names = {"_as_autosend_turn_dest", "_as_job_already_sent_file", "_as_autosend_turn_files", "send"}
    nodes = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    ns = {"__name__": "late_delivery_regressions", "Optional": Optional, "Dict": Dict, "Any": Any, "SendResult": SimpleNamespace,
          "logger": logging.getLogger("late-document-regression"), "_replica_count": lambda: 1}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name="Methods", bases=[], keywords=[], body=nodes, decorator_list=[])], type_ignores=[])), "actual-adapter", "exec"), ns)
    class Adapter(ns["Methods"]):
        def __init__(self):
            self._as_document_jobs = {}  # Workflow's finally block already ran.
            self._as_turns = {"fixture::job::old": {"thread_id": "fixture::job::old", "thread_type": "user", "source_message_id": "old-source"},
                              "fixture": {"thread_id": "fixture", "thread_type": "user", "source_message_id": "new-source"}}
            self._as_job_file_sent = {}; self.acks = {"old-source": 1, "new-source": 1}; self.calls = []; self.captured = None
        def _as_session_http(self, method, path):
            self.calls.append(path)
            source = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query).get("source_message_id", [""])[0]
            return {"ok": True, "acknowledged_count": self.acks.get(source, 0)}
        def _as_compound_mark_delivered(self, *args): pass
        def _as_turn_token(self, *args): return 2
        def _as_env_float(self, name, default, *args): return default
        def _as_autosend_ok_ext(self): return (".pdf",)
        def _as_autosend_roots(self): raise AssertionError("typed document job scanned another job's public artifacts")
        def _as_autosend_wrong_thread(self, *args): return False
        async def _as_autosend_turn_files(self, chat, content, metadata):
            await asyncio.sleep(0)
            self._as_turns["fixture"]["source_message_id"] = "third-source"
            self.captured = dict(metadata)
            return content
        def _as_kick_late_autosend(self, *args): pass
        def _rewrite_gateway_user_notice(self, *args): return None
        def _as_is_media_ack_only(self, *args): return False
        async def _as_persist_deferred_notes(self, chat, content, meta): return content
    a = Adapter()
    print("running test case 1/11 ACK-backed mute survives workflow cleanup", flush=True)
    assert a._as_job_already_sent_file("fixture::job::old")
    assert "source_message_id=old-source" in a.calls[-1] and "/receipts/fixture?" in a.calls[-1]
    print("running test case 2/11 newer ACK cannot mute an unacknowledged older job", flush=True)
    a.acks["old-source"] = 0
    assert not a._as_job_already_sent_file("fixture::job::old")
    print("running test case 3/11 missing isolated binding never falls back to global turn", flush=True)
    before = len(a.calls)
    assert a._as_autosend_turn_dest("fixture::job::unknown") == {}
    assert not a._as_job_already_sent_file("fixture::job::unknown") and len(a.calls) == before
    print("running test case 4/11 late final text captures original source before async work", flush=True)
    a.acks["old-source"] = 1
    result = asyncio.run(a.send("fixture::job::old", "Previous document was sent."))
    assert result.success and result.message_id is None
    assert a.captured["source_message_id"] == "old-source"
    print("running test case 5/11 unknown isolated send fails before side effects", flush=True)
    a.captured = None
    result = asyncio.run(a.send("fixture::job::unknown", "Should not be sent."))
    assert not result.success and a.captured is None
    a._as_turns["fixture::job::old"]["artifact_only"] = True
    for number, count in ((6, 0), (7, 1)):
        print(f"running test case {number}/11 private review is silent with {count} original ACK", flush=True)
        a.acks["old-source"] = count
        a.captured = None
        result = asyncio.run(a.send("fixture::job::old", "Private draft review passed. Deliver it."))
        assert result.success and result.message_id is None
        assert a.captured["source_message_id"] == "old-source"
    print("running test case 8/11 typed document jobs never scan shared public artifacts", flush=True)
    assert asyncio.run(ns["Methods"]._as_autosend_turn_files(a, "fixture::job::old", "Final review")) == "Final review"
    workflow = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_as_run_workflow_job")
    workflow_source = ast.unparse(workflow)
    assert "if not defer_sidecars and" in workflow_source
    assert "if defer_sidecars and idle and (not delivered):" in workflow_source
    assert "('artifacts', 'delivery_failed')" in workflow_source
    assert workflow_source.index("await self.cancel_session_processing") < workflow_source.index("await self._as_autosend_late_files")
    print("PASS late document completion binding")
    print("running test case 9/11 normal queued document uses its original ACK", flush=True)
    a.acks["third-source"] = 1
    assert a._as_job_already_sent_file("fixture")
    print("running test case 10/11 previous normal ACK cannot mute the next source", flush=True)
    a._as_turns["fixture"]["source_message_id"] = "next-source"
    assert not a._as_job_already_sent_file("fixture")
    print("running test case 11/11 missing normal turn cannot borrow global receipt", flush=True)
    before = len(a.calls)
    assert not a._as_job_already_sent_file("other-fixture") and len(a.calls) == before
    print("PASS normal queued document receipt isolation")


if __name__ == "__main__":
    main()
