"""Production delivery invariants using real function AST and isolated fakes.

No service connections, real recipients, or production filesystem writes.
The tiny transport/Redis fakes expose ordering and identity bugs; they do not
replace concurrent live delivery tests. Exit nonzero while an invariant fails.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import Mock, patch
import sys
import time
import os
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'architect/models/dispatcher'))
sys.path.insert(0, str(ROOT / 'architect/lib'))
import office_file
from artifact_delivery import DeliveryClaim, bridge_message_id


class HttpError(Exception):
    def __init__(self, status, detail):
        self.status_code = status
        self.detail = detail


def functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(selected) == len(names)
    for node in selected:
        node.decorator_list = []
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)


def main():
    failures = []
    with tempfile.TemporaryDirectory() as temp:
        media = Path(temp) / 'media'
        (media / 'out').mkdir(parents=True)
        source = media / 'out/source.txt'
        source.write_text('source')
        claims = {}
        class Redis:
            def set(self, key, value, **kwargs):
                if key in claims:
                    return False
                claims[key] = value
                return True
            def get(self, key):
                return claims.get(key)
            def eval(self, script, numkeys, key, receipt, token, state, message_id, ttl, *identity):
                record = json.loads(claims.get(key) or '{}')
                if record.get('token') != token or record.get('state') == 'acknowledged':
                    return 0
                if state == 'release':
                    claims.pop(key, None)
                else:
                    record.update(state=state, message_id=message_id)
                    claims[key] = json.dumps(record)
                return 1
        sn = {'Any': object, 'r': Redis(), 'SENTFILE_PREFIX': 'test-files',
              'SENTFILE_TTL': 600, 'TTL': 86400, 'FileClaim': SimpleNamespace,
              'FileTransition': SimpleNamespace, 'HTTPException': HttpError, 'json': json, 'hashlib': hashlib}
        functions(ROOT / 'architect/memory/session/app.py', {'file_claim', 'file_transition', '_file_receipt_key'}, sn)
        class Client:
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def post(self, url, json):
                result = sn['file_transition' if url.endswith('/transition') else 'file_claim'](SimpleNamespace(**json))
                return SimpleNamespace(status_code=200, json=lambda: result)
        bridge = Mock(return_value={'ok': True, 'message_id': 'fixture-ack'})
        ns = {'Path': Path, 'Any': object, 'SendFileReq': SimpleNamespace,
              'HTTPException': HttpError, 'MEDIA_DIR': media, 'time': time,
              'DeliveryClaim': DeliveryClaim, '_bridge_message_id': bridge_message_id,
              '_SEND_FILE_AV': set(), '_SEND_FILE_OK': {'.txt'},
              '_active_turn': Mock(return_value={}), '_active_source': Mock(return_value='source-A'),
              '_outbound_av_scan': Mock(return_value='clean'), '_send_zalo_base64': bridge,
              '_record_zalo_attachment_delivery': Mock(return_value=True), '_timing_add': Mock(),
              'httpx': SimpleNamespace(Client=Client), 'SESSION_URL': 'http://fake-session', 'os': os}
        functions(ROOT / 'architect/models/dispatcher/app.py', {'send_file', '_claim_generated_file', '_send_zalo_attachment'}, ns)
        def req(**updates):
            return SimpleNamespace(**{'path': str(source), 'thread_id': 'conversation-A',
                'thread_type': 'user', 'caption': '', 'filename': None, 'lock_thread': True, **updates})
        def outcome(index, name, good):
            print(f'running test case {index}/10 {name}: ' + ('PASS' if good else 'FAIL'))
            if not good:
                failures.append(name)
        with patch.object(office_file, '_MEDIA_ROOTS', (media,)):
            canary = Path(temp) / 'outside.txt'
            rejected = False
            try:
                ns['send_file'](req(filename=str(canary)))
            except HttpError as exc:
                rejected = exc.status_code == 400
            outcome(1, 'delivery filename cannot write outside approved media', rejected and not canary.exists())
            claims.clear(); bridge.reset_mock()
            ns['_active_turn'].return_value = {'thread_id': 'conversation-B', 'thread_type': 'group'}
            ns['send_file'](req(lock_thread=False))
            outcome(2, 'explicit recipient cannot be redirected by concurrent global turn',
                    bridge.call_args.args[0] == 'conversation-A')
            claims.clear(); bridge.reset_mock(); ns['_active_turn'].return_value = {}
            other = media / 'out/other/source.txt'
            other.parent.mkdir(); other.write_text('other!')  # same size, different contents
            assert other.stat().st_size == source.stat().st_size
            ns['send_file'](req())
            ns['send_file'](req(path=str(other), thread_id='conversation-B'))
            outcome(3, 'equal filename and size cannot suppress another conversation result', bridge.call_count == 2)
            claims.clear(); bridge.reset_mock()
            ns['_outbound_av_scan'].return_value = 'blocked'
            try:
                ns['send_file'](req())
            except HttpError as exc:
                assert exc.status_code == 403
            ns['_outbound_av_scan'].return_value = 'clean'
            retried = ns['send_file'](req())
            outcome(4, 'failed scan does not become acknowledged successful delivery on retry',
                    bridge.call_count == 1 and not retried.get('skipped'))
            client = Mock()
            client.__enter__ = Mock(return_value=client)
            client.__exit__ = Mock(return_value=False)
            client.post.return_value = SimpleNamespace(status_code=200,
                json=lambda: {'success': False, 'error': 'fixture send rejected'})
            ns['httpx'] = SimpleNamespace(Client=Mock(return_value=client))
            rejected = False
            try:
                ns['_send_zalo_attachment']('conversation-A', 'user', source, '')
            except HttpError as exc:
                rejected = exc.status_code == 502
            outcome(5, 'HTTP 200 bridge rejection is not a delivery acknowledgement', rejected)
            ns['httpx'] = SimpleNamespace(Client=Client)
            claims.clear(); bridge.reset_mock()
            bridge.side_effect = [HttpError(502, {'definite_rejection': True}), {'ok': True, 'message_id': 'retry-ack'}]
            try:
                ns['send_file'](req())
            except HttpError as exc:
                assert exc.status_code == 502
            retried = ns['send_file'](req())
            outcome(6, 'definite bridge rejection releases owner claim for a real retry', retried['ok'] and bridge.call_count == 2)
            claims.clear(); bridge.reset_mock()
            bridge.side_effect = TimeoutError('fixture ambiguous wire timeout')
            try:
                ns['send_file'](req())
            except TimeoutError:
                pass
            pending = False
            try:
                ns['send_file'](req())
            except HttpError as exc:
                pending = exc.status_code == 409
            outcome(7, 'ambiguous wire timeout cannot blindly resend or claim delivery', pending and bridge.call_count == 1)
            claims.clear(); bridge.reset_mock(); bridge.side_effect = None
            bridge.return_value = {'ok': True, 'message_id': 'accepted-ack'}
            ns['send_file'](req())
            replay = ns['send_file'](req())
            outcome(8, 'acknowledged replay returns the receipt without a second bridge send', replay.get('message_id') == 'accepted-ack' and bridge.call_count == 1)
            claims.clear(); bridge.reset_mock()
            ns['_record_zalo_attachment_delivery'].reset_mock()
            ns['_active_source'].return_value = 'original-request'
            def late_turn(*args):
                ns['_active_source'].return_value = 'later-request'
                return {'ok': True, 'message_id': 'source-ack'}
            bridge.side_effect = late_turn
            ns['send_file'](req())
            outcome(9, 'late attachment ACK retains the source captured before wire send',
                    ns['_record_zalo_attachment_delivery'].call_args.kwargs['source_message_id'] == 'original-request')
            claims.clear(); bridge.reset_mock(); bridge.side_effect = None
            ns['_active_source'].return_value = ''
            rejected = False
            try:
                ns['send_file'](req(thread_type='group'))
            except HttpError as exc:
                rejected = exc.status_code == 503
            outcome(10, 'missing conversation source fails before claiming or sending',
                    rejected and bridge.call_count == 0 and not claims)
    print('Unresolved production delivery invariants: ' + str(len(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
