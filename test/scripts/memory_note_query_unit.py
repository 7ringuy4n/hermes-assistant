"""Execute the production query handler with a recording persistence boundary."""
from __future__ import annotations
import ast
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    source = ROOT / "architect/memory/memory-worker/app.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "query_notes")
    function.decorator_list = []
    function.returns = None
    for argument in function.args.args:
        argument.annotation = None
    calls = []
    class Database:
        @contextmanager
        def connection(self):
            yield self
        def execute(self, sql, params):
            calls.append((sql, params))
            return SimpleNamespace(fetchall=lambda: [])
    env = {"db": Database, "_parse_note_date": lambda value, key: value,
           "_note_row": lambda row: row, "Any": object,
           "HTTPException": lambda code, text: ValueError(text)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), env)
    for index, scopes in enumerate(([], ["zalo:user:u", "zalo:group:g"]), start=1):
        print(f"running test case {index}/2 strict query/date/tags with scoped SQL")
        calls.clear()
        request = SimpleNamespace(scope_id="zalo:user:u", scope_ids=scopes, id=None,
            query="unmatched predicate", date_from="2026-09-01", date_to="2026-09-14",
            tags=["category"], limit=10)
        result = env["query_notes"](request)
        assert result["items"] == [] and result["query_fallback"] is False
        assert len(calls) == 1
        sql, params = calls[0]
        assert "note_date >=" in sql and "note_date <=" in sql and "tags &&" in sql
        assert params[0] == (scopes or request.scope_id)
        assert "unmatched predicate" in params and request.tags in params
    print("PASS strict memory query")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
