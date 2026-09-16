# Verification

This is the release-verification contract and test index for the stack. It
combines the verification rules (outcomes, capability cases, gates, merge gate)
and the invariant registry (invariant-first coverage index).

## Layout

| Path | Purpose |
|---|---|
| `README.md` | Verification contract + invariant registry + gap-cases index (this file). |
| `cases/` | Durable scenario specifications and historical gap cases. |
| `scripts/` | Offline units and authorized lab drivers. |
| `reports/` | Sanitized generated evidence; never credentials or personal identifiers. |
| `REPORT.md` | Index of run summaries (update after completing test cases). |

From-scratch setup and recovery live with the operator rules
(`rule/SETUP.local.md`).

Run the batch gate with `test/scripts/run_case_index_lab.py`. It discovers all
`*_unit.py` files, then runs the curated live list unless `SKIP_VPS=1` is set.
A successful process or assertion is insufficient for Zalo/media/office cases:
the delivered reply or artifact must also be inspected and rated.

The current Zalo HA model has one Valkey-elected SSE owner. Different DM/group
conversations may execute concurrently; one conversation stays FIFO ordered.
Claimed queue items are acknowledged only at a terminal turn and are recovered
by a promoted owner after a process loss.

---

# Hermes Stack verification contract

This file is the source of truth for repository and VPS release verification.
Tests prove the live user outcome and route; an assertion alone is not proof.

Activation checks include `test/scripts/feature_activation_unit.py` (canonical
active/inactive flags, both senders' required AV wiring, scanner outage cannot
bypass parsing). `file_convert_unit.py` includes all-slide PPTX-to-PNG and
all-page PDF-to-JPG plus selected-page PNG, page order and native aspect ratio.
Live antivirus proof requires ClamAV ready, clean/EICAR verdicts and required
scanner-outage rejection; a running container alone is insufficient.
`antivirus_capacity_unit.py` additionally exercises multipart admission before
spooling, file/queue/byte/session caps, basename containment, completed-record
retention, bounded upload reads and worker survival after scanner exceptions.
Live AV capacity checks must verify HTTP 411/413 without parsing, normal clean
uploads still reach a clean verdict, and required scanner failure still blocks.

## 1. Safety and test identity

- Read `rule/AGENT_RULES.md`, `rule/BE_RULE.md`, `rule/GIT.md`,
  `rule/TEST_STRATEGY.md`, `docs/CHANGELOG.md`, `docs/HISTORY.md`, and `history/`
  before a lab.
- Use only the designated test VPS and operator-authorized Zalo account.
- Supply the user identity at runtime as `ZALO_TEST_USER_ID`. Never commit a
  numeric Zalo identity or print authentication tokens.
- Back up and verify Zalo state, OpenBao, and OmniRoute configuration before
  destructive lifecycle testing. Reports record checksums/counts, not secrets.
- First setup is setup-only: no test traffic, temporary patch, or generated
  media. Tests begin after setup completes.
- Do not change AI Box accounts, provider members, combo ordering, or strategy
  during an update test. Export before/after and compare.
- Temporary artifacts go under `scripts/temp/` or the lab report directory and
  are removed when the run completes. Remove Python caches from core source.
- VPS-local fixture transfer must atomically replace a stale destination rather
  than truncate it in place, because prior sudo-backed runs may leave an
  unwritable file inside an intentionally writable temporary lab directory.

## 2. Outcomes

Environment/OpenBao labs use private owned directories/KV paths, real shared
load/scrub helpers and an isolated consumer. Never seed an invalid test key
into live operator KV or overwrite production env to test rotation. Confirm
owned cleanup and unchanged live KV/token/files/consumer env before PASS.
Policy-refusal gates count the actual host policy result even when tagged
`delivery_kind=gate`; semantic review distinguishes it from process chatter.
Quote concurrency requires real cached native CLI identity, exact replies,
native acknowledged `quoted=true` and terminal settlement. Label injected input
contexts separately from a real-client input quote bubble. PDF quality includes
source-grounded condition/category and model-versus-measurement attribution;
fonts and visual polish alone are not factual verification. Preserve timing
FAIL when an artifact arrives after the declared limit.
Gateway startup-buffered events are pending work, not terminal idle, even if
their initial adapter callback already returned. Verify delayed replay and
timeout cancellation: only the owned buffered event is removed/fenced; sibling
jobs and later requests remain runnable. Native startup logs must not show a
workflow completed before its replayed agent started.

| Result | Meaning |
|---|---|
| `PASS` | Route evidence, final artifact/reply, semantic evaluation, and relevant logs all satisfy the case. |
| `FAIL` | Product behavior, delivery, correctness, layout, concurrency, or stability is wrong. |
| `SKIP` | A free-provider quota/capability block is proven in logs; never use SKIP for a code/runtime defect. |
| `BLOCKED` | Required authorization or external state is unavailable. |

Never relabel a failed live test as pass. Every report includes exact timestamps,
commit SHA, replica count, correlation IDs, combo/model attribution, elapsed
time, restart deltas, and sanitized evidence.

Transport delivery evidence must be an acknowledgement-backed durable
`delivered` event. A queued `assistant_turn`, generated file, log intention, or
optional bridge self-message echo is not proof that Zalo accepted the result.

Gateway approval prompts are control-plane messages. When a gateway marks a
send with `is_approval_prompt`, the Zalo adapter must deliver it through the
normal secret and egress guards while bypassing assistant process-narration and
post-media muting. A filtered prompt reported as successfully delivered is a
failure because it leaves the tool waiting for consent the user cannot provide.

## 3. Two-phase release gate

### Phase A — local/static

1. Confirm current architecture docs agree with compose and `run.sh`.
2. Search current code/docs for retired 9Router, legacy OmniRouter, local OCR,
   ComfyUI, video-gen/video-edit, and retired secret aliases. Historical
   changelogs may retain them as dated history.
3. Run syntax, unit, classify-contract, media-policy, Zalo queue, backup,
   OpenBao, and documentation-link checks.
4. Confirm no numeric Zalo identity, secret, Python cache, or ad-hoc patch file
   is committed.

### Phase B — clean VPS deployment

1. Capture baseline services, workers, timers, restart counters, disk/memory,
   recent container logs, Zalo journal, OmniRoute logs/history, and watcher logs.
2. Run `bash run.sh backup` and `bash run.sh verify`; verify Zalo and OmniRoute
   components without exposing their contents.
3. Run `bash run.sh destroy`, then `bash run.sh up`. Volumes and
   `/data/assistant` remain. Restore enabled workers from the retained supported
   configuration and validate service-specific health.
4. Prove Zalo identity/session and OmniRoute provider/combo configuration match
   the pre-destroy backup.
5. Prove the Zalo path is bridge → proxy → Traefik → Valkey-elected Hermes
   owner. Stop the active owner and verify a standby acquires after the bounded
   lease interval without duplicate delivery or restarting every replica.
   Kill an owner after it claims a queued item and prove the promoted owner
   recovers the inflight item before later items in that conversation.
6. Execute the capability cases below through the Zalo plugin and confirm the
   operator sees every expected result in Zalo.
7. Repeat the concurrency workload with `HERMES_REPLICAS=1` and `2` using the
   same prompts/fixtures; compare latency, throughput, routing, restarts, and
   resource pressure.
8. Re-read logs and restore the requested final replica count. Clean temporary
   files and caches.

## 4. Capability cases

Fixtures come from `D:\Onedrive\Work\test docs`. Copy only the case inputs to a
sanitized VPS lab directory; do not modify the source fixture directory.

### C1 — image generation (`image-gen`)

Send a natural-language still-image request through Zalo. Require:

- classify selects image generation and OmniRoute records requested combo
  `image-gen`;
- one viewable image is delivered to Zalo within the image operation deadline
  (maximum five minutes);
- when text is requested, generated-image informational copy defaults to English
  even for a Vietnamese question; an explicit image-text language or exact quoted
  copy overrides that default. Native document text and chat replies keep the
  requested language. Require correct spelling and OCR plus visual inspection;
- for a multi-subject request, every independently sourced subject is present
  exactly once and every explicit spatial relationship is preserved;
- treat an explicitly requested shared region as one visual group even when it
  contains several independently sourced subjects. Subject count must not
  silently become panel count, and payload adaptation must preserve every
  validated fact rather than truncating to a legacy line limit;
- exercise both a shared bottom information bar and a shared left-side frame
  with current weather plus fuel prices. Require the complete facts in the
  requested language, the requested placement, one cohesive background, and no
  hard-coded split-panel fallback. A bottom band is content-sized by default
  and must leave meaningful scene visible beside it; it may cover the full
  width only when the request explicitly requires full width;
- exercise at least one named grid arrangement, one repeated-side arrangement,
  and one normalized custom-region arrangement. Unspecified regions must be
  distributed without overlap; no panel may cover another panel or essential
  requested scene content;
- the scene, composition, typography, contrast, and requested facts are scored,
  not merely file existence.
- Include the requested locale, a readable compact-font request, and highlighted
  key values. Inspect diacritics, phone-size readability, meaningful measurement
  labels, and scene clearance. A successful valid image must not invoke ordinary
  runtime OCR/vision or aesthetic re-generation; release-test visual review is
  explicit and separate. Provider failover remains for transport/decode failures.

### C2 — vision analysis (`vision-ocr`)

Send at least one image containing text and one image without text. Ask the LLM
to analyze naturally rather than force a fixed OCR template. Require route
evidence for `vision-ocr`, accurate description/transcription where applicable,
uncertainty for unreadable content, and one user-visible answer per input.

### C3 — optimize/compact memory and knowledge

Seed a unique non-secret fact/document, invoke both supported optimization
paths, and prove embedding calls use combo `embedding`. Verify useful recall
before/after, no silent data loss, collection/schema compatibility, bounded
resource usage, and no unrelated conversation leakage.

### C4 — web search (`web-search`)

Ask a time-sensitive question whose answer can be independently checked.
Require route attribution to `web-search`, current sources/links, agreement
between cited sources and answer, and no fabricated citation. A provider quota
may be skipped only when an alternate member also cannot serve and logs prove
the external limit. Each typed current-data request must make a fresh native
search call in the same turn. Reusing a prior answer or substituting code,
shell, or direct language HTTP calls fails the route even if the prose looks
plausible.

Also exercise a multi-source public-web gather across different site types.
Require search first, page extraction when snippets are insufficient,
source-correlated concrete records, cross-provider deduplication, honest
handling of private/login-blocked pages, and no invented crawl results. Repeat
the same gather through a scheduled background note flow to prove the runtime
uses current search results rather than creation-time history.

### C5 — embedding API (`embedding`)

Submit known related/unrelated strings through the live embedding path. Require
correct vector shape, finite values, related-pair similarity above unrelated
pairs, `embedding` combo attribution, and no fallback to a chat combo.

### C6 — document and archive analysis

Use representative PDF, DOCX, PPTX, XLSX, text, image, and compressed fixtures.
Require safe extraction limits, traversal/bomb defenses, natural analysis via
`vision-ocr` where visual reading is needed, accurate file enumeration, and no
server paths or extracted secrets in the Zalo reply. Unsupported/corrupt files
must fail clearly without crashing workers.

### C7 — scheduler

Schedule one harmless result for no more than two minutes in the future. A
simple reminder must be stored and delivered as verbatim standalone content;
it must not be converted into generated work or a follow-up question. Require
exactly one acknowledgement, durable row, one execution, and one final
transport-accepted delivery whose `source_message_id` correlates to that
schedule row. Also require the correct timezone and no duplicate after a
worker or Hermes restart. Remove the test schedule and row afterward.

For scheduled image work, persist the full original intent instead of reducing
it to a text reminder. Run the same adaptive weather-and-fuel composition used
by C1 with a near-future deadline and require the scheduled artifact to retain
the shared-region placement, facts, language, single-scene requirement, and
source-correlated image delivery.

Every test-created schedule must include an opaque source marker and be deleted
in a cleanup boundary on pass, failure, or timeout. A later live case must never
observe a delayed fire left behind by an earlier harness.

Schedule a near-future process whose fire text is an explicit search-then-note
ask (for example find public Java backend jobs then note them). Without an
explicit result-delivery request, require one fire, Memory rows retaining source
URLs, and zero fire-time chat messages. With explicit result delivery, require
one gather listing and one host note-save confirmation without duplicate work.
Delete the schedule afterward.

Also cover a recurring background gather at several clocks (for example
06:00, 12:00, and 18:00) with `notify_on_fire=false`. Require a concise stored
schedule title, one fresh routed search per fire, durable titled notes with
citations, and no chat delivery from the fire. Listing defaults to the ten
newest schedules by time/title; inspecting one selected schedule returns its
full fire content and lifecycle fields without internal context JSON.

### C8 — image edit, including Zalo reply quote

Send an image, then reply-quote that message with a natural edit instruction.
Require quoted attachment resolution, route attribution to `image-edit`, a
visibly edited output that preserves unrequested content, and delivery to the
same conversation. Fail if the source image is guessed from global recent
state, the original is returned unchanged, or only routing is proven.

### C9 — professional office artifacts

Generate one PDF, DOCX, PPTX, and XLSX from the same small content brief.
Require accurate content plus visual QA from rendered pages/slides/sheets:
hierarchy, margins, alignment, contrast, readable typography, tables/charts,
page breaks, clipping/overflow, localization, and consistent style. “File
opens” is insufficient. Use the repository document skills and their
render-and-inspect workflow.

External design references must be reviewed for license before reuse. Research
may use high-signal repositories such as `anthropics/skills` and
`hugohe3/ppt-master`; learn from their workflows, but do not vendor unlicensed
or incompatible code/assets.

Repeat the PDF case with several explicitly positioned subjects. Ordinary
document content must preserve the requested row/column/edge relationships in
safe normal flow. When the request explicitly requires copy over an embedded
image, require one dispatcher-composed image with all requested regions, embed
only that final image, and reject overlap, missing regions, risky absolute CSS,
or separately delivered intermediate images.

When Dispatcher has already delivered and claimed a final PDF or Office file,
adapter late-autosend must stop at that claimed document and must not expose an
older embedded image as another attachment. Filesystem sidecars are diagnostic;
the release oracle fails on an acknowledgement-backed image delivery correlated
to the document-only source request.

For a requested three-slide PPTX, require exactly one PPTX delivery, exactly
three rendered slides, at least one embedded scenic image, and model-authored
slide structure/layout through file-gen directives. Reject PDF substitutions,
separate intermediate-image delivery, repeated title-only slides, empty
backgrounds, clipped text, or a fixed topic-specific template.

Replica startup must retain the repository root `pdf`, `docx`, and `xlsx`
wrapper directories and add the bundled names to `.curator_suppressed` before
image-level skill sync. Their frontmatter names remain distinct and route chat
creation to `file-gen`; categorized and official clones are removed. The live
oracle must match the positive `NEW_PDF` line exactly, never treat `NO_NEW_PDF`
as success, query durable image delivery even when no document appears before
the deadline, and fail closed if that audit is unavailable. For a current-only
request, it must reject forecast, probability, or advice sections. Its rendered
page judge must report at least 8/10 and no blocking overlap, clipping,
unreadable text, broken hierarchy, or materially wasted space.

For composed images with several information regions, also reject an empty or
truncated structured composition plan. The live gate must observe a complete
planner response before accepting generated-file and delivery evidence.

### C10 — multipurpose notes, session history, RAG, and cancellation

Create dated and undated notes for at least three unrelated subjects (for
example a plan, an idea, and a personal checklist). Require DM/user and group
scopes to remain isolated, exact-date lookup to use the indexed note date,
topic lookup to return the correct stored content, duplicate create to dedupe,
and update/delete to write an audit version. An ambiguous mutation must ask for
selection and must not change data.

Every new note has a concise model-authored title, including content-only
notes. A default/date/date-range/keyword list shows at most the ten newest
matches as date + title without dumping bodies; a count request returns only a
compact count; a selected detail returns title, full content, and citations.
Explicit whole-scope delete must remove every scoped note, while date-range or
keyword bulk update/delete requires classifier `bulk=true`; a non-bulk
multi-match remains ambiguous. Verify audit versions and DM/group isolation for
all mutations.

Search-then-note (find live web facts, then note them) must stay one atomic
turn: exactly one gather listing and one host save confirmation; zero workflow
「Đang xử lý」 second listing for the same user message. Stored notes created
from web gathers must retain citation URLs (`http`/`https`) for the sources
used; bodies must not contain agent storage-disclaimer commentary. For
deferred writes, verify host-owned original-source provenance and two concurrent
pending note requests in one chat; neither request may consume/clear the other.
Retain authenticated specific-group/DM selector and admin context through gather
and save. Silent scheduled fixture cleanup must use original-source provenance,
not a model-produced marker alone; identifiers explicitly requested by the user
must still be retained in note content. Keep concise title and details separate.
For recruitment gathers, the notes/web-search skills require concrete openings
(`Title — Employer`), forbid aggregate count buckets, and omit openings already
present when Prior notes are supplied; the host must not implement that policy
via user-text regex.

Verify short-term session history survives a Hermes replica replacement and
that durable RAG recall remains grounded after compact/embedding reindex. Reset
the session and prove archived history is traceable without leaking another
thread's content.

During a deliberately long request, send an explicit stop message and repeat
with a quote-reply in both an authorized DM and group. The control request must
bypass rate/FIFO admission, cancel only the active turn in that thread, record
`cancel_requested` then `cancelled`, suppress late delivery, release ownership,
and allow the next queued request to complete. If no work is active, require an
accurate no-active response rather than a false success.
The user-facing stop acknowledgement must not expose a process/container ID,
task or message identifier, correlation value, queue key, or other internal
execution handle.
An unauthorized sender, disallowed group, unaddressed group message, or group
with control disabled must not reach semantic cancellation or stop another
user's active turn.

### C11 — continuous-message ordering and conversational continuity

Send at least four natural messages consecutively to one DM without waiting for
the previous response. Include one direct request, one reply quoting the bot's
answer, one short contextual follow-up that omits an entity already established
by the quoted/prior turn, and one unrelated request. Repeat the sequence in an
authorized group while correctly addressing the bot.

Require every accepted message to produce exactly one terminal outcome in FIFO
order. Each response must remain correlated with its own source queue item,
retain the correct source-tagged user text in session history, use quoted and
recent context without an unnecessary clarification, and keep unrelated
requests independent. Native quote transport must be verified with genuine
Zalo message identifiers; an injection lab may verify quoted-context semantics
and successful plain fallback but must not claim native quote-bubble proof.
Fail on crossed sources, duplicate or missing replies, context taken from a
later message, a timeout notice after a valid result, late output from an
earlier turn, queue residue, or leakage between DM and group scopes.

After an attachment case, send an unrelated URL, image-generation, schedule,
or document-creation request in the same conversation. The fresh request must
not inherit the old extract. A text-only attachment follow-up must contain an
explicit file/sheet/image/archive back-reference (or be a short unambiguous
elliptical follow-up) before recall is hydrated. Archive injection must use the
real single-media shape and its case must wait for a non-busy, exact-source
terminal reply before later concurrency cases begin.

Run a second burst while the first item is intentionally slow. Verify queue
depth grows within its configured bound, the elected owner renews its lease,
later items remain durable, and completion or cancellation of the first item
allows the remaining items to drain in order. Record admission-to-delivery
latency for every item rather than reporting only total runtime.

### C12 — ten-million-record memory scale

Generate an isolated, disposable corpus of exactly 10,000,000 records on the
production PostgreSQL engine. Do not commit or retain the generated data. Use
the same full-text, conversation, session, and time predicates/index families
as Memory Worker.

Measure two independently marked needles: one knowledge/RAG fact and one task
from a specifically named old session. Require exact content and scope matches,
an indexed query plan, individual execution latency within the configured
production budget, and zero cross-session substitution. Report corpus size and
both measured latencies. Always drop the lab table in cleanup, including after
a failed assertion.

## 5. Two-request concurrency and quote isolation

Run exactly two concurrent Zalo requests for the designated test identity:

1. reply-quoted image edit using a known source image;
2. a different capability from C1–C7 with a unique marker.

Both requests must retain their own correlation ID, quoted/source attachment,
acknowledgement, final result, and ordering. Fail on swapped media, cross-talk,
duplicate sends, missing final delivery, shared temporary filenames, or one
request blocking the other beyond its operation deadline.

Record wall-clock completion for the pair with one and two Hermes replicas.
Report median/tail latency only from observed samples; do not claim scaling
benefit when provider latency dominates or the sample is too small.

Also run one DM request and one request in the named three-member test group at
the same instant. Resolve the group by display name at runtime, verify its
membership through durable channel state, and require each result to return to
its originating conversation. Numeric identities must remain runtime-only.
The elected owner serializes gateway agent execution per conversation while
allowing independent conversations to run concurrently. It must retain both
durable claims, pulse worker ownership while waiting, acknowledge only after
terminal session completion, and deliver both within their operation deadlines.

Run two additional capability bursts with
`test/scripts/zalo_dm_group_capability_concurrency_lab.py`. Each burst admits
exactly one DM and one addressed group request simultaneously:

1. current-weather searches for different cities, with independent
   source-message correlations, current-condition semantics, independent
   evaluation, and `web-search` combo attribution;
2. DOCX creation with distinct titles and exact body markers, followed by
   acknowledged attachment correlation and package-content inspection.

These bursts must not use quote replies as a substitute for executing the real
search and file-generation paths. See
`test/cases/76-zalo-dm-group-capability-concurrency.md`.

## 6. Stability observation

Before and after every live set, capture:

```bash
docker compose ps
docker compose logs --since 15m hermes router-worker omni-router
journalctl --user -u com.hermes.zaloplugin --since '15 minutes ago'
systemctl --user status com.hermes.zaloplugin
systemctl list-timers 'assistant-*'
```

After any lifecycle test that restarts the active Zalo owner, wait until bridge
health reports both a logged-in session and at least one SSE consumer before
injecting the next test event. HTTP acceptance without a live consumer is not
message-delivery evidence.

Include dispatcher/jobs, schedule-worker, Valkey/PostgreSQL/Qdrant, and stack/
alert watchers when used. Distinguish:

- provider quota, queue saturation, or slow generation;
- deadlocked/blocked local request handling;
- health-check mismatch;
- memory/CPU/disk pressure;
- restart-policy/watchdog loops;
- Zalo session loss, duplicate ownership, or send failure.

Any unexpected restart, unbounded queue growth, missed reply, wrong quote, or
continuous watcher recovery blocks release until its core cause is fixed and
the full affected case is rerun.

## 7. Merge gate

### Affected conversion and standalone gates

Run `production_delivery_unit.py`, `artifact_delivery_unit.py` and
`adapter_delivery_unit.py` before live affected-path tests. They cover filename
confinement, immutable recipients/source identity, byte-content isolation,
failed-claim recovery, definite rejection versus ambiguous wire outcomes, and
actual bridge acknowledgements. Repeat the shared protocol inside Session with
`--live-session` to prove real Valkey atomic ownership and exact fixture cleanup.
Do not relabel deterministic core failures as provider quota skips.

1. Run `file_convert_unit.py` in the Dispatcher runtime: real Office print
   engines, selected slide/page rasterization, all-sheet editable reflow,
   inert formula-like imports, invalid/unsafe inputs and security denial.
   Run `file_conversion_security_unit.py` for active-content/archive variants.
2. Through actual user attachment routing, convert PPTX to PDF and selected PDF
   pages to images. Inspect every actual output and terminal delivery audit;
   no source or intermediate artifact may be a sibling attachment.
   Run `quote_file_conversion_unit.py` and the quote-only cases in
   `file_conversion_smoke_lab.py`: reply to an acknowledged PPTX with
   "convert this PPTX file to PDF", and to a workbook with a Vietnamese
   conversion request. Use the real quoted message ID with no direct media,
   preserve all slides/sheets, verify the exact source contents and one terminal
   requested delivery. Record native quote-bubble evidence separately; an
   invented quote ID or correct filename alone is not PASS. Missing/inaccessible
   quoted files must never silently fall back to an unrelated recent attachment.
3. Convert a multiple-sheet workbook to DOCX with explicit content-reflow
   consent; preserve every populated section/cell without claiming original
   chart/layout/formula fidelity. Scanned PDF to editable output must use
   authorized OCR or fail honestly, never return blank success.
4. Run `standalone_schedule_smoke_lab.py` and `standalone_notes_smoke_lab.py`:
   actual short-delay Hermes execution and durable scoped note CRUD, without
   inventing a messaging destination. Remove exact fixtures after terminal work.
5. Run `scoped_records_smoke_lab.py` against authenticated channel registry,
   Memory and Schedule services. Verify group/DM/all boundaries and ordinary
   principal denial; no impersonated real user or broad deletion is permitted.

Open/merge release requests only when explicitly authorized and every required
case is PASS or an evidenced provider-only SKIP accepted by the decision. Use a
feature branch into `develop`; then create a release branch from current
`main`, bring only the verified changes, and merge its request into `main`.
Inspect other open requests, keep the newest compatible fix when changes
conflict, and never merge stale superseded behavior.

---

# Invariant registry (TEST_STRATEGY)

This repository implements the `rule/TEST_STRATEGY.md` structure with its own
convention instead of a literal `tests/` tree:

- **`test/scripts/*.py`** — offline units executed by
  `test/scripts/run_case_index_lab.py` (it prints `running test case N/M`).
- **`test/cases/*.md`** — scenario cases (some VPS/live, some offline).

Each invariant below maps to existing evidence. `COVERED` means at least one
automated test proves it; `PARTIAL` means partial evidence or a gap case exists;
`GAP` means no automated test yet. Test count is not coverage.

| Invariant | Statement | Category | Coverage | Evidence |
|-----------|-----------|----------|----------|----------|
| INV-CONV-001 | Messages within a conversation preserve FIFO ordering | conversation | COVERED | `test/scripts/queue_fifo_recovery_unit.py`; `test/scripts/inbound_queue_unit.py`; `test/cases/54-gap-queue-ordering-fairness.md` |
| INV-CONV-002 | A message cannot be processed twice | conversation | COVERED | `test/scripts/zalo_claim_unit.py`; `test/cases/42-gap-duplicate-delivery-idempotency.md` |
| INV-CONV-003 | Concurrent conversations cannot corrupt each other | conversation | PARTIAL | `test/scripts/zalo_scope_authz_unit.py`; `test/cases/76-zalo-dm-group-capability-concurrency.md` |
| INV-QUEUE-001 | A queued task is eventually processed or marked failed | queue | COVERED | `test/scripts/queue_fifo_recovery_unit.py`; `test/scripts/inbound_queue_unit.py`; `test/cases/23-zalo-inbound-queue.md` |
| INV-QUEUE-002 | Worker failure must not silently lose a task | queue | COVERED | `test/scripts/queue_fifo_recovery_unit.py`; `test/scripts/zalo_queue_session_timeout_unit.py`; `test/cases/23-zalo-inbound-queue.md` |
| INV-SEC-001 | Untrusted paths cannot escape the allowed workspace | security | COVERED | `test/scripts/archive_member_path_unit.py`; `test/scripts/fixture_paths_unit.py`; `test/cases/19-file-pipeline-security.md` |
| INV-SEC-002 | SSRF prevents access to prohibited network targets | security | COVERED | `test/scripts/ssrf_guard_unit.py` |
| INV-SEC-003 | Archive processing stays within security/resource boundaries | security | COVERED | `test/scripts/archive_member_path_unit.py`; `test/scripts/archive_media_only_unit.py`; `test/scripts/archive_host_ack_wait_unit.py`; `test/scripts/quote_folder_archive_unit.py` |
| INV-SEC-004 | Untrusted content cannot override platform controls | security | PARTIAL | `test/cases/64-gap-prompt-injection-through-every-data-boundary.md` |
| INV-SEC-005 | Protected secrets are not disclosed to users/tools/files | security | COVERED | `test/scripts/secret_probe_unit.py`; `test/scripts/secret_probe_path_unit.py`; `test/scripts/learn_skip_secret_unit.py`; `test/scripts/user_secret_ask_blob_unit.py` |
| INV-SEC-006 | Untrusted executables cannot bypass attachment security | security | PARTIAL | `test/scripts/archive_member_path_unit.py`; `test/scripts/antivirus_capacity_unit.py`; `test/cases/32-secret-probe-path-eicar.md` |
| INV-SEC-007 | Untrusted workloads cannot exhaust protected resources | security | PARTIAL | `test/scripts/archive_member_path_unit.py`; `test/scripts/antivirus_capacity_unit.py` |
| INV-MEM-001 | Required conversation continuity survives worker recreation | memory | COVERED | `test/scripts/session_idle_rollover_unit.py`; `test/scripts/memory_recall_index_unit.py` |
| INV-ROUTER-001 | Fallback routing cannot bypass security or policy gates | router | PARTIAL | `test/scripts/router_worker_fallback_unit.py`; `test/scripts/router_worker_identity_unit.py` |
| INV-FAIL-001 | Injected dependency failure does not lose/duplicate/corrupt work | failure_injection | PARTIAL | `test/cases/74-gap-failure-injection-coverage-gate.md` |

## Remaining coverage gaps

- FIFO under a live Valkey reconnect/failover (in-process FIFO ordering and
  worker-failure recovery are now covered by `queue_fifo_recovery_unit.py`).
- Symlink traversal combined with nested archives against the workspace guard
  (INV-SEC-001; plain/absolute/relative/backslash member traversal is covered).
- Prompt-injection regression corpus executed as automated assertions
  (INV-SEC-004).
- Executable-attachment MIME/type-mismatch matrix (INV-SEC-006).
- Failure-injection matrix (router/queue/worker/db/redis/zalo/omnirouter/network)
  as automated units (INV-FAIL-001).

## How to extend

1. Pick an invariant row; add `PARTIAL`/`GAP` evidence under `test/scripts/` or
   `test/cases/`.
2. Reference it in the `Evidence` column so this registry stays the index.
3. Run `python test/scripts/invariant_registry_unit.py` and the affected units.

---

## Gap cases index (production failure matrix, cases 40–74)

Source: operator gap matrix extending cases 01–37.

Lab scripts that need a Zalo user must inject as allowlisted **Tn** via bridge /inject-event (id from host allowlist — never commit).

| Case | File | Title |
|------|------|-------|
| 40 | 40-gap-dependency-failure-matrix.md | Dependency Failure Matrix |
| 41 | 41-gap-restart-during-in-flight-request.md | Restart During In-Flight Request |
| 42 | 42-gap-duplicate-delivery-idempotency.md | Duplicate Delivery / Idempotency |
| 43 | 43-gap-outbox-lease-recovery.md | Outbox / Lease Recovery |
| 44 | 44-gap-poison-job-permanently-failing-job.md | Poison Job / Permanently Failing Job |
| 45 | 45-gap-retry-storm-backoff.md | Retry Storm / Backoff |
| 46 | 46-gap-malformed-llm-response-matrix.md | Malformed LLM Response Matrix |
| 47 | 47-gap-omniroute-combo-failure.md | OmniRoute Combo Failure |
| 48 | 48-gap-valkey-failure-session-consistency.md | Valkey Failure / Session Consistency |
| 49 | 49-gap-postgresql-failure-memory-write-race.md | PostgreSQL Failure / Memory Write Race |
| 50 | 50-gap-qdrant-failure-knowledge-consistency.md | Qdrant Failure / Knowledge Consistency |
| 51 | 51-gap-attachment-pipeline-partial-failure.md | Attachment Pipeline Partial Failure |
| 52 | 52-gap-ocr-false-positive-blind-vision-regression.md | OCR False-Positive / Blind Vision Regression |
| 53 | 53-gap-watchdog-false-positive.md | Watchdog False Positive |
| 54 | 54-gap-queue-ordering-fairness.md | Queue Ordering / Fairness |
| 55 | 55-gap-zalo-sse-disconnect-reconnect.md | Zalo SSE Disconnect / Reconnect |
| 56 | 56-gap-zalo-outbound-failure-after-successful-processing.md | Zalo Outbound Failure After Successful Processing |
| 57 | 57-gap-schedule-crash-boundary.md | Schedule Crash Boundary |
| 58 | 58-gap-schedule-time-boundary-clock-anomalies.md | Schedule Time Boundary / Clock Anomalies |
| 59 | 59-gap-backup-corruption-partial-backup.md | Backup Corruption / Partial Backup |
| 60 | 60-gap-disk-full-resource-exhaustion.md | Disk Full / Resource Exhaustion |
| 61 | 61-gap-permission-ownership-drift.md | Permission / Ownership Drift |
| 62 | 62-gap-configuration-corruption.md | Configuration Corruption |
| 63 | 63-gap-public-local-security-regression.md | Public / Local Security Regression |
| 64 | 64-gap-prompt-injection-through-every-data-boundary.md | Prompt Injection Through Every Data Boundary |
| 65 | 65-gap-cross-user-cross-thread-isolation.md | Cross-User / Cross-Thread Isolation |
| 66 | 66-gap-session-reset-stale-session-recovery.md | Session Reset / Stale Session Recovery |
| 67 | 67-gap-router-worker-edge-backpressure.md | Router Worker / Edge Backpressure |
| 68 | 68-gap-long-running-soak-test.md | Long-Running Soak Test |
| 69 | 69-gap-chaos-combination-test.md | Chaos Combination Test |
| 70 | 70-gap-recovery-after-full-dependency-restart.md | Recovery After Full Dependency Restart |
| 71 | 71-gap-upgrade-recreate-persistence-test.md | Upgrade / Recreate Persistence Test |
| 72 | 72-gap-unknown-input-fuzzing.md | Unknown Input Fuzzing |
| 73 | 73-gap-production-error-classification.md | Production Error Classification |
| 74 | 74-gap-failure-injection-coverage-gate.md | Failure Injection Coverage Gate |
