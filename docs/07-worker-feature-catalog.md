# Current workers and feature catalog

Current promotion status (2026-09-14 16:21 +07): explicitly authorized by the
user despite known failures; not production certification or a VPS rollout.
Latest complete offline134/134 PASS; VPS15/26 PASS,11unpassed
(4,5,6,7,8,12,16,18,21,22,25). Latest observer refinements have focused checks
only. PDF delivery deadline, strict greeting latency and actual native-client
quoted-file delivery remain open. Older progress snapshots below are historical.

Inventory date: 2026-09-14. This describes the current source candidate, including
unmerged scoped-record, conversion and antivirus changes. It is an architecture
review inventory, **not** a production certification or an activation command.

Fresh follow-up progress is **14/26 VPS gates PASS, 12 unpassed**. Safe private
environment/KV tests and native acknowledged DM/group quoted output pass; the
input quote contexts are injected, not a real-client bubble. The grounding
candidate passes 134/134 offline entries. A later file-gen attribution refinement
is normally deployed and validated, with fresh PDF/offline reruns running. PDF
latency/semantic accuracy, strict greeting latency and native-client quoted-file
delivery remain unpassed. Never rotate invalid lab keys into live operator KV.

Memory indexing uses deterministic UUID point identities across restarts and
accepts finite numeric embeddings only. Compact reports acknowledged upsert
counts, no indexing for an inactive optional backend, and failure for an
unavailable configured embedding. Legacy hashed points are preserved; this
latest candidate fix still requires normal deployment and fresh verification.

Latest follow-up verifies isolated real SQL/vector compact, grounding, repeat
identity and owned retention/cleanup on the rebuilt worker. Deferred messaging
notes are bound to their original request source, keep authenticated target
scope/admin context and record provenance outside user-visible content.
Concurrent requests in one chat cannot consume one another's pending notes.
The normally deployed note follow-up still awaits full offline/background gates.

That follow-up now passes the complete 134-entry offline index and three live
background checks: source-provenanced note content, terminal silence and owned
cleanup. This does not certify the remaining 16 VPS gates or native client quote.

Natural document creation is model-authored through file-gen, not implicitly
dispatched as a literal office shortcut based on its task label. Dispatcher
remains the shared renderer/converter for messaging and standalone sessions.
Exact shortcut artifacts prefer the agent mount path; failed delivery cannot
silently finish or borrow another conversation's output. See the dated audit.

Latest verification: enabled Security Manager antivirus now waits for a
terminal clean verdict rather than accepting `SCANNING`; pending/error/outage
states cannot authorize a file. The rebuilt VPS security matrix passes 5/5,
including actual-engine EICAR rejection with YARA disabled. Other live gates
remain open; see the dated production audit.

## How to read defaults

`active` and `inactive` are canonical feature states. Defaults below mean a
fresh `.env.example` deployed through `run.sh`, not the testing VPS's settings.
An installed skill is available for selection; it does not execute by itself.
Optional services require installation, healthy dependencies and configured
credentials. A flag being active does not prove its feature works.

Source authorities: [.env.example](../.env.example),
[worker resolution](../architect/backup-restore/lib/workers.sh),
[installation catalog](../scripts/main/install-component.sh),
[base Compose](../docker/docker-compose.yml), and its
[media](../docker/docker-compose.media.yml),
[security](../docker/docker-compose.security.yml) and
[edge](../docker/docker-compose.edge.yml) overlays.

## Worker bundles

| Worker / execution layer | Description | Fresh default | Activation and dependencies |
|---|---|---|---|
| Hermes Agent | Native CLI/API/dashboard, model-driven reasoning, tools and skills | active | Core; configured chat provider and authentication |
| Memory Worker | Durable facts, context assembly and scoped notes | active | Core `memory`; source `architect/memory/memory-worker`; Postgres |
| Session | Short-term turns, destination metadata, coordination and attachment receipts | active | Core `session`; Valkey |
| Workflow | Typed request planning, asynchronous job coordination and schedule integration | active | Core `workflow`; Hermes and persistent stores |
| Router Worker | Capability-aware provider proxy, classification/outbound filtering and fallback routing | active | Core `router-worker`; configured OmniRoute combos |
| Knowledge / ingest | Staged learning, extraction, chunking, retrieval and citation catalog | active | Core `ingest` + `embedding`; Qdrant, configured embedding provider |
| Schedule | One-time and recurring execution, named schedules and persisted fire state | inactive | `install schedule`; Postgres, Hermes or configured delivery channel |
| Media / File | Image operations, office authoring, conversion, long jobs and search fallback | inactive | `install media`; Dispatcher, Jobs, jobs-worker, SearXNG |
| Security | File isolation, authorization service, SIEM and policy management | inactive | `install security`; bundles OpenBao/authz/SIEM/policy |
| Notification | Structured alerts and summaries, log/channel fan-out | inactive | `install notify`; notify + alert-watch; channel credentials where used |
| Message / Zalo | Conversation registry, bridge ingress, permissions, queues and channel delivery | inactive | `install message` or `install zalo`; QR login and channel authorization |
| Monitor | Metrics, dashboards, log collection and exporters | inactive | `install monitor`; Grafana, Prometheus, Loki, Alloy and exporters |

OpenBao is **active core secrets infrastructure**, independently of the inactive
full Security worker. The short name `install openbao` currently resolves the
full Security bundle plus OpenBao; it is not a distinct lightweight worker.
Media bundle defaults Jobs, file generation and SearXNG on; Monitor forces its
four monitoring components active. Explicit host configuration can override
some other bundled defaults. `OFFICE_FILE_GEN=active` in the template does not
start the inactive Dispatcher profile by itself.

## All deployed service definitions

Rows enumerate the supported Compose graph once, even when an overlay extends
the same service. These service identifiers are not separate installation tiers.

| Compose service | Responsibility | Fresh effective default |
|---|---|---|
| `hermes` | Agent execution; per-replica homes; native CLI/API/dashboard | active |
| `memory` | Memory Worker and notes API; compatible DNS after source rename | active |
| `session` | Valkey-backed session and delivery coordination | active |
| `workflow` | Request/job orchestration API | active |
| `postgres` | Durable memory, workflow, messaging and schedule data | active |
| `valkey` | Ephemeral state, locks, queues and execution coordination | active |
| `qdrant` | Rebuildable vector knowledge index | active |
| `embedding` | Embedding provider facade | active; provider setup required |
| `ingest` | Knowledge staging, ingest, retrieval and learning | active |
| `router-worker` | Typed model/capability routing and fallback | active |
| `omni-router` | OmniRoute provider/accounts/combos control plane | active |
| `omni-attribution` | Attribution companion for OmniRoute integration | active |
| `traefik` | Local reverse proxy and internal service/bridge routes | active; localhost mode |
| `traefik-acme` | Public ACME/TLS proxy variant | inactive; public mode/domain/email required |
| `api-gateway` | Authenticated API edge and rate limiting | active |
| `openbao` | Secrets source of truth and runtime secret exports | active |
| `schedule-worker` | Go scheduler and persistent scheduled jobs | inactive; Schedule |
| `dispatcher` | Shared image/file authoring/conversion and explicit file delivery | inactive; Media |
| `searxng` | Self-hosted search fallback | inactive; Media or `install searxng` |
| `jobs` | Long-running job admission/status API | inactive; Media or `install jobs` |
| `jobs-worker` | RQ job execution | inactive; Media/Jobs |
| `security-manager` | Static/archive/YARA isolation and optional AV/judge/sandbox | inactive; Security |
| `authz` | Authorization decisions | inactive; Security |
| `siem` | Security event ingestion/query | inactive; Security |
| `policy-center` | Policy management | inactive; Security |
| `clamav` | Malware scanning engine and signature database | inactive; `install antivirus` |
| `av-gateway` | Per-file asynchronous scan verdicts and quarantine | inactive; Antivirus |
| `docker-socket-proxy` | Optional constrained Docker API access for sandbox path | inactive; explicit sandbox opt-in; not production isolation |
| `zalo-proxy` | Docker access to host Zalo bridge | inactive; Message/Zalo |
| `zalo-api` | Channel registry, history, admin and messaging-scope records | inactive; Message/Zalo |
| `notify` | Alert/summary fan-out | inactive; Notification |
| `alert-watch` | Operational alert polling and notification | inactive; Notification |
| `grafana` | Dashboards | inactive; Monitor or `install grafana` |
| `prometheus` | Metrics collection | inactive; Monitor/Prometheus/Grafana |
| `loki` | Central log storage | inactive; Monitor/Loki/Alloy |
| `alloy` | Log collection and shipping | inactive; Monitor/Loki/Alloy |
| `omni-exporter` | OmniRoute metrics | inactive; metrics stack + active OmniRoute |
| `node-exporter` | Host metrics | inactive; Prometheus/Grafana |
| `stack-exporter` | Stack health metrics | inactive; Prometheus/Grafana |
| `clouddrive-sync` | Remote documents mirrored locally by rclone | inactive; configured remote required |
| `openvpn` | Administrative VPN edge | inactive; configuration and PKI required |

There is no separate deployed OCR container: visual reads use the `vision-ocr`
model capability through Router Worker. Image generation is provider-backed,
not a local diffusion/GPU service. Named volumes, profiles and source folders
must not be counted as additional workers.

## User-facing and shared capabilities

| Feature | Description | Default availability / dependency |
|---|---|---|
| Chat and reasoning | Native agent conversation, multi-step planning and task splitting | Core available; usable provider required |
| Classification and outbound filtering | Typed intent/parts, output operation and send/drop control | Core available; classifier/chat combos |
| Coding / debugging / review | Coding, tests, architecture, security review and Git skill families | Skills available; requested tools/repository access required |
| Communication | Tone, translation and Vietnamese terminology guidance | Skills available; on demand |
| Durable memory | Remember facts/preferences and assemble bounded context | Core Memory available |
| Notes CRUD | Generated titles, content/citations, count/list/detail, date/range/keyword and semantic selection | Core Memory; notes skill; semantic selection requires model |
| Scoped notes | Current group/DM or trusted native scope; admin-specific/all reads | Candidate; host authorization; cross-scope all is read-only |
| Schedule CRUD | Named schedules, recent lists/details and scoped edits/deletes | Inactive until Schedule; messaging scopes additionally require registry/authorization |
| Timed/background work | Once-after/at or recurring work; store notes silently when requested | Inactive until Schedule; only explicit user requests create work; not automatic user-job generation |
| Workflow long jobs | Asynchronous multi-step execution and bounded parallel jobs | Core workflow available; execution dependencies required |
| RQ jobs | Background ingest/memory/learning/security queues | Inactive until Media/Jobs; distinct from user schedules |
| Web search/research | Configured OmniRoute web-search combo and SearXNG fallback | Provider route available when configured; local fallback inactive until enabled |
| Website retrieval | Retrieve public accessible sources for research, notes or scheduled work | On demand with configured search/fetch tools; no promise of private Facebook access or bypass |
| Knowledge learning/RAG | Stage, approve, index, search and cite knowledge | Core ingest available; embeddings required; submitted Zalo files remain pending approval |
| Vision/OCR | Image/document visual reads and authorized OCR | Configured `vision-ocr` route; provider credentials required |
| Image generation/editing | Prompt/skill-driven composition and edits; not deterministic legacy overlay layout | Configured image capability; Dispatcher/Image route and model required |
| Image text language | English text inside generated raster images to reduce Vietnamese spelling defects | Image skill policy; native document text follows requested language |
| Document authoring | TXT/Markdown/PDF/DOCX/XLSX/PPTX; native HTML-to-PDF, images/icons and fonts | Inactive until Media; `OFFICE_FILE_GEN=active`; formatted outputs require private preview |
| File conversion | Office-to-PDF, PDF/Office-to-PNG/JPG, image-to-PDF and explicit editable content reflow | Candidate; inactive until Media; file-convert skill; native print dependencies |
| Quote-reply conversion | Exact quoted attachment outranks recall; preserve source content and return requested output only | Candidate Message path; direct path accepts the exact attachment without Zalo |
| Artifact delivery | Selected requested files only; immutable source/destination binding and ACK-backed receipts | Candidate; native files without messaging; Zalo delivery requires Message+Session+bridge |
| Zalo DM/groups | Mention policy, users/groups registry, permissions and reply context | Inactive until Message/Zalo, QR login and authorization |
| Queue/cancellation | Per-conversation FIFO, concurrency controls and explicit active-work cancellation | Zalo queue flag active by default when Message is installed; native execution uses its own control path |
| Alerts/notifications | Structured operational messages and summaries | Inactive until Notification; transport configuration required |
| Metrics/log dashboards | Host/stack/router metrics, centralized logs and visualization | Inactive until Monitor or individual monitor components |
| Backup/restore | Verified backups before lifecycle mutation; explicit restore and retention | Core host tooling available; timers installed by normal lifecycle |
| Cloud backup sync | Explicit backup mirror/sync command using configured rclone remote | Inactive until CloudDrive; separate from scheduled document mirroring |
| Authorization/secrets/security | Authenticated gateway, OpenBao secrets; optional ACL/SIEM/file isolation | Gateway/OpenBao active; full Security inactive |

Features shared by native Hermes and messaging do not depend on a running Zalo
bridge for execution. Their capability workers still must be available. Zalo
permissions, quote wire metadata and channel delivery are transport-specific,
not a prerequisite for core note/image/document/conversion execution.

## Security and integration switches

| Switch / facility | Description | Fresh default / limitation |
|---|---|---|
| `GATEWAY_REQUIRE_AUTH`, `GATEWAY_AUTH_ENABLED` | Authenticated API access | active |
| `GATEWAY_RL_FAIL_CLOSED` | Reject when rate-limit backend cannot enforce policy | active |
| `GATEWAY_TRUST_FORWARDED` | Trust forwarded-client headers | inactive; only trusted proxy topology |
| `SECURITY_YARA` | Signature/static rule checks in Security worker | active policy; worker itself inactive |
| `SECURITY_FAIL_CLOSED` | Isolation outage/error rejection | active policy; affected security paths require worker/config |
| `ENABLE_ANTIVIRUS` | ClamAV/gateway plus required Hermes/Dispatcher scanning | inactive; explicit activation includes fail-closed scans |
| `SECURITY_LLM_JUDGE`, `ENABLE_LLM_JUDGE` | Optional model heuristic may add risk, never authorize unsafe content | inactive; configured model required; not isolation |
| `SECURITY_SANDBOX` | Optional Docker-backed inspection | inactive; not recommended as a production boundary |
| `ENABLE_OPENBAO_AGENT` | Compatibility option for agent integration | inactive; not a separate service in the current graph |
| `TRAEFIK_ACME_ENABLED` / public mode | Public TLS deployment | inactive/local by default; DNS/email/firewall prerequisites |
| `ENABLE_CLOUDDRIVE` | rclone document mirror and explicit backup sync | inactive; configured remote and host mounts |
| `ENABLE_OPENVPN` | Administrative VPN | inactive; valid configuration/PKI |
| Telegram channel pack | Source channel scaffold (`ENABLE_TELEGRAM`) | inactive; scaffold only, no working standalone channel service |
| Notification Telegram/SMS/email hooks | Optional notification transports, separate from a Telegram chat channel | Inactive/unconfigured unless transport credentials/destination supplied |
| WhatsApp/Vault flags | Retired integrations | forced inactive; not activatable supported features |
| Mem0, local OCR engines, ComfyUI/video-generation pins | Removed legacy paths | retired; not dormant capabilities to enable |

Do not interpret “activate all” as disabling authentication, enabling automatic
approval, reviving retired integrations or fabricating missing credentials.
Knowledge auto-learning policy is separate from user-requested background
tasks. `LEARN_REQUIRE_APPROVE` is derived from channel enablement (`ENABLE_ZALO`,
and `scripts/main/install-component.sh` sets it for `message`); scan-based
learning auto-ingests only when the switch is off (`0`/`inactive`), and Zalo
submissions are always staged pending regardless. This policy deserves an
explicit architecture/security review, not a silent approval-policy change.

## Host maintenance tasks

These are systemd timers installed by normal `run.sh` lifecycle, not extra
Compose workers or user background requests. Times use the configured host zone.

| Timer | Description | Installed default |
|---|---|---|
| `assistant-auto-learn.timer` | Scan configured knowledge/media roots | active; daily 00:00; ingest/learning policy applies |
| `assistant-backup.timer` | Scheduled backup | active; daily 00:30 |
| `assistant-stack-watch.timer` | Health/self-heal for enabled services | active; every 2 minutes |
| `assistant-log-archive.timer` | Retained log archive | active when `ENABLE_LOG_ARCHIVE` (default active); 01:15 |
| `assistant-zalo-watch.timer` | Bridge/SSE self-heal | inactive until Zalo active; every minute |
| `assistant-compact.timer` | Daily memory housekeeping (compact staged drafts + reindex) | active (core); daily 00:00 |

Timer installation needs systemd/sudo. A Compose-only light start does not prove
timers are installed. `UPDATE_AGGRESSIVE_PRUNE` defaults inactive; lifecycle
destruction keeps volumes/data and requires verified backups.

## Testing VPS checkpoint, not repository defaults

At the continued 2026-09-14 lab, all six optional worker bundles were already
active. Antivirus was subsequently activated through normal backup+verify
installation; both Hermes replicas and Dispatcher have `AV_SCAN=active` and
`AV_REQUIRED=active`. Six live AV checks pass, including EICAR, rejection
before conversion and an unavailable-scanner fail-closed check. Eight activation
regressions and twelve native conversion
cases pass, including PDF/PPTX-to-image. Two fresh quote-only conversion cases
return exactly one file each without completion text.

CloudDrive lacks its remote configuration; OpenVPN lacks configuration/PKI;
Telegram is a scaffold and has no configured token. Sandbox and LLM judge are
separate security opt-ins, not default production protections. Provider vision
authentication/quota issues remain in the release audit. Both later semantic
exclusion cases pass and the delivered one-page PDF passes visual review; the
PPTX fails on late extra text and scope expansion pending its core-fix rerun.
Another PDF run exposed pre-ACK private-review chatter. Typed artifact-only
delivery and workflow timeout fencing now have seven focused regressions;
fresh terminal-delivery reruns remain required. Document review jobs default to
`ZALO_WORKFLOW_DOCUMENT_TIMEOUT_S=900`; ordinary jobs retain 420 seconds.
The offline index passes 134/134. Standalone notes also pass 4/4 with messaging
disabled and its URLs unreachable in the test child process. No blanket
all-features-pass or merge is claimed.
The next receipt-aware PDF run returns one file without chatter and passes
all-page visual/native-language inspection. Direct delayed scheduling passes
2/2. Current monitoring service-label and fail-closed gauge checks pass.
The subsequent PPTX delivers one selected file only and all three native preview
pages pass visual, language and request-scope inspection. Both final document
checksums match acknowledged bridge echoes. Eight source-binding/result-only
regressions and the latest full 134/134 offline rerun pass after deploying the
typed-document shared-directory discovery guard. Conversational conversions,
native quote bubbles and the broader clean-deployment matrix are separate gates.

The AV gateway now caps file size (50 MiB), retained queued/scanning bytes
(128 MiB), queue (16), sessions (2,048) and session files (64), with completed
records expiring after one hour. Concurrent multipart parsing is bounded and
oversize/chunked bodies fail before parsing; scanner exceptions block but do
not kill the worker. See the gateway README for canonical tuning variables.

## Architecture revision checklist

- Separate execution capabilities, channel adapters, model provider plane,
  persistent stores and host maintenance ownership.
- Preserve compatible service names when changing component source names.
- Distinguish a worker's activation from policy defaults and provider readiness.
- Review optional security boundaries, scan resource limits and learning policy.
- Keep conversion fidelity explicit: native print/raster versus editable reflow.
- Define recovery/reconciliation for ambiguous delivery receipts; no blind resend.
- Require actual native page/slide review and channel-independent live tests.

Verification contract: [test/README.md](../test/README.md). Open evidence:
[production audit](../history/2026-09-14/production-gap-audit.md).
