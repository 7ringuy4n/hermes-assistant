"""Delivery protocol regressions; --live-session executes actual Valkey Lua.

The live mode runs inside Session, creates an opaque isolated key family, and
removes exactly those fixture keys. No bridge call or real recipient is used.
"""
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "architect/lib"))
from artifact_delivery import DeliveryClaim, artifact_key, bridge_message_id


class MemoryRedis:
    def __init__(self):
        import threading
        self.lock = threading.Lock()
        self.values = {}
        self.receipts = {}

    def set(self, key, value, **kwargs):
        with self.lock:
            if kwargs.get("nx") and key in self.values:
                return False
            self.values[key] = value
            return True

    def get(self, key):
        return self.values.get(key)

    def hlen(self, key):
        return len(self.receipts.get(key, {}))

    def eval(self, script, numkeys, key, receipt, token, state, message_id, ttl, thread_id, thread_type, source_message_id):
        with self.lock:
            record = json.loads(self.values.get(key) or "{}")
            if record.get("token") != token or record.get("state") == "acknowledged":
                return 0
            if [record.get(field) for field in ("thread_id", "thread_type", "source_message_id")] != [thread_id, thread_type, source_message_id]:
                return 0
            if state == "sending" and record.get("state") != "reserved":
                return 0
            if state == "acknowledged" and record.get("state") != "sending":
                return 0
            if state == "release":
                self.values.pop(key, None)
            else:
                record.update(state=state, message_id=message_id)
                self.values[key] = json.dumps(record)
                if state == "acknowledged":
                    self.receipts.setdefault(receipt, {})[key] = message_id
            return 1


class HttpError(Exception):
    def __init__(self, status, detail):
        self.status_code = status
        self.detail = detail


def backend(live):
    if live:
        sys.path.insert(0, "/app")
        import app
        app.SENTFILE_PREFIX = "lab-delivery-" + uuid.uuid4().hex
        return vars(app)
    namespace = {"Any": object, "FileClaim": SimpleNamespace, "FileTransition": SimpleNamespace,
                 "HTTPException": HttpError, "r": MemoryRedis(), "hashlib": hashlib, "json": json,
                 "SENTFILE_PREFIX": "lab-delivery", "SENTFILE_TTL": 600, "TTL": 86400}
    tree = ast.parse((ROOT / "architect/memory/session/app.py").read_text(encoding="utf-8"))
    wanted = {"file_claim", "file_transition", "file_receipts", "_file_receipt_key"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    assert len(nodes) == len(wanted)
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "session-regressions", "exec"), namespace)
    return namespace


def main():
    live = "--live-session" in sys.argv
    ns = backend(live)
    keys = set()
    checks = []
    def post(route, body):
        keys.add(f"{ns['SENTFILE_PREFIX']}:v2:{body['key']}")
        keys.add(ns["_file_receipt_key"](body["thread_id"], body["thread_type"], body["source_message_id"]))
        name = "file_transition" if route.endswith("transition") else "file_claim"
        model = ns["FileTransition" if name == "file_transition" else "FileClaim"]
        return ns[name](model(**body))
    def rejected(call, status):
        try:
            call()
        except Exception as exc:
            return getattr(exc, "status_code", None) == status
        return False
    try:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "page-001.txt"
            second = Path(directory) / "second/page-001.txt"
            second.parent.mkdir()
            first.write_text("alpha!")
            second.write_text("bravo!")
            def claim(source="original-request", dest="fixture-A", kind="user", path=first):
                return DeliveryClaim(post, path, dest, kind, source)
            checks.append(("same filename and size retains different bytes", artifact_key(first, "A", "user", "s") != artifact_key(second, "A", "user", "s")))
            checks.append(("same bytes in distinct requests remain distinct", claim().body["key"] != claim(source="later-request").body["key"]))
            checks.append(("DM and group namespace remain distinct", claim().body["key"] != claim(kind="group").body["key"]))
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: claim(source="concurrent-request").claim(), range(8)))
            checks.append(("concurrent replicas reserve exactly once", sum(bool(row["first"]) for row in results) == 1))
            original = claim()
            assert original.claim()["first"]
            pending = claim().claim()
            checks.append(("reservation replay is not successful delivery", not pending["first"] and pending["state"] == "reserved" and not pending["message_id"]))
            stale = claim()
            checks.append(("stale token cannot release another owner's claim", rejected(lambda: stale.transition("release"), 409)))
            original.transition("release")
            retry = claim()
            checks.append(("known pre-send failure can be retried", retry.claim()["first"]))
            retry.transition("sending")
            pending = claim().claim()
            checks.append(("ambiguous wire result remains pending without a fake ACK", not pending["first"] and pending["state"] == "sending" and not pending["message_id"] and (not live or ns["r"].ttl(f"{ns['SENTFILE_PREFIX']}:v2:{retry.body['key']}") == -1)))
            checks.append(("ACK requires an actual message identifier", rejected(lambda: retry.transition("acknowledged"), 400)))
            retry.transition("acknowledged", "fixture-acknowledgement")
            replay = claim().claim()
            receipts = ns["file_receipts"]("fixture-A", "user", "original-request")
            unrelated = ns["file_receipts"]("fixture-A", "user", "later-request")
            checks.append(("ACK replay and receipts are source-correlated", replay["state"] == "acknowledged" and replay["message_id"] == "fixture-acknowledgement" and receipts["acknowledged_count"] == 1 and unrelated["acknowledged_count"] == 0))
            checks.append(("HTTP success flags do not substitute for attachment ID", not bridge_message_id({"ok": True}) and not bridge_message_id({"success": False, "result": {"msgId": "rejected"}}) and bridge_message_id({"ok": True, "result": {"attachment": {"msgId": "accepted"}}}) == "accepted"))
        for index, (name, passed) in enumerate(checks, 1):
            print(f"running test case {index}/{len(checks)} {name}: {'PASS' if passed else 'FAIL'}")
        return 0 if all(passed for _, passed in checks) else 1
    finally:
        if live and keys:
            assert all(key.startswith(ns["SENTFILE_PREFIX"] + ":") for key in keys)
            ns["r"].delete(*sorted(keys))
            print("Exact live fixture keys removed")


if __name__ == "__main__":
    raise SystemExit(main())
