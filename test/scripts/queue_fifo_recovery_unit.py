#!/usr/bin/env python3
"""Unit: inbound FIFO ordering, cap, and worker-failure recovery.

Exercises the real `hermes/main/plugins/zalo/inbound_queue.py` FIFO contract:
per-conversation FIFO order, bounded capacity (push refuses instead of dropping),
claim/ack, and recovery of in-flight items after a worker failure with no loss
and no duplication (INV-CONV-001, INV-QUEUE-001, INV-QUEUE-002).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "hermes" / "main" / "plugins" / "zalo" / "inbound_queue.py"


def _load():
    spec = importlib.util.spec_from_file_location("inbound_queue_unit_mod", MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    m = _load()

    # encode/decode round-trip and malformed input
    item = m.make_item(
        kind="inbound", text="hi", thread_id="t1", thread_type="user",
        sender_id="u1", sender_name="U", chat_type="dm", message_id="m1",
    )
    assert m.decode_item(m.encode_item(item))["thread_id"] == "t1"
    assert m.decode_item(None) is None
    assert m.decode_item("not-json") is None
    assert m.decode_item(b'{"a": 1}') == {"a": 1}
    assert item["user_text"] == "hi"
    assert item["message_type"] == "TEXT"
    assert item["media_urls"] == [] and item["schedule_fire"] is False

    # FIFO order within one conversation
    fifo = m.MemoryFifo(max_n=10)
    for x in ("A", "B", "C"):
        fifo.queue_push("conv", x, 10, 60)
    assert [fifo.queue_pop("conv") for _ in range(3)] == ["A", "B", "C"]
    assert fifo.queue_pop("conv") is None

    # Bounded capacity: push refuses (returns -1) instead of silently dropping
    cap = m.MemoryFifo(max_n=2)
    assert cap.queue_push("c", "A", 2, 60) == 1
    assert cap.queue_push("c", "B", 2, 60) == 2
    assert cap.queue_push("c", "C", 2, 60) == -1
    assert [cap.queue_pop("c"), cap.queue_pop("c")] == ["A", "B"]

    # push_front gives a deferred/priority item the next slot
    front = m.MemoryFifo()
    front.queue_push("c", "B", 16, 60)
    front.queue_push_front("c", "A", 60)
    assert [front.queue_pop("c"), front.queue_pop("c")] == ["A", "B"]

    # claim moves to in-flight; ack clears it; remaining queue stays active
    claim = m.MemoryFifo()
    claim.queue_push("c", "A", 16, 60)
    claim.queue_push("c", "B", 16, 60)
    got = claim.queue_claim("c")
    assert got == "A"
    assert claim.queue_len("c") == 1
    claim.queue_ack("c", got)
    assert claim.queue_active_ids() == ["c"]

    # Worker failure: in-flight returns to the front, order preserved, no loss/dup
    rec = m.MemoryFifo()
    for x in ("A", "B", "C"):
        rec.queue_push("c", x, 16, 60)
    assert (rec.queue_claim("c"), rec.queue_claim("c")) == ("A", "B")
    assert rec.queue_active_ids() == ["c"]
    assert rec.queue_recover("c") == 2
    assert rec.queue_len("c") == 3
    assert [rec.queue_pop("c") for _ in range(3)] == ["A", "B", "C"]
    assert rec.queue_recover("c") == 0  # empty in-flight is a no-op

    # env parsing (standard stack switch semantics)
    saved = {k: os.environ.get(k) for k in ("ZALO_INBOUND_QUEUE", "ZALO_INBOUND_QUEUE_MAX", "ZALO_INBOUND_QUEUE_TTL_S")}
    try:
        os.environ["ZALO_INBOUND_QUEUE"] = "inactive"
        assert m.queue_flag_on() is False
        os.environ["ZALO_INBOUND_QUEUE"] = "active"
        assert m.queue_flag_on() is True
        os.environ["ZALO_INBOUND_QUEUE_MAX"] = "999"
        assert m.queue_max() == 100
        os.environ["ZALO_INBOUND_QUEUE_MAX"] = "0"
        assert m.queue_max() == 1
        os.environ["ZALO_INBOUND_QUEUE_TTL_S"] = "1"
        assert m.queue_ttl_s() == 60
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print("queue_fifo_recovery_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
