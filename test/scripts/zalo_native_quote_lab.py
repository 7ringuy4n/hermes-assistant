"""Read-only native quote identity from the CURRENT bridge listener's cache.

Incoming contexts remain injected; a real outbound ACK/cache is not proof of a
native-client input bubble. Never substitute msgId for a missing cliMsgId.
"""
from __future__ import annotations

import json
import pathlib
import pwd
import re
import subprocess
import time


def native_quote(message_id: str, content: str, own_id: str) -> dict:
    sockets = subprocess.check_output(['ss', '-ltnp', '( sport = :8787 )'], text=True)
    pids = set(re.findall(r'pid=(\d+)', sockets))
    if len(pids) != 1:
        raise RuntimeError('current_bridge_pid_ambiguous')
    proc = pathlib.Path('/proc') / next(iter(pids))
    env = dict(raw.split(b'=', 1) for raw in (proc / 'environ').read_bytes().split(b'\0') if b'=' in raw)
    cwd = (proc / 'cwd').resolve()

    def resolved(value):
        path = pathlib.Path(value.decode())
        return path if path.is_absolute() else cwd / path

    if env.get(b'ZALO_CLIMSG_DIR'):
        directory = resolved(env[b'ZALO_CLIMSG_DIR'])
    elif env.get(b'ZALO_DATA_DIR'):
        directory = resolved(env[b'ZALO_DATA_DIR']) / 'climsgids'
    else:
        directory = pathlib.Path(pwd.getpwuid(proc.stat().st_uid).pw_dir) / '.hermes-zalo/climsgids'
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        for epoch in (time.time(), time.time() - 86400):
            cache = directory / ('climsgids-' + time.strftime('%Y-%m-%d', time.gmtime(epoch)) + '.jsonl')
            if not cache.is_file():
                continue
            for raw in cache.read_text().splitlines():
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if str(record.get('m')) != message_id:
                    continue
                cli = str(record.get('c') or '')
                captured_at = int(record.get('t') or 0)
                if not cli or cli == message_id or captured_at <= 0:
                    raise RuntimeError('native_quote_identity_unproven')
                return dict(msgType='webchat', msgId=message_id, cliMsgId=cli,
                            content=content, ownerId=own_id, uidFrom=own_id,
                            ts=str(captured_at))
        time.sleep(.3)
    raise RuntimeError('native_quote_cache_missing')
