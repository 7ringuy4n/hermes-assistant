#!/usr/bin/env python3
"""Real OpenBao rotation/load/scrub using an owned KV and private consumer.

Production KV, token, environment and consumers are read-only. This does not
rotate an invalid key into the live production Router Worker.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_stack import connect, sudo_bash
from sanitize import sanitize
ROOT = Path(os.environ.get('ASSISTANT_REPO_ROOT', Path(__file__).resolve().parents[2]))


def main():
    remote = r"""
set -euo pipefail
cd /opt/assistant
python3 - <<'PY'
import json,os,subprocess,tempfile,urllib.request,urllib.error,uuid
from pathlib import Path
import sys
sys.path.insert(0,'/opt/assistant/scripts/main')
from openbao_common import OPENBAO_SECRET_PATH,SEED_KEYS
os.umask(0o077)
token_file=Path('/data/assistant/openbao/root-token')
token=token_file.read_text().strip()
assert token and not token.startswith('CHANGE_ME'), 'protected token unavailable'
addr='http://127.0.0.1:8200/v1/'
owned='secret/data/assistant/kv-lab-'+uuid.uuid4().hex
metadata=owned.replace('secret/data/','secret/metadata/',1)
created=False
def api(method,path,body=None):
 request=urllib.request.Request(addr+path,method=method,
   headers={'X-Vault-Token':token,'Content-Type':'application/json'},
   data=json.dumps(body).encode() if body is not None else None)
 with urllib.request.urlopen(request,timeout=15) as response:
  raw=response.read()
  return json.loads(raw) if raw else {}
def consumer():
 raw=subprocess.check_output(['docker','inspect','router-worker','--format','{{json .Config.Env}}'],text=True,timeout=15)
 return json.loads(raw)
paths=[Path('/opt/assistant/.env'),Path('/data/assistant/.env'),
       Path('/data/assistant/.env.openbao'),token_file]
before={p:p.read_bytes() if p.is_file() else None for p in paths}
production=api('GET',OPENBAO_SECRET_PATH)
consumer_before=consumer()
assert bool(production['data']['data'].get('OMNIROUTER_API_KEY'))
assert 'POLLINATIONS_API_KEY' in SEED_KEYS
image=subprocess.check_output(['docker','inspect','router-worker','--format','{{.Image}}'],text=True,timeout=15).strip()
try:
 print('running test case 1/4: isolated KV create and versioned rotation',flush=True)
 response=api('POST',owned,{'options':{'cas':0},'data':{'TAVILY_API_KEY':'owned-fixture-v1'}})
 created=True
 assert response['data']['version']==1
 with tempfile.TemporaryDirectory(prefix='hermes-openbao-lab-',dir='/tmp') as temporary:
  fixture=Path(temporary).resolve()
  assert fixture.parent==Path('/tmp') and fixture.name.startswith('hermes-openbao-lab-')
  assert fixture.stat().st_mode & 0o777 == 0o700
  root=fixture/'root'; data=fixture/'data'; root.mkdir(); data.mkdir()
  (root/'.env').write_text('KEEP_SETTING=owned-retained\nTAVILY_API_KEY=owned-plaintext-fixture\n')
  env={**os.environ,'STACK_ROOT':str(root),'ASSISTANT_DATA_DIR':str(data),
    'HERMES_DATA_DIR':str(data),'OPENBAO_TOKEN_FILE':str(token_file),
    'OPENBAO_ADDR':addr.removesuffix('/v1/'),'OPENBAO_SECRET_PATH':owned}
  env.pop('OPENBAO_DEV_ROOT_TOKEN',None)
  def run(name):
   result=subprocess.run(['python3','/opt/assistant/scripts/main/'+name],env=env,
      capture_output=True,text=True,timeout=30)
   assert result.returncode==0, 'actual loader/scrubber failed: '+name
  def load_and_consume(expected):
   run('load-openbao-env.py')
   export=data/'.env.openbao'
   assert export.stat().st_mode & 0o777 == 0o600
   assert export.read_text()=='TAVILY_API_KEY='+expected+'\n'
   result=subprocess.run(['docker','run','--rm','--network','none','--env-file',str(export),
      '-e','LAB_EXPECTED='+expected,'--entrypoint','python3',image,'-c',
      "import os; assert os.environ['TAVILY_API_KEY']==os.environ['LAB_EXPECTED']; print('OWNED_CONSUMER_PASS')"],
      capture_output=True,text=True,timeout=60)
   assert result.returncode==0 and result.stdout.strip()=='OWNED_CONSUMER_PASS', 'isolated consumer failed'
   run('scrub-plaintext-env.py')
   assert not export.exists() and not (data/'.env').exists()
   content=(root/'.env').read_text()
   assert 'KEEP_SETTING=owned-retained' in content and 'TAVILY_API_KEY=\n' in content
   assert expected not in content and 'owned-plaintext-fixture' not in content
  print('running test case 2/4: actual loader, isolated consumer and scrub v1',flush=True)
  load_and_consume('owned-fixture-v1')
  response=api('POST',owned,{'options':{'cas':1},'data':{'TAVILY_API_KEY':'owned-fixture-v2'}})
  assert response['data']['version']==2
  assert api('GET',owned)['data']['data']=={'TAVILY_API_KEY':'owned-fixture-v2'}
  print('running test case 3/4: rotation loads new value and scrub v2',flush=True)
  load_and_consume('owned-fixture-v2')
 assert not fixture.exists(), 'private export cleanup incomplete'
finally:
 if created:
  api('DELETE',metadata)
  try:
   api('GET',metadata)
  except urllib.error.HTTPError as error:
   assert error.code==404, 'owned KV cleanup not confirmed'
  else:
   raise AssertionError('owned KV metadata still present')
print('running test case 4/4: production KV, token, env and consumer unchanged',flush=True)
assert api('GET',OPENBAO_SECRET_PATH)['data']==production['data'], 'production KV changed'
assert consumer()==consumer_before, 'production consumer environment changed'
assert all((p.read_bytes() if p.is_file() else None)==raw for p,raw in before.items()), 'production file changed'
print('VERDICT PASS isolated_rotation_load_scrub_operator_unchanged')
PY
"""
    client=connect()
    try:
        output=sanitize(sudo_bash(client,remote,timeout=240))
    finally:
        client.close()
    out=ROOT/'test/reports/run-openbao-kv'
    out.mkdir(parents=True,exist_ok=True)
    passed='VERDICT PASS isolated_rotation_load_scrub_operator_unchanged' in output
    (out/'remote.txt').write_text(output,encoding='utf-8')
    (out/'SUMMARY.json').write_text(json.dumps({'verdict':'PASS' if passed else 'FAIL',
       'owned_kv_path':True,'production_rotation':False,'operator_unchanged':passed},indent=2)+'\n',encoding='utf-8')
    print(output,flush=True)
    return 0 if passed else 1


if __name__=='__main__':
    raise SystemExit(main())
