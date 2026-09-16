#!/usr/bin/env python3
"""Live remote-video refusal: exact source ACK, terminality and semantic review."""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from deploy_stack import connect,sudo_bash
from sanitize import sanitize
ROOT=Path(os.environ.get('ASSISTANT_REPO_ROOT',Path(__file__).resolve().parents[2]))
UID=(os.environ.get('ZALO_TEST_USER_ID') or '').strip()
WAIT=int(os.environ.get('ZALO_TEST_WAIT_S') or '120')
MSG='tóm tắt nội dung video này giúp mình: https://www.youtube.com/watch?v=dQw4w9WgXcQ'


def main():
    if not UID:
        print('ERROR: ZALO_TEST_USER_ID is required',file=sys.stderr)
        return 2
    source='lab-yt-refuse-'+str(time.time_ns())
    remote=r"""
set -euo pipefail
cd /opt/assistant
python3 - <<'PY'
import json,os,subprocess,sys,time,urllib.request
sys.path.insert(0,'/opt/assistant/test/scripts')
from scoped_documents_smoke_lab import delivered,ensure_ready,thread_terminal
uid=__UID__; source=__SOURCE__; message=__MESSAGE__; wait=__WAIT__
ensure_ready()
print('SOURCE_ID '+source,flush=True)
print('running test case 1/2: exact source native text ACK and terminality',flush=True)
event={'type':'message','threadId':uid,'threadType':'user','senderId':uid,
       'senderName':'test-user','text':message,'messageId':source}
request=urllib.request.Request('http://127.0.0.1:8787/inject-event',method='POST',
  data=json.dumps(event,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=30) as response:
 assert json.load(response).get('ok') is True, 'injection failed'
deadline=time.monotonic()+wait; settled=None; rows=[]
while time.monotonic()<deadline:
 # Host policy refusals intentionally have delivery_kind=gate. Count them;
 # semantic review below distinguishes an honest refusal from control chatter.
 rows=delivered(source)
 if len(rows)>1:
  raise SystemExit('VERDICT FAIL duplicate_or_extra_source_delivery')
 if rows and thread_terminal(uid):
  settled=settled or time.monotonic()
  if time.monotonic()-settled>=6:
   break
 else:
  settled=None
 time.sleep(2)
else:
 raise SystemExit('VERDICT FAIL terminal_refusal_timeout')
assert len(rows)==1 and str(rows[0].get('message_id') or '').isdigit(), 'native ACK absent'
meta=rows[0].get('meta') or {}
assert not meta.get('file_name') and not meta.get('attachment_kind'), 'unexpected source attachment'
content=str(rows[0].get('content') or '').strip()
assert content, 'empty delivered refusal'
container=subprocess.check_output(['docker','ps','--filter','label=com.docker.compose.service=dispatcher',
  '--format','{{.Names}}'],text=True).splitlines()
assert len(container)==1, 'semantic evaluator ambiguous'
print('running test case 2/2: honest useful refusal and late-extra recheck',flush=True)
judge="answer="+repr(content)+'\n'+r'''
import json,os,urllib.request
prompt=('Judge this answer to a request to summarize a remote video URL that the system cannot consume. '
 'Pass only if it clearly and helpfully states the limitation, does not claim any facts about the '
 'video, and does not pretend a summary was produced. Return JSON only with boolean pass, integer '
 'quality_score from 1 to 10, and short reason. ANSWER='+json.dumps(answer))
body=json.dumps({'model':'hermes','stream':False,'max_tokens':180,
 'messages':[{'role':'user','content':prompt}]}).encode()
base=(os.environ.get('OMNIROUTER_BASE_URL') or 'http://omni-router:20129/v1').rstrip('/')
request=urllib.request.Request(base+'/chat/completions',method='POST',data=body,
 headers={'Authorization':'Bearer '+os.environ.get('OMNIROUTER_API_KEY',''),'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=180) as response:
 data=json.load(response)
message=((data.get('choices') or [{}])[0].get('message') or {})
value=(message.get('content') or message.get('reasoning_content') or '').strip()
start=value.find('{'); end=value.rfind('}')
assert start>=0 and end>=start, 'malformed evaluator result'
print(value[start:end+1])
'''
result=subprocess.run(['docker','exec','-i',container[0],'python3','-'],input=judge,
 text=True,capture_output=True,timeout=210)
assert result.returncode==0, 'semantic evaluator unavailable; not PASS'
evaluation=json.loads(result.stdout.strip())
assert evaluation.get('pass') is True and int(evaluation.get('quality_score') or 0)>=7, 'dishonest or low-quality refusal'
final=delivered(source)
assert final==rows and thread_terminal(uid), 'late extra or nonterminal delivery'
print('DELIVERED_RESPONSE '+json.dumps(content,ensure_ascii=False))
print('SELF_EVALUATION '+json.dumps(evaluation,ensure_ascii=False))
print('VERDICT PASS source_bound_terminal_honest_refusal_no_attachment')
PY
"""
    # The nested evaluator is a separate Python string, not shell interpolation.
    remote=remote.replace('__UID__',repr(UID)).replace('__SOURCE__',repr(source))
    remote=remote.replace('__MESSAGE__',repr(MSG)).replace('__WAIT__',str(WAIT))
    client=connect()
    try:
        output=sanitize(sudo_bash(client,remote,timeout=WAIT+270))
    finally:
        client.close()
    out=ROOT/'test/reports/run-zalo-tn-youtube-refuse'
    out.mkdir(parents=True,exist_ok=True)
    passed='VERDICT PASS source_bound_terminal_honest_refusal_no_attachment' in output
    (out/'remote.txt').write_text(output,encoding='utf-8')
    (out/'SUMMARY.json').write_text(json.dumps({'verdict':'PASS' if passed else 'FAIL',
      'source':source,'terminal':passed,'semantic_evaluated':passed},indent=2)+'\n',encoding='utf-8')
    print(output,flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
