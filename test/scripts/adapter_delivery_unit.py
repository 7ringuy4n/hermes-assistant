"""Execute real adapter document/image methods against isolated protocol fakes."""
import ast
import asyncio
import logging
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes/main/plugins/zalo"))
from artifact_delivery_unit import backend


def main():
    ns = backend(False)
    def post(route, body):
        name = "file_transition" if route.endswith("transition") else "file_claim"
        return ns[name](SimpleNamespace(**body))
    tree = ast.parse((ROOT / "hermes/main/plugins/zalo/adapter.py").read_text(encoding="utf-8"))
    wanted = {"_as_autosend_file_fp", "_as_autosend_file_claim", "_as_autosend_already_sent",
              "_as_autosend_file_unclaim", "_as_delivery_begin", "_as_delivery_ack", "_as_delivery_reject",
              "_as_bridge_message_id", "send_document", "send_image_file"}
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ZaloAdapter")
    nodes = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted]
    assert len(nodes) == len(wanted)
    namespace = {"__name__": "adapter_regressions", "Path": Path,
                 "logger": logging.getLogger("adapter-regression"), "SendResult": SimpleNamespace}
    module = ast.fix_missing_locations(ast.Module(body=[ast.ClassDef(name="Methods", bases=[], keywords=[], body=nodes, decorator_list=[])], type_ignores=[]))
    exec(compile(module, "adapter-regressions", "exec"), namespace)
    Methods = namespace["Methods"]
    class Adapter(Methods):
        def __init__(self):
            self.calls = []
            self.next_response = {"ok": True, "result": {"msgId": "fixture-ack"}}
            self.scan = "clean"
        def _as_autosend_turn_dest(self, thread):
            return {"thread_id": thread, "thread_type": "user", "source_message_id": "original-" + thread}
        def _as_zalo_api_chat_id(self, thread): return thread
        def _as_session_http(self, method, route, body): return post(route, body)
        def _thread_type_from_chat_id(self, chat, meta): return "user"
        def _as_attach_caption(self, text): return text or ""
        def _bridge_attachment_payload(self, dest, kind, path, caption):
            return {"path": str(path), "fileName": Path(path).name, "threadId": dest}
        def _sanitize_send_quote(self, quote): return quote
        async def _as_outbound_scan(self, *args): return self.scan
        async def _as_with_dest_send_lock(self, dest, call): return await call()
        async def _post(self, route, payload):
            self.calls.append((route, payload))
            return self.next_response
        def _as_bridge_ok(self, response): return bool(self._as_bridge_message_id(response))
        def _as_record_attachment_delivery(self, **kwargs): pass
        def _as_compound_mark_delivered(self, thread): pass
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "source.pdf"
        path.write_bytes(b"fixture-one")
        async def cases():
            adapter = Adapter()
            adapter.scan = "blocked"
            denied = await adapter.send_document("scan-fixture", path)
            adapter.scan = "clean"
            retry = await adapter.send_document("scan-fixture", path)
            checks.append(("blocked scan does not cache a successful file send", not denied.success and retry.success and len(adapter.calls) == 1))
            adapter = Adapter()
            adapter.next_response = {"success": False, "error": "fixture rejection", "definite_rejection": True}
            failed = await adapter.send_document("known-rejection", path)
            adapter.next_response = {"ok": True, "result": {"msgId": "retry-ack"}}
            retried = await adapter.send_document("known-rejection", path)
            checks.append(("definite bridge failure releases the shared claim", not failed.success and retried.success and len(adapter.calls) == 2))
            adapter = Adapter()
            adapter.next_response = {"error": "fixture ambiguous timeout"}
            failed = await adapter.send_document("unknown-rejection", path)
            retry = await adapter.send_document("unknown-rejection", path)
            checks.append(("unknown wire result is not success or a blind resend", not failed.success and not retry.success and len(adapter.calls) == 1))
            adapter = Adapter()
            delivered = await adapter.send_document("duplicate-fixture", path)
            repeated = await adapter.send_document("duplicate-fixture", path)
            checks.append(("ACK-backed repeat suppresses only a proven duplicate", delivered.success and repeated.success and len(adapter.calls) == 1))
            adapter = Adapter()
            first = await adapter.send_document("first-conversation", path)
            other = Path(directory) / "other/source.pdf"
            other.parent.mkdir()
            other.write_bytes(b"fixture-two")
            second = await adapter.send_document("second-conversation", other)
            checks.append(("same name and byte count do not cross conversations", first.success and second.success and len(adapter.calls) == 2))
            adapter = Adapter()
            forged = await adapter.send_document("unowned-claim", path, metadata={"as_claimed": True})
            checks.append(("metadata cannot manufacture claim ownership", not forged.success and not adapter.calls))
        asyncio.run(cases())
    for index, (name, passed) in enumerate(checks, 1):
        print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
