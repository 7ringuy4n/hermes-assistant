#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VPS lab: embedding combo Requested Model + memory /v1/compact."""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_stack import connect, sudo_bash  # noqa: E402
from sanitize import sanitize

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("ASSISTANT_REPO_ROOT", Path(__file__).resolve().parents[2]))
OUT = ROOT / "test" / "reports" / "run-embedding-compact"


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def _clean(text: str) -> str:
    lines = []
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if "sudo" in low and "password" in low:
            continue
        if low.startswith("[sudo"):
            continue
        lines.append(s)
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    c = connect()
    remote = r"""
set -euo pipefail
python3 - <<'PY'
import json, math, subprocess, urllib.request, sys
sys.path.insert(0,'/opt/assistant/test/scripts')
from sanitize import sanitize

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode() or "{}")

def post(url, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")

checks = []
def note(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:160]})
    print(("PASS" if ok else "FAIL"), name, str(detail)[:120])

# Direct embedding service with combo model name
try:
    emb = post("http://127.0.0.1:8094/v1/embeddings", {"model": "embedding", "input": "compact lab ping"})
    vecs = emb.get("data") or []
    vector = (vecs[0] or {}).get("embedding") or [] if vecs else []
    dim = len(vector)
    model = str(emb.get("model") or "")
    valid = (dim >= 8 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                             and math.isfinite(v) for v in vector) and any(v != 0 for v in vector))
    note("embed_http", valid, f"dim={dim} model={model or 'embedding'}")
    note("embed_model_echo", bool(model) and ("embedding" in model or "/" in model or dim >= 8), model or "ok")
except Exception as e:
    note("embed_http", False, type(e).__name__)

# Actual HTTP route against isolated real Postgres/Qdrant fixtures. Never run
# global staged retention over the operator's database merely to test compact.
try:
    code = '''
import app,json,math,uuid,httpx,psycopg,hashlib
from psycopg import sql
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from fastapi.testclient import TestClient
token=uuid.uuid4().hex
schema='compact_lab_'+token
collection='compact_lab_'+token
mid='compact-owned-'+token
needle='restart grounded memory '+token
assert app.EMBED_URL and app.QDRANT_URL, 'configured embedding/index required'
conn=psycopg.connect(app.DSN,autocommit=True)
pool=None; created=False; collection_owned=False
result=None
try:
 conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema))); created=True
 conn.execute(sql.SQL('CREATE TABLE {}.memories (LIKE public.memories INCLUDING DEFAULTS)').format(sql.Identifier(schema)))
 conn.execute(sql.SQL('INSERT INTO {}.memories (id,content,type,importance,content_hash,active,staged) VALUES (%s,%s,%s,%s,%s,true,false)').format(sql.Identifier(schema)),(mid,needle,'fact',.5,hashlib.sha256(needle.encode()).hexdigest()))
 conn.execute(sql.SQL("INSERT INTO {}.memories (id,content,type,importance,content_hash,active,staged,created_at) VALUES (%s,%s,%s,%s,%s,true,true,now()-interval '4000 days')").format(sql.Identifier(schema)),('staged-'+token,'owned stale fixture','fact',.5,hashlib.sha256(('staged-'+token).encode()).hexdigest()))
 # Only this short-lived diagnostic process sees these isolated globals.
 pool=ConnectionPool(app.DSN,min_size=1,max_size=2,kwargs={'options':'-c search_path='+schema,'row_factory':dict_row,'autocommit':True})
 app.pool=pool; app.QDRANT_COLLECTION=collection
 collection_owned=True
 client=TestClient(app.app)
 for run in range(2):
  response=client.post('/v1/compact?limit=1',json={}); response.raise_for_status()
  compact=response.json()
  assert compact.get('ok') and compact.get('embed') and compact.get('reindexed')==1, 'compact did not acknowledge fixture upsert'
  if run==0: assert compact.get('deactivated_staged')==1, 'owned stale retention missing'
  point_response=httpx.post(app.QDRANT_URL+'/collections/'+collection+'/points/scroll',json={'limit':10,'with_payload':True,'with_vector':True},timeout=15)
  point_response.raise_for_status(); points=point_response.json()['result']['points']
  assert len(points)==1, 'reindex duplicated vector identity'
  point=points[0]; vector=point['vector']
  assert point['payload']['memory_id']==mid and point['payload']['content']==needle, 'index lost fixture grounding'
  assert vector and all(isinstance(v,(int,float)) and math.isfinite(v) for v in vector) and any(vector), 'invalid stored vector'
  assert str(point['id'])==str(uuid.uuid5(uuid.NAMESPACE_URL,'hermes-stack:memory:'+mid)), 'unstable index identity'
 result={'ok':True,'compact_reindexed':1,'repeat_points':1,'grounded':True,'isolated_retention':True,'embed_model':compact['embed_model']}
finally:
 if pool: pool.close()
 if collection_owned:
  cleanup=httpx.delete(app.QDRANT_URL+'/collections/'+collection,timeout=15)
  assert cleanup.status_code in (200,404), 'owned vector cleanup failed'
 if created:
  conn.execute(sql.SQL('DROP TABLE IF EXISTS {}.memories').format(sql.Identifier(schema)))
  conn.execute(sql.SQL('DROP SCHEMA {}').format(sql.Identifier(schema)))
 conn.close()
print(json.dumps({**result,'owned_cleanup':True}))
'''
    container = subprocess.check_output(['docker','ps','--filter','label=com.docker.compose.service=memory','--format','{{.Names}}'],text=True).splitlines()[0]
    raw = subprocess.check_output(['docker','exec',container,'python3','-c',code],text=True,stderr=subprocess.STDOUT,timeout=150)
    compact = json.loads(raw.strip().splitlines()[-1])
    note("compact_acknowledged_index", compact.get('ok') and compact.get('grounded') and compact.get('repeat_points')==1, 'isolated real SQL/vector HTTP route')
    note("compact_owned_cleanup", compact.get('owned_cleanup'), 'no operator records touched')
except Exception as e:
    detail = sanitize(str(getattr(e, 'output', '') or type(e).__name__))[-300:]
    note("compact_ok", False, detail)

# Web search body carries model=combo (router worker)
try:
    # Health only — full search may rate-limit; still verify router search path exists
    with urllib.request.urlopen("http://127.0.0.1:8096/health", timeout=15) as r:
        note("router_health", r.status == 200, r.status)
except Exception as e:
    note("router_health", False, type(e).__name__)

ok = all(x["ok"] for x in checks)
print("VERDICT", "PASS" if ok else "FAIL")
print(json.dumps({"checks": checks, "ok": ok}))
raise SystemExit(0 if ok else 1)
PY
"""
    out = _clean(sudo_bash(c, remote, timeout=240))
    (OUT / "remote.txt").write_text(out, encoding="utf-8")
    print(out)
    verdict = "PASS" if "VERDICT PASS" in out else "FAIL"
    report = {"ts": ts(), "verdict": verdict}
    try:
        for ln in out.splitlines():
            if ln.startswith("{") and '"checks"' in ln:
                report["payload"] = json.loads(ln)
                break
    except Exception:
        pass
    (OUT / "SUMMARY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REPORT", OUT / "SUMMARY.json", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
