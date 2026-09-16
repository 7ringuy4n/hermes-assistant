#!/usr/bin/env python3
"""Vietnamese note locale gate: real scoped storage, titled content and cleanup."""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from deploy_stack import connect,sudo_bash
from sanitize import sanitize
ROOT=Path(os.environ.get('ASSISTANT_REPO_ROOT',Path(__file__).resolve().parents[2]))


def main():
    uid=(os.environ.get('ZALO_TEST_USER_ID') or '').strip()
    if not uid:
        raise SystemExit('ZALO_TEST_USER_ID required')
    remote=r"""
set -euo pipefail
cd /opt/assistant
python3 - <<'PY'
import json,subprocess,sys,time,urllib.request,urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,'/opt/assistant/test/scripts')
from scoped_documents_smoke_lab import ensure_ready,delivered,thread_terminal
uid=__UID__; started=time.time(); marker='note-locale-'+str(time.time_ns())
text='note giúp tôi hôm nay cần bàn giao công việc. Nội dung ghi chú cần có mã '+marker+'.'
scope='zalo:user:'+uid
today=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date().isoformat()
ensure_ready()
names=subprocess.check_output(['docker','ps','--filter','label=com.docker.compose.service=zalo-api','--format','{{.Names}}'],text=True).splitlines()
assert len(names)==1, 'note audit service ambiguous'
probe=r'''
import json,os,psycopg
with psycopg.connect(os.environ['DATABASE_URL']) as conn:
 rows=conn.execute("SELECT id,title,content,note_date::text FROM notes WHERE active AND owner_id=%s AND scope_id=%s AND created_at>=to_timestamp(%s) AND content LIKE %s ORDER BY id",
   (os.environ['LAB_UID'],'zalo:user:'+os.environ['LAB_UID'],float(os.environ['LAB_START']),'%'+os.environ['LAB_MARKER']+'%')).fetchall()
print(json.dumps(rows,ensure_ascii=False))
'''
def owned_notes():
 raw=subprocess.check_output(['docker','exec','-e','LAB_UID='+uid,'-e','LAB_START='+str(started),
   '-e','LAB_MARKER='+marker,names[0],'python3','-c',probe],text=True)
 return json.loads(raw)
print('SOURCE_ID '+marker,flush=True)
print('running test case 1/3: Vietnamese source-bound native confirmation',flush=True)
event={'type':'message','threadId':uid,'threadType':'user','senderId':uid,'senderName':'test-user','text':text,'messageId':marker}
request=urllib.request.Request('http://127.0.0.1:8787/inject-event',method='POST',
 data=json.dumps(event,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
notes=[]; rows=[]
try:
 with urllib.request.urlopen(request,timeout=30) as response:
  assert json.load(response).get('ok') is True, 'injection failed'
 settled=None; deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  rows=delivered(marker)
  if len(rows)>1:
   raise AssertionError('duplicate note operation reply')
  if rows and thread_terminal(uid):
   settled=settled or time.monotonic()
   if time.monotonic()-settled>=6: break
  else: settled=None
  time.sleep(2)
 else: raise AssertionError('note confirmation not terminal')
 assert len(rows)==1 and str(rows[0].get('message_id') or '').isdigit(), 'native ACK absent'
 assert rows[0]['content']=='Đã lưu ghi chú.', 'incorrect Vietnamese note reply'
 assert not (rows[0].get('meta') or {}).get('file_name'), 'unexpected attachment'
 print('running test case 2/3: actual dated scoped note and generated title',flush=True)
 notes=owned_notes()
 assert len(notes)==1, 'confirmation did not persist exactly one owned scoped note'
 note_id,title,content,date=notes[0]
 assert title and len(title)<=100 and marker not in title, 'missing or nonconcise generated title'
 assert 'bàn giao' in (title+' '+content).casefold() and marker in content, 'requested note content missing'
 assert date==today, 'incorrect local note date'
 assert not any(term in content.casefold() for term in ('không thể tự lưu','hệ thống xử lý','nếu bạn muốn')), 'note polluted with process boilerplate'
 assert delivered(marker)==rows, 'late extra reply'
finally:
 print('running test case 3/3: exact owned note cleanup',flush=True)
 for note in owned_notes():
  path='http://127.0.0.1:8095/v1/notes/'+urllib.parse.quote(str(note[0]),safe='')+'?scope_id='+urllib.parse.quote(scope,safe='')
  with urllib.request.urlopen(urllib.request.Request(path,method='DELETE'),timeout=15) as response:
   assert json.load(response).get('success') is True, 'owned note deletion failed'
 assert not owned_notes(), 'owned note cleanup incomplete'
print('VERDICT PASS vietnamese_scoped_titled_note_and_owned_cleanup',flush=True)
PY
""".replace('__UID__',repr(uid))
    client=connect()
    try:
        output=sanitize(sudo_bash(client,remote,timeout=240))
    finally:
        client.close()
    out=ROOT/'test/reports/run-zalo-note-locale'
    out.mkdir(parents=True,exist_ok=True)
    passed='VERDICT PASS vietnamese_scoped_titled_note_and_owned_cleanup' in output
    (out/'raw.log').write_text(output,encoding='utf-8')
    (out/'SUMMARY.json').write_text(json.dumps({'verdict':'PASS' if passed else 'FAIL','checks':3,
       'scoped_storage_verified':passed,'owned_cleanup':passed},indent=2)+'\n',encoding='utf-8')
    print(output,flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
