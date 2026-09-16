"""Shared deterministic identity and acknowledgement-aware delivery coordination."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import uuid


def artifact_key(path, thread_id, thread_type, source_message_id):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    fields = [str(thread_type), str(thread_id), str(source_message_id), Path(path).name, digest.hexdigest()]
    return hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest()


def bridge_message_id(payload):
    pending = [payload]
    while pending:
        item = pending.pop(0)
        if isinstance(item, dict):
            if item.get("ok") is False or item.get("success") is False or item.get("error"):
                return ""
            for key in ("msgId", "message_id"):
                if item.get(key) is not None and str(item[key]).strip():
                    return str(item[key])
            pending.extend(item[key] for key in ("result", "message", "attachment") if key in item)
        elif isinstance(item, list):
            pending.extend(item)
    return ""


class DeliveryClaim:
    """Inject a Session HTTP transport; never turn an uncertain send into success."""

    def __init__(self, post, path, thread_id, thread_type, source_message_id):
        self.post = post
        self.body = {"key": artifact_key(path, thread_id, thread_type, source_message_id),
                     "thread_id": str(thread_id), "thread_type": str(thread_type),
                     "source_message_id": str(source_message_id), "token": uuid.uuid4().hex}
        self.sending = False

    def claim(self):
        result = self.post("/v1/files/claim", self.body)
        if not isinstance(result, dict) or not result.get("ok"):
            raise RuntimeError("delivery coordination unavailable")
        return result

    def transition(self, state, message_id=""):
        result = self.post("/v1/files/transition", {**self.body, "state": state, "message_id": message_id})
        if not isinstance(result, dict) or not result.get("ok"):
            raise RuntimeError("delivery claim transition failed")
        return result
