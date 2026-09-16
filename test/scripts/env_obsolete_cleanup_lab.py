#!/usr/bin/env python3
"""VPS gate: real obsolete-env cleanup on private owned fixtures only."""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from deploy_stack import connect,sudo_bash
from sanitize import sanitize
ROOT=Path(os.environ.get("ASSISTANT_REPO_ROOT",Path(__file__).resolve().parents[2]))

def main():
    remote=r"""
set -euo pipefail
cd /opt/assistant
python3 - <<'PY'
import os,subprocess,tempfile
from pathlib import Path
import sys
sys.path.insert(0,'/opt/assistant/scripts/main')
from openbao_common import OBSOLETE_ENV_KEYS
os.umask(0o077)
real_paths=[Path('/opt/assistant/.env'),Path('/data/assistant/.env')]
before={p:p.read_bytes() if p.is_file() else None for p in real_paths}
retired=set(OBSOLETE_ENV_KEYS)
def keys(p):
 return {line.partition('=')[0].strip() for line in p.read_text().splitlines()
         if line.strip() and not line.lstrip().startswith('#') and '=' in line}
def values(p):
 return {line.partition('=')[0].strip():line.partition('=')[2].strip()
         for line in p.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#')}
print('running test case 1/3: retired keys and exact-default migration',flush=True)
with tempfile.TemporaryDirectory(prefix='hermes-env-lab-',dir='/tmp') as temporary:
 fixture=Path(temporary).resolve()
 assert fixture.parent==Path('/tmp') and fixture.name.startswith('hermes-env-lab-')
 root=fixture/'root'; data=fixture/'data'; root.mkdir(); data.mkdir()
 assert fixture.stat().st_mode & 0o777 == 0o700
 payload=''.join(k+'=owned-retired-fixture\n' for k in sorted(retired))
 (root/'.env').write_text(payload+'KEEP_SETTING=owned-retained\nZALO_BRIDGE_URL=http://host.docker.internal:8787\nZALO_INBOUND_QUEUE_MAX=8\n')
 (data/'.env').write_text(payload+'KEEP_SETTING=owned-retained\nZALO_INBOUND_QUEUE_MAX=64\n')
 env={**os.environ,'STACK_ROOT':str(root),'ASSISTANT_DATA_DIR':str(data)}
 command=['python3','/opt/assistant/scripts/main/cleanup-obsolete-env.py']
 subprocess.run(command,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
 assert not ((keys(root/'.env')|keys(data/'.env')) & retired), 'retired fixture keys remain'
 first=values(root/'.env'); second=values(data/'.env')
 assert first['KEEP_SETTING']==second['KEEP_SETTING']=='owned-retained'
 assert first['ZALO_BRIDGE_URL']=='http://traefik:8081/zalo-bridge'
 assert first['ZALO_INBOUND_QUEUE_MAX']=='16' and second['ZALO_INBOUND_QUEUE_MAX']=='64'
 print('running test case 2/3: idempotence and private fixture modes',flush=True)
 snapshot={p:p.read_bytes() for p in (root/'.env',data/'.env')}
 subprocess.run(command,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=30)
 assert all(p.read_bytes()==content and p.stat().st_mode & 0o777 == 0o600 for p,content in snapshot.items())
assert not fixture.exists(), 'owned fixture cleanup incomplete'
print('running test case 3/3: operator environment unchanged',flush=True)
assert all((p.read_bytes() if p.is_file() else None)==content for p,content in before.items()), 'operator env changed during isolated test'
assert not (set().union(*(keys(p) for p in real_paths if p.is_file())) & retired), 'operator env still contains retired pins'
print('VERDICT PASS private_fixture_cleanup_operator_unchanged')
PY
"""
    client=connect()
    try:
        output=sanitize(sudo_bash(client,remote,timeout=120))
    finally:
        client.close()
    out=ROOT/"test/reports/run-env-obsolete-cleanup"
    out.mkdir(parents=True,exist_ok=True)
    passed="VERDICT PASS private_fixture_cleanup_operator_unchanged" in output
    (out/"result.log").write_text(output,encoding="utf-8")
    (out/"SUMMARY.json").write_text(json.dumps({"timestamp":datetime.now(timezone.utc).isoformat(),
        "verdict":"PASS" if passed else "FAIL","owned_fixtures":True,"operator_env_unchanged":passed},indent=2)+"\n",encoding="utf-8")
    print(output,flush=True)
    return 0 if passed else 1
if __name__=="__main__":
    raise SystemExit(main())
