# 03 — System architecture

The [worker/feature catalog](./07-worker-feature-catalog.md) enumerates current
services, descriptions, default activation, bundle dependencies and scaffolds
for architecture revision. Defaults are not the testing host's effective state.

## Direct and messaging execution

Existing attachments are converted by the shared Media/File worker through
`file-convert` and `/v1/file-convert`. Native DOCX/XLSX/PPTX print export uses
isolated LibreOffice profiles; PDF/Office page images use bounded PyMuPDF
rasterization. Editable cross-format outputs explicitly use content reflow,
not a false claim of layout preservation. Sheets/pages remain distinct;
imported formula-like strings are inert. Scanned text extraction requires OCR.
Inputs stay in approved media roots; macros, fetchable external Office resources,
invalid page selections and resource-limit violations fail before delivery.
Successful outputs live in private `.conversions/` directories; clients send
only the requested outputs, not source/intermediate files.

Standalone schedule fires use Hermes `/v1/runs` asynchronous admission with
execution idempotency. A confirmed run ID records handoff acceptance, not task
completion; the scheduler never waits for the whole model turn on its 15-second
transport timeout. Configure `HERMES_RUN_URL` for this native API, independently
of chat-completion provider endpoints.

Capabilities are shared by direct Hermes CLI/API and messaging sessions. Zalo
and Message Worker are optional ingress, queueing, and delivery components—not
requirements for direct note storage, schedule persistence, image generation,
or office rendering. Capability services still need to be configured/available.
Direct notes use the host-owned `HERMES_RECORD_SCOPE`; direct office creation
sets `send_zalo=false` with no thread; direct schedules set
`origin.platform=hermes` and hand off through `HERMES_RUN_URL`.

The durable-memory component is `architect/memory/memory-worker/`. Its existing
Compose key/container/DNS `memory` and update command remain compatible. The
rename does not change database schemas or volumes. Historical incident paths
describe the names at the time of the incident.

## Logical view

```text
Users
  ├─ Hermes console / HTTP → Hermes skills → shared capability services
  └─ Zalo → host bridge → zalo-proxy → Traefik
                                      │
                                      ▼
                         Valkey-elected Hermes owner
                                      │
                                      ▼
                           per-conversation queue
                         │
                         ▼
                 Hermes (1 or 2; messaging path)
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
 memory/session     classify/skills   workflow/schedule
        │                │                 │
        ▼                ▼                 ▼
Postgres/Valkey   router-worker       Postgres + worker
Qdrant                    │
                          ▼
                 OmniRoute priority combos
          hermes · classifier · web-search · image-gen
            vision-ocr · embedding · image-edit
```

## Deployment layers

| Layer | Ownership |
|---|---|
| `hermes/` | Agent configuration, skills, plugins, message contracts, replica runtime. |
| `architect/models/` | router-worker, OmniRoute integration, attribution, dispatcher/jobs. |
| `architect/memory/` | Session, long-term memory, ingest, embedding clients. |
| `architect/social-app/` and `architect/zalo-api/` | Channel session, inbound/outbound API, queue ownership. |
| `architect/schedule-worker/` | Deterministic scheduled execution. |
| `architect/security/` | Secrets, policy, authorization, audit, optional antivirus. |
| `architect/monitor/` | Metrics, dashboards, logs, alerting and health observation. |
| `architect/backup-restore/` | Verified backup, restore, worker flags, migrations. |
| `docker/` | Core compose and optional overlays. |

## Capability paths

| Request | Path |
|---|---|
| Chat | Hermes → router-worker → `hermes` combo |
| Classification | classify prompt → router-worker → `classifier` combo → validated JSON |
| Web research | web-search skill/dispatcher → `web-search` combo |
| New still image | image-gen skill → `image-gen` combo |
| Image edit | attached/reply-quoted image → image-edit skill → `image-edit` combo |
| Image/document analysis | media staging → `vision-ocr` combo → natural analysis |
| Knowledge ingest | ingest → embedding service → `embedding` combo → Qdrant |
| Durable notes | classify → notes host route → scoped PostgreSQL note/date indexes + audit |
| Timed work | schedule skill → schedule-worker/Postgres → later queue injection |
| Stop active work | classify control intent → thread-local active task cancellation → queue continues |
| Office artifact | documents skill/file tooling → staged artifact → visual QA → outbound file |

Notes and schedules default to the current typed conversation. Cross-group or
cross-DM access requires the adapter's authenticated operator-admin identity and
an explicit registry-resolved reference; a model-provided role never grants
access. All-scope access is read-only. Note all-scope lookup batches registered
conversation scopes through `NoteQueryReq.scope_ids` in one PostgreSQL query.
Memory remains an internal trusted-service API; end-user authorization belongs
at the messaging adapter, not in model-generated API parameters.

Exact note queries retain every scope/date/tag/text filter. Semantic predicates
use `semantic_query` and a versioned selection prompt; the host validates returned
IDs and fails closed on uncertainty, context overflow, or a saturated retrieval
window. `NOTES_SELECTION_MAX_BYTES` bounds model input (default 131072 bytes).
Schedule requester/sender IDs are audit data, not conversation-visibility keys.

New PDFs are model-authored HTML rendered by WeasyPrint. Embedded assets use
the exact returned `hermes_path`; Dispatcher translates shared-volume aliases
to `MEDIA_CACHE_DIR`, validates local resources, and rejects missing/corrupt or
external resources rather than delivering blank image boxes. Native text keeps
the requested language. DOCX/XLSX/PPTX embed validated `IMAGE:` assets. Scenic
document assets stay under `media/out/.assets`; office files are built under
`.build` and atomically published only after rendering. Both autosend claim
checks terminate at an already-delivered rich document instead of exposing
older illustrations or alternate drafts.

There is no supported video generation/editing capability and no separate
PaddleOCR, Tesseract, ComfyUI, 9Router, or legacy OmniRouter service.

## Concurrency and availability

Hermes replicas share durable services but have isolated runtime homes. HTTP
requests are active-active: Traefik resolves the Compose `hermes` service and
selects a healthy replica. Zalo ingestion is active-passive: every replica
loads the adapter against Traefik's internal bridge route, while an expiring,
renewed Valkey lease permits exactly one active SSE consumer. If that replica
dies, a standby acquires the lease without restarting the replica set.

The elected Zalo owner writes an event to a Valkey FIFO keyed by conversation,
claims that conversation's Valkey worker lock, and atomically moves the FIFO
head to a durable in-flight list before executing it locally. Terminal turns
acknowledge the claim. Its adapter sends the result back through Traefik,
`zalo-proxy`, and the host bridge to the event's original DM or group. There is
no callback to a separately selected ingress replica. Another conversation may
run at the same time. If ownership changes, the old owner cancels local work;
the promoted owner discovers registered queues, fences worker locks owned by
the previous lease holder, restores abandoned claims to the FIFO head, and
resumes them. Routine worker leases exceed the bounded turn deadline, so a
slow healthy request is never reclaimed by the periodic scanner. Duplicate
message IDs and worker leases prevent concurrent handling. Quote-reply
correlation is carried as message metadata and staged media, not inferred from
global recent state.

Before durable admission, an owner-local sequencer processes SSE events in
arrival order for each conversation. Cancellation can still bypass the work
queue after deterministic access/addressing checks, but a slow semantic check
cannot allow a later ordinary message to overtake an earlier one. Claimed agent
turns use per-conversation locks, not one owner-wide lock.

This is therefore a hybrid single-node availability design: active-active for
HTTP, active-passive for the Zalo event stream, and shared queues for background
workers. Scaling Hermes from one to two replicas improves capacity and process
failover only. On one
host, PostgreSQL, Valkey, Qdrant, OmniRoute, storage, and the Zalo owner remain
single points of failure. Multi-node deployment requires external/shared state
and explicit service HA; see [MULTI_NODE.md](./MULTI_NODE.md).

## Persistence and recovery

- PostgreSQL: durable facts, scoped notes/audit, sessions, workflows, schedules, channel metadata.
- Valkey: short-lived context, locks, queues, rate limits.
- Qdrant: knowledge and conversational vectors.
- `/data/assistant`: documents, staged inbound media, generated artifacts.
- OpenBao: provider/service secrets and durable operational retention values.
- OmniRoute volume/export: accounts, providers, combo order/strategy/history.
- `/data/assistant/backups`: verified recovery stamps.

Lifecycle mutation is backup-gated. `destroy` removes project containers and
networks but retains volumes/data. See [02-commands.md](./02-commands.md).

Authorized Zalo refreshes obtain a complete group roster from the bridge and
replace that group's PostgreSQL member snapshot in one transaction. The API
rejects partial, paginated, malformed, and count-mismatched responses, leaving
the last valid snapshot intact. This makes named-group authorization and
post-restore membership verification independent of transient bridge reads.

## Operational invariants

- Prompt policy is file-based; no request-specific prompt hardcoding in code.
- Provider quota or queue saturation is not reported as a service crash.
- First setup configures only; live probes are run separately.
- Watchers restart only components that fail a component-specific health gate.
- Every live lab captures route/combo evidence, user-visible delivery, latency,
  logs, restart deltas, and semantic/visual self-evaluation.
