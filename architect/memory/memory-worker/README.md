# memory / memory-worker

## Purpose

Central Memory Worker Hermes calls instead of growing a giant `MEMORY.md`. Postgres is the source of truth for typed memories; optional Qdrant index helps retrieval. Exposes context assembly and remember APIs.

## Profile

Must — container `memory`.

The component was renamed from memory-manager to memory-worker. The deployment
service key, container name, `MEMORY_URL`, and `run.sh update memory` remain
`memory` for compatibility; the Docker build source is now `memory-worker/`.
This is a source/component rename, not a database or data-volume migration.

Durable notes use `/v1/notes` and `/v1/notes/query` with exact conversation or
trusted local Hermes scopes. Host-authorized multi-scope queries use
`scope_ids`; this internal service is not an unauthenticated public admin API.
The direct notes command does not require Zalo or Message Worker.

## Main functions

| API / job | Function |
|---|---|
| `POST /v1/context` | Given user text (+ flags), return mode hints, skills list, budgeted memories |
| `POST /v1/remember` | Persist a durable fact/event (async from agent) |
| `POST /v1/compact` | Daily housekeeping: retire staged drafts older than `MEMORY_STAGED_RETENTION_DAYS` and re-index recent rows |

## Memory kinds (conceptual)

| Kind | Meaning |
|---|---|
| Working | Ephemeral turn hints (not long-lived here) |
| Episodic | Events / interactions |
| Semantic | Facts, preferences, decisions |
| Procedural | Pointers to skills on disk (`hermes/main/skills`) |

## Env (typical)

`DATABASE_URL`, `REDIS_URL` (Valkey; env name kept for clients), `QDRANT_URL`, `CONTEXT_BUDGET_TOKENS`, `MEMORY_STAGED_RETENTION_DAYS` (default 7), `TZ`

## Related

- [../README.md](../README.md)
- [session](../session/README.md)
