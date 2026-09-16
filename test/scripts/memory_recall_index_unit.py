#!/usr/bin/env python3
"""Indexed recall contracts and actual vector/compact function regressions."""
from __future__ import annotations

import ast
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import uuid


def vector_contract(path: Path) -> None:
    """Execute production functions; isolated transports do not certify live RAG."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {"compact", "_index_memory", "_embed"}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for node in functions:
        node.decorator_list = []
    calls = []
    response = SimpleNamespace(status_code=200, json=lambda: {"data": [{"embedding": [1.0, 2.0]}]},
                               raise_for_status=lambda: None)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, *args): return self
        def commit(self): pass
        def rollback(self): pass
        rowcount = 0
        def fetchall(self): return [{"id": "owned-fixture", "content": "fixture", "type": "fact", "importance": .5}]
    ns = {"Query": lambda value, **kw: value, "Any": object, "uuid": uuid, "math": math,
          "QDRANT_URL": "http://index", "QDRANT_COLLECTION": "fixture", "EMBED_URL": "http://embed",
          "EMBED_MODEL": "embedding", "EMBED_API_KEY": "", "STAGED_RETENTION_DAYS": 7,
          "db": lambda: SimpleNamespace(connection=Connection), "_timing_add": lambda *args: None,
          "_ensure_qdrant_collection": lambda **kw: None,
          "httpx": SimpleNamespace(post=lambda *a, **kw: response,
                                   put=lambda *a, **kw: (calls.append(kw["json"]) or response))}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), ns)
    failures = []
    def check(label, ok):
        if not ok: failures.append(label)
    index = ns["_index_memory"]
    check("successful upsert must return acknowledgement", index("owned-fixture", "fixture", "fact", .5) is True)
    node = next(n for n in functions if n.name == "_index_memory")
    point_id = next(v for n in ast.walk(node) if isinstance(n, ast.Dict)
                    for k, v in zip(n.keys, n.values) if isinstance(k, ast.Constant) and k.value == "id")
    expression = ast.unparse(point_id)
    probe = "import uuid; mid='owned-fixture'; print(" + expression + ")"
    identities = [subprocess.check_output([sys.executable, "-c", probe], text=True,
                    env={**os.environ, "PYTHONHASHSEED": seed}).strip() for seed in ("1", "2")]
    check("index identity must survive process restart", identities[0] == identities[1])
    ns["_embed"] = lambda text: None
    failed = ns["compact"]()
    check("missing vector must not claim indexing success", failed["reindexed"] == 0 and not failed["embed"] and not failed["ok"])
    ns["QDRANT_URL"] = ""
    inactive = ns["compact"]()
    check("inactive index must report zero upserts", inactive["reindexed"] == 0 and not inactive["embed"])
    # Restore actual embed function to exercise malformed provider payloads.
    embed_node = next(n for n in functions if n.name == "_embed")
    exec(compile(ast.Module(body=[embed_node], type_ignores=[]), str(path), "exec"), ns)
    response.json = lambda: {"data": [{"embedding": [float("nan"), 0.0]}]}
    check("nonfinite vectors must be rejected", ns["_embed"]("fixture") is None)
    assert not failures, "; ".join(failures)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    path = root / "architect" / "memory" / "memory-worker" / "app.py"
    source = path.read_text(encoding="utf-8")
    ast.parse(source)
    assert "memories_session_idx" in source
    assert "memories_thread_session_created_idx" in source
    recall = source.split("def recall(req: RecallReq)", 1)[1]
    recall = recall.split('@app.get("/v1/search")', 1)[0]
    assert 'clauses.append("session_id = %s")' in recall
    assert 'clauses.append("created_at >= %s")' in recall
    assert 'clauses.append("created_at <= %s")' in recall
    assert "base_clauses = list(clauses)" in recall
    assert "to_tsvector('simple', coalesce(content, ''))" in recall
    assert "AND content ILIKE %s" in recall
    primary = recall.split("fallback_sql", 1)[0]
    assert " OR content ILIKE " not in primary
    assert '"session_id": r["session_id"]' in recall
    lab = (root / "test" / "scripts" / "memory_scale_10m_lab.py").read_text(
        encoding="utf-8"
    )
    assert "ROWS = 10_000_000" in lab
    assert "knowledge_accuracy" in lab and "old_session_accuracy" in lab
    assert "DROP TABLE IF EXISTS" in lab
    assert 'TABLE = "memory_scale_lab_" + uuid.uuid4().hex' in lab
    assert "WHEN n IN (1700003, 1700004)" in lab
    assert "session == \"1700003|oldsession" in lab
    assert 'raise RuntimeError("memory_scale_fixture_cleanup_failed") from exc' in lab
    vector_contract(path)
    print("memory_recall_index_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
