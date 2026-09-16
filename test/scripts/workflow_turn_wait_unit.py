# -*- coding: utf-8 -*-
"""Unit: wait for Hermes gateway session idle before the next workflow job."""
from __future__ import annotations

import asyncio
import ast
import io
import sys
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

from turn_wait import session_active_for_thread, wait_thread_idle  # noqa: E402

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

TID = "thread-test-1"


def test_session_match() -> None:
    from turn_wait import isolate_session_chat_id, is_isolated_session, real_thread_id

    active = {f"zalo:dm:{TID}": object()}
    if not session_active_for_thread(active, TID):
        raise SystemExit("FAIL match thread in session key")
    if session_active_for_thread(active, "other-thread"):
        raise SystemExit("FAIL other thread should be idle")
    user_id = "dm-user-99"
    collision = {f"agent:main:zalo:group:group-42:{user_id}": object()}
    if session_active_for_thread(collision, user_id, "user"):
        raise SystemExit("FAIL group sender suffix must not hold the matching DM queue")
    if not session_active_for_thread(collision, "group-42", "group"):
        raise SystemExit("FAIL group destination should match its own session")
    if session_active_for_thread({}, TID):
        raise SystemExit("FAIL empty map")
    if session_active_for_thread(None, TID):
        raise SystemExit("FAIL none map")
    iso = isolate_session_chat_id(TID, "job_ab")
    if not is_isolated_session(iso) or real_thread_id(iso) != TID:
        raise SystemExit(f"FAIL isolate {iso}")
    from turn_wait import same_dest_thread

    if not same_dest_thread(iso, TID) or not same_dest_thread(TID, iso):
        raise SystemExit("FAIL same_dest_thread isolated vs real")
    if same_dest_thread(iso, "other-thread"):
        raise SystemExit("FAIL same_dest_thread other")
    if same_dest_thread("", TID):
        raise SystemExit("FAIL same_dest_thread empty")
    iso_active = {f"zalo:dm:{iso}": object()}
    if not session_active_for_thread(iso_active, iso):
        raise SystemExit("FAIL isolated session match")
    other = isolate_session_chat_id(TID, "job_cd")
    if session_active_for_thread(iso_active, other):
        raise SystemExit("FAIL sibling job should not share session")
    print("PASS session_active_for_thread")


async def _idle_cases() -> None:
    box: dict = {}

    ok = await wait_thread_idle(lambda: box, TID, timeout_s=1.0, poll_s=0.05)
    if not ok:
        raise SystemExit("FAIL already idle")

    box[f"zalo:dm:{TID}"] = object()

    async def _clear() -> None:
        await asyncio.sleep(0.2)
        box.clear()

    task = asyncio.create_task(_clear())
    ok = await wait_thread_idle(lambda: box, TID, timeout_s=2.0, poll_s=0.05)
    await task
    if not ok:
        raise SystemExit("FAIL wait until clear")

    box[f"zalo:dm:{TID}"] = object()
    ok = await wait_thread_idle(lambda: box, TID, timeout_s=0.25, poll_s=0.05)
    if ok:
        raise SystemExit("FAIL timeout should be False while still active")
    box.clear()

    pulses = {"n": 0}

    def _pulse() -> None:
        pulses["n"] += 1

    box[f"zalo:dm:{TID}"] = object()

    async def _clear_slow() -> None:
        await asyncio.sleep(0.35)
        box.clear()

    task = asyncio.create_task(_clear_slow())
    ok = await wait_thread_idle(
        lambda: box,
        TID,
        timeout_s=2.0,
        poll_s=0.05,
        pulse=_pulse,
        pulse_every_s=0.1,
    )
    await task
    if not ok or pulses["n"] < 1:
        raise SystemExit(f"FAIL pulse n={pulses['n']} ok={ok}")

    # After handle_message: session never appears → idle after arm window.
    ok = await wait_thread_idle(
        lambda: {},
        TID,
        timeout_s=2.0,
        poll_s=0.05,
        arm_first=True,
        arm_s=0.15,
    )
    if not ok:
        raise SystemExit("FAIL arm_first never-started")

    box[f"zalo:dm:{TID}"] = object()

    async def _clear_armed() -> None:
        await asyncio.sleep(0.2)
        box.clear()

    task = asyncio.create_task(_clear_armed())
    ok = await wait_thread_idle(
        lambda: box,
        TID,
        timeout_s=2.0,
        poll_s=0.05,
        arm_first=True,
        arm_s=0.05,
    )
    await task
    if not ok:
        raise SystemExit("FAIL arm_first then idle")
    print("PASS wait_thread_idle")


async def _startup_buffer_case() -> None:
    event=SimpleNamespace(source=SimpleNamespace(chat_id=TID,chat_type='dm',platform=SimpleNamespace(value='zalo')))
    pending=[event]
    box={f'zalo:dm:{TID}':object()}
    replayed=False
    async def replay():
        nonlocal replayed
        await asyncio.sleep(.03)
        box.clear()  # initial callback only buffers during startup restore
        await asyncio.sleep(.2)
        pending.clear()
        box[f'zalo:dm:{TID}']=object()  # replay claims synchronously
        replayed=True
        await asyncio.sleep(.15)
        box.clear()
    task=asyncio.create_task(replay())
    result=await wait_thread_idle(lambda:box,TID,thread_type='user',
        pending_get=lambda:pending,timeout_s=1,poll_s=.05,arm_first=True,arm_s=.05)
    assert result and replayed and task.done(), 'buffered callback mistaken for terminal completion'
    await task
    assert not await wait_thread_idle(lambda:{},TID,thread_type='user',
        pending_get=lambda:[event],timeout_s=1,poll_s=.05,arm_first=True,arm_s=.05), 'unreplayed buffer must time out, not pass'
    foreign=SimpleNamespace(source=SimpleNamespace(chat_id=TID,chat_type='group',platform=SimpleNamespace(value='zalo')))
    assert await wait_thread_idle(lambda:{},TID,thread_type='user',
        pending_get=lambda:[foreign],timeout_s=1,poll_s=.05,arm_first=True,arm_s=.05)
    print('PASS startup buffered handoff is not terminal idle')


async def _actual_adapter_buffer_fence_case() -> None:
    # Compile the production adapter methods, not reimplemented test logic.
    tree=ast.parse((ROOT/'hermes/main/plugins/zalo/adapter.py').read_text(encoding='utf-8'))
    selected={'set_message_handler','_as_pending_gateway_events','_as_cancel_buffered_gateway_event'}
    methods=[node for cls in tree.body if isinstance(cls,ast.ClassDef) for node in cls.body
             if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in selected]
    assert len(methods)==3
    class StubBase:
        def set_message_handler(self,handler): self._message_handler=handler
    namespace={'StubBase':StubBase}
    definition=ast.ClassDef(name='AdapterProbe',bases=[ast.Name(id='StubBase',ctx=ast.Load())],
                            keywords=[],body=methods,decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[definition],type_ignores=[])),
                 '<actual-adapter-buffer-methods>','exec'),namespace)
    first=SimpleNamespace(); sibling=SimpleNamespace()
    class Gateway:
        def __init__(self): self._startup_restore_queue=[first,sibling]; self.calls=[]
        async def handle(self,event): self.calls.append(event); return 'final'
    gateway=Gateway(); adapter=namespace['AdapterProbe']()
    adapter.set_message_handler(gateway.handle)
    assert adapter._as_pending_gateway_events()==(first,sibling)
    adapter._as_cancel_buffered_gateway_event(first)
    assert gateway._startup_restore_queue==[sibling], 'cancelling one event removed its sibling'
    assert await adapter._message_handler(first) is None and not gateway.calls, 'cancelled replay still executed'
    assert await adapter._message_handler(sibling)=='final' and gateway.calls==[sibling]
    assert sibling._as_terminal_response=='final'
    print('PASS actual adapter fences owned buffered event and cancelled replay only')


def main() -> int:
    test_session_match()
    asyncio.run(_idle_cases())
    asyncio.run(_startup_buffer_case())
    asyncio.run(_actual_adapter_buffer_fence_case())
    print("PASS workflow turn wait")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
