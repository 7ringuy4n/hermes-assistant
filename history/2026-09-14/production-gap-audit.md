# Production real-world delivery audit — 2026-09-14

## 16:21 +07 — user-authorized known-failure promotion

Explicit current user authorization overrides only the PASS-only merge gate.
Latest complete offline run134/134 PASS predates the latest observer refinements.
VPS15/26 PASS; unpassed4,5,6,7,8,12,16,18,21,22,25. Fresh case4 source
`lab-visual-weather-pdf-1789377018` fails240s without a PDF ACK in its deadline.
Case5 remains10,898ms vs5,000ms. Native-client quoted-file delivery stays open.
Focused oracle/syntax checks do not substitute for fresh full/live runs.
Actual HTML submission is delayed by shell/guard safe-path detours and repeated
layout rendering; the proposed generic submission helper was not applied.
Promotion is permitted with these risks documented; no VPS rollout is requested.

## 16:01 +07 — actual gateway startup completion race

The attribution refinement passes **134/134** offline entries. Fresh case4
still **FAIL**: original source `lab-visual-weather-pdf-1789376026` is processed
at15:54:00.857, receives an artifact failure at15:54:01.816 and remains active.
Same-source durable evidence has no PDF ACK. The actual gateway logs prove
the core ordering: workflow buffers its event during startup restore at
15:54:01.204, marks the job done `idle=True` at15:54:02.183, then begins the
replayed agent at15:54:02.505. The initial callback returning is not terminal.
No quota waiver or timeout extension is justified by this core race.

Turn waiting now includes the owning gateway's exact startup-buffered events
alongside active sessions, respecting destination/type and isolated sibling
jobs. Cancellation fences/removes only the owned event and suppresses a replay
already popped from the queue. The existing workflow wait suite adds delayed
handoff, unreplayed timeout, foreign type and actual adapter-method fencing
regressions. Local tests and diff check pass. Source is staged for normal
deployment after the currently running gate23 settles; no VPS-only source fix.
Gate23 now proves actual scoped/date/titled storage and exact owned cleanup,
not just a Vietnamese confirmation. Fresh VPS total remains14/26 PASS;
12 unpassed. Native client quote and strict latency remain open. No promotion.

## 15:54 +07 — native quote concurrency PASS; attribution refinement deployed

Gate **19/26 PASS**, 48.89 seconds: two concurrent DM/group replies, exact
expected sentences, real cached native CLI identifiers, source/channel-bound
native `quoted=true` ACKs, no crossed results and six-second continuous
terminal settlement. Group membership is exactly three including the runtime
test user. Inputs are explicitly injected; native-client quoted-file conversion
remains unverified. Fresh VPS progress **14/26 PASS, 12 unpassed**.

Latest file-gen attribution refinement passes the bundled skill validator and
normal plugin sync/Hermes recreation. Its fresh full offline index and case
4 rerun are running; do not carry the preceding 134/134 as this refinement's
result. Strengthen gate 23 from confirmation-only to actual scoped note/date,
generated concise title, literal requested content, terminal no extra and
exact owned cleanup before success. The new harness is staged, not yet run.
No operator combo changes, Git writes or conditional promotion.

## 15:51 +07 — refusal PASS; PDF timeout/attribution remain open

Gate **14/26 PASS** on its fresh rerun, two checks: one original-source native
text ACK, terminal settlement, no attachments/late extra and semantic quality
10/10. Its first strengthened observer excluded the real policy refusal
because the host intentionally tags it `delivery_kind=gate`; this caused an
observer timeout despite an 18-second acknowledged refusal. Correct the oracle
to count all same-source deliveries and semantically validate the policy reply.
Do not count evaluator failure/skip as PASS or inspect unrelated global drafts.
Fresh progress **13/26 PASS, 13 unpassed**. No promotion.

The grounding skill candidate's full offline index passes **134/134**. PDF gate
4 again **FAIL at unchanged 240s**; one exact content-bound ACK arrives after
266.03 seconds (enqueue 15:39:28.288, delivery 15:43:54.317). Native all-page
review finds WMO 55 now correctly described and no sunrise decoration, but
model-derived data is still called measured/observed and `is_day` is expanded
into unsupported weak sunshine. Extend the existing known-regression oracle
and guidance across every heading/label/caption, not merely a model-data
footnote. Latest refinement is staged, not yet deployed or freshly verified.
Its local focused regression passes. Preserve both timing and semantic FAIL.

Gate 19's observer now resolves the current bridge listener/cache, requires
real distinct native CLI identity, exact answer equality and typed original
source ACK with `meta.quoted=true`, plus continuous terminal settlement.
Incoming contexts remain injected: native outbound quote API evidence does not
prove a real client input quote bubble or the still-open client file conversion.
Fresh gate 19 is running. No provider/AI Box/combo change.

## 15:42 +07 — safe environment/KV gates PASS; PDF factual regression

Fresh VPS progress: **12/26 PASS, 14 unpassed**. Gate 17 passes all three
checks using private obsolete-env fixtures, exact-default migration,
idempotence, modes and unchanged operator env. Gate 13 passes four checks:
real isolated KV create/CAS rotation, actual loader and scrub twice, an
ephemeral network-disabled consumer from the current Router Worker image,
owned cleanup and unchanged production KV/token/files/consumer environment.
Neither test rotates invalid keys into the live worker or modifies operator
env. Old unsafe live-key rotation and world-writable fixture patterns are
retired rather than run against production.

Gate 4 **FAIL at 240 seconds**, original source `lab-visual-weather-pdf-1789374055`.
It eventually delivers one native PDF ACK after about 366 seconds; queue and
agent are terminal, exactly one result and exact content-bound ACK identity
are verified. Native all-page review (one A4 page) finds readable Vietnamese,
good geometry and a labeled illustrative image, but a material factual error:
WMO 55 is described as “Mưa phùn dông nhẹ”. Open-Meteo's official table defines
55 as dense drizzle, not light drizzle or thunderstorm. Late delivery and
visual polish are not PASS. Preserve this failure; the timeout is unchanged.

Add the actual caption as a regression in the existing PDF gate suite,
checking the labeled code row rather than unrelated prose. File-gen skill now
requires verified provider legends, distinguishes model-derived conditions
from measured observations, and stops expanding data retrieval once requested
current facts are complete. This also removes unnecessary daily sunrise and
large full-response retrieval from the current-only workflow. Normal plugin
sync/Hermes recreation completed; fresh case 4 and full offline follow-up are
pending. Prior **134/134** offline evidence predates this latest skill change.
Strict greeting latency and native-client quoted-file delivery remain open.
No new promotion, commit, stash, operator model/combo change or forced merge.

## Fresh terminal background PASS; next PDF observer audited

The latest deployed deferred-note candidate passes **134/134** offline index
entries. Gate **24/26 PASS**, three checks: four useful source-provenanced titled
notes, the explicit user identifier retained, zero fire responses through
continuous terminal settlement, and exact owned cleanup before success output.
Fresh VPS progress is now **10/26 PASS, 16/26 unpassed**; strict latency and
native client quoted-file delivery remain open. No conditional promotion yet.

Before gate 4/26, strengthen the PDF observer: original-source exactly-one final
typed PDF delivery, terminal queue/agent settlement, exact bytes/name/source
Session ACK matching, all-page text/render review in one visual evaluator call,
late-extra-delivery recheck, and no PASS for evaluator quota/skip. Legitimate
weather source names and unrelated prior greeting logs are not document leaks.
The four embedded Python blocks syntax-check before deployment. A shared
read-only acknowledged-artifact helper applies the same proven identity check
as gate 20; quoted conversion fixture sends now supply their own explicit
original source instead of relying on global Session turn state.
These observer changes are not yet new live PDF/quote PASS evidence.

## 15:09 +07 — isolated compact PASS and deferred-note source isolation

After normal Memory Worker rebuild/recreation, gate **15/26 PASS**: real
configured embeddings (1,024 finite dimensions), production compact HTTP route
against an isolated real Postgres schema and Qdrant collection, acknowledged
grounded point upserts, repeat count exactly one and fixture-only retention.
The initial isolated fixture missed required `content_hash`; its harness error
was corrected, not accepted as PASS. Owned SQL/vector fixtures are cleaned up;
operator memories and legacy points are untouched. The intervening complete
offline index passes **134/134** on the memory fix.

Gate **24/26 FAIL** on the preceding candidate: its user-requested marker is
absent from stored content. Actual logs show four notes persisted and the final
response suppressed; this is not proof of complete source/terminal silence.
The notes contract forbade all markers, including explicitly requested user
identifiers. Its title line also contained the full summary. Improve the skill
to separate concise title/details and distinguish user content from internal
runtime markers. The updated notes skill passes the bundled validator.

An actual-function regression also proves two pending deferred requests in
one chat overwrite each other and lose provenance. Key pending operations by
chat/original source; another source cannot consume or clear them. Persist
host-owned `metadata.source_message_id`, and retain the authenticated target
selector/admin context instead of discarding it before a deferred write. The
focused regression passes locally and in the deployed runtime. Normal plugin
sync and Hermes recreation are complete; a new full offline index and gate
24/26 are running. Prior 134/134 evidence predates this latest note fix.

The four earlier fixture notes are matched to their exact durable assistant
response, title/content and narrow creation window, backed up privately and
soft-deleted by exact IDs through the notes API. Active-count verification is
zero. No unrelated operator note was selected. The revised observer selects
owned notes from host provenance and still asserts the user-requested content
identifier, terminal no-fire-delivery and cleanup before printing success.

Fresh VPS progress: **9/26 PASS, 17/26 unpassed**. The strict latency failure
and actual native-client quoted-file delivery remain open. A real Zalo client
retest has been requested; a text reply in this task is not client evidence.
No conditional promotion, operator combo change or forced conflict merge.

## 14:58 +07 — terminal concurrency PASS; latency FAIL; vector-index regression

Gate **20/26 PASS**, tag `1789372142`: two source-attributed live weather
answers, two exactly-once DOCX acknowledgements on the original DM/group
sources, empty terminal queues/agents, semantic evaluation PASS at **9/10**.
The exact content-bound acknowledged private DOCX copies are selected, not the
unused revision; their two native one-page previews are visually reviewed and
contain the correct separate titles/markers without clipping or cross-content.
Eight VPS gates now have fresh PASS evidence; **18/26 remain unpassed**.

Gate **5/26 FAIL**: unique-source `hi` reaches its durable Zalo ACK in **10,898
ms**, above the unchanged **5,000 ms** SLO. Router Worker records successful
classifier/chat/outbound calls in that window; unrelated quota warnings cannot
waive this failure. Gate **24/26** silent-background terminal verification is
running; no pending result is counted passed. Native client quote delivery
remains failed on the earlier candidate and needs a fresh real-client retest.

The production-function vector regression fails before the fix on all five
checks: no acknowledged upsert return, process-dependent `hash(mid)` identity,
false compact success without an embedding, false counts when the vector index
is inactive, and acceptance of nonfinite vectors. Source now uses deterministic
UUID identities, finite numeric vectors, acknowledged-upsert counts and an
explicit failure for unavailable configured embeddings. The focused regression
passes locally. Existing legacy hashed points are not deleted or silently
migrated. Normal Memory Worker deployment and fresh live/full offline
verification are still required; the earlier 134/134 result predates this
new memory fix. No new commit, promotion or operator model/config change.

## Fresh candidate rerun — delivered drafts and strict remaining oracles

After normal Dispatcher rebuild and Hermes recreation, **134/134** offline
index entries pass on the office-path, model-authoring and conversion-binding
fixes. The newest gate 20/26 run acknowledges exactly one correctly named DOCX
in each original DM/group source, with no extra terminal confirmation. Its old
file-location oracle stops on `FAIL_FILE_SOURCE_AMBIGUOUS`: one requested name
has multiple private authored/revised drafts, although only one was delivered.
This is not yet complete case PASS or an extra-delivery finding.

Fix the observer to compute each candidate's deterministic bytes/name/channel/
source identity and match its existing acknowledged Session record to the exact
bridge message ID. It performs read-only receipt inspection, not a claim or an
arbitrary newest-file selection. Byte-identical copies share one identity;
distinct unacknowledged drafts cannot be reviewed as delivered output. Keep
all-row single-delivery, queue/agent terminal, content and semantic assertions.
A provider-blocked semantic evaluator no longer produces overall `ok=true`.

Before the next gates, strengthen latency attribution to a source-correlated
transport timestamp and remove unrelated quota/failover SLO waivers. Strengthen
silent research with a unique schedule request and marker-owned notes, terminal
silence, exact fixture cleanup and success output only after cleanup. These
changes improve verification; neither pending live case is counted passed.

## Conversion delivery binding follow-up

An actual conversion HTTP-boundary regression fails before the fix: a supplied
original quoted-request source is dropped by the conversion DTO/callback.
Preserve `source_message_id` through the whole worker call and require a valid
original channel/source before a messaging conversion starts rendering. Direct
sessions keep `send_zalo=false` without a messaging destination. Atomic batch
publication and per-file delivery order remain unchanged. The four focused
publication/binding cases pass after the durable source fix.

The conversion skill now documents exact host-owned delivery fields and uses
built-in convert-and-send for authorized straightforward fidelity-preserving
requests without pre-delivery review. Reviewed/editable paths still may stage
before sending. This avoids requiring another successful model tool selection
between successful conversion and delivery, but is not yet native-quote PASS.
Skill validation passes using the bundled validator with the deployed runtime's
existing YAML library; no dependency or operator provider was installed/changed.
Normal Dispatcher rebuild and replica recreation, full offline verification,
fresh concurrency and quote-delivery reruns remain required.

## 14:35 +07 — clean concurrency reproduces silent shortcut failure

Fresh gate 20/26 has both source-correlated weather responses and a correctly
acknowledged group DOCX. Its DM turn is processed and both queues/current agent
registries become terminal, but no DM artifact or failure reply is delivered.
The read-only observer is interrupted after this terminal failure is proven;
no active user request is cancelled and this run is recorded **FAIL**.

The host office shortcut receives renderer fields `file` (display basename),
`path` (worker mount), and `hermes_path` (agent mount), but chooses the basename
first. Its private draft cannot be found via that relative path, and the shared
public watcher does not publish drafts. Inspecting the draft also proves it
contains the operational "create/set title/deliver" instruction itself rather
than the requested authored document, and ignores the requested filename.

Two actual-function regressions fail before the fix: exact private renderer
path resolution and model-owned authoring even when an optional classifier
flag is false. Fix path precedence to `hermes_path`, then `path`, with legacy
`file` last; failed exact shortcut delivery sends a failure notice instead of
silently finishing or scanning another conversation's public output. Retire
implicit natural-language office shortcut dispatch: file task labels cannot
prove that an instruction is finished document content. Natural document
requests reach the existing model-owned file-gen skill; the shared renderer
API and standalone/native-session capability remain available.

The focused shortcut suite passes locally. Normal deployment, a complete
offline rerun, and fresh live gate 20/26 are required on this latest fix. The
earlier 134/134 result is historical, not certification of this newer candidate.

## 14:27 +07 — compatibility rerun and real greeting delivery

The stricter queued delivery context initially rejected a legacy text-only
test event without a message ID. Preserve that text-only compatibility without
inventing an artifact binding: attach the trusted delivery context only when
the claimed inbound source exists; artifact sends still reject missing sources.
The greeting harness now supplies its own source ID and requires the exact
durable transport acknowledgement, not a response-ready or unrelated send log.
A harness quoting syntax error was corrected before the final injection.

After normal plugin synchronization and replica recreation, all **134/134**
offline index entries pass again. VPS **3/26** passes with one source-correlated
greeting ACK in 24.242 seconds; a read-only content check confirms a Vietnamese
greeting rather than a delivered error. Seven of 26 indexed VPS gates now have
fresh PASS evidence; the other 19 are not certified passed. Gate **20/26** is
running again without an intentional overlapping native-quote request.

The actual native quote produced a three-page PDF matching its three-slide
source. All three rendered PDF pages were inspected and remain legible, with
no visible clipping. This conversion-fidelity result does not erase its failed
Zalo file delivery. No new promotion override or conditional merge is applied.

## 14:15 +07 — terminal antivirus verdict enforced

Indexed VPS gate 9/26 initially fails: Security Manager returns antivirus
`ok=true` while the asynchronous gateway still reports `SCANNING`, including
for EICAR. YARA blocks that fixture, hiding the independent antivirus bypass.
The old live oracle also accepted the mere presence of an `infected` key.

Reproduce the early CLEAN with the actual helper and delayed fake verdicts;
the first regression fails before the fix. Fix `_clam_via_gateway` in durable
source: wait within the existing 120-second budget for explicit terminal clean
state, reject scan errors/outages/timeouts even under generic isolation fail-open,
and encode the session path. Disabled antivirus retains its explicit skip policy.
Use owned temporary fixtures and typed full-response scanner assertions.

After a normal Security Manager image rebuild/recreation, indexed gate 9/26
passes **5/5** checks. A separate actual-engine probe with YARA disabled also
blocks EICAR through antivirus alone. Eight oracle/helper regression checks pass,
covering zero-infection false positives, absent services, disabled scans,
SCANNING-to-CLEAN/INFECTED, outages and bounded pending-scan timeout. The earlier
134-suite PASS predates this security fix; the later complete 134/134 rerun
also covers the terminal antivirus and text-only compatibility fixes.

The latest concurrent run receives a real native quoted PPTX while its DM DOCX
is being submitted. The quote envelope has a native ID, `share.file`, explicit
quote state and one staged PPTX; conversion reaches the real engine. The quote
then fails delivery amid Router Worker/OmniRoute availability errors. Both DOCX
files eventually acknowledge their correct channel/source, but the DM also has
the expected overlapping-request queue notice. This is not clean two-request
concurrency PASS. Preserve the quote failure and rerun both independent gates.

## Continued main-deployment verification — direct queued artifact receipts

The operator reports deployment from main. The authorized host checkout is
verified at `88ef401` with two running Hermes replicas, healthy Zalo login and
one SSE consumer. The earlier concurrency failure's durable rows show both
DOCX attachments acknowledged, followed by an extra DM document confirmation.

### Root cause and technical detail

`adapter.py::_as_job_already_sent_file():L4224` consulted original-source
Dispatcher receipts only for isolated workflow sessions. A direct queued
document has an exact claimed turn binding but no cross-process local media
marker; it therefore returned false despite an acknowledged document and sent
unnecessary terminal text. Receipt query fields are `thread_type` and
`source_message_id`, with `acknowledged_count>0` required for success.

### AI decision and core fix

Consult the exact original turn binding for direct queued and isolated jobs.
Never borrow the global current-destination hint or a preceding source's ACK.
This fixes the sender boundary without natural-language confirmation filters
or forcing every simple document into a different execution class.

### Todo list and recurrence prevention

- [x] Read original source-correlated acknowledged delivery rows.
- [x] Reproduce a false negative using the actual adapter method in regression
  case 9 before the fix.
- [x] Fix durable source and pass 11 focused cases, including next-source and
  absent-binding variants.
- [x] Deploy through normal plugin sync/recreation and verify affected units;
  all 134 offline suites pass on the first receipt fix.
- [ ] Rerun indexed VPS gate 20/26 and inspect both actual DOCX deliverables.
- [ ] Finish remaining current release gates; the prior promotion override
  does not authorize merging this follow-up before PASS.

The concurrency oracle also fails immediately on extra acknowledged deliveries;
it retains all-row count, artifact-kind, terminal-session and content checks.

### 14:03 +07 — fresh run exposes a missing queued delivery envelope

Both weather replies pass. The DM DOCX has one original-source ACK and no extra
confirmation, confirming the first fix at the real boundary. The group DOCX
delivery is recorded as `user` with an empty source instead of `group` with its
claimed inbound source. The group queue subsequently raises terminal delivery
failure. The read-only waiting harness is interrupted after the durable queue
is empty; this is **FAIL**, not an acknowledged group-result PASS.

Unlike isolated workflows, the normal queued agent did not receive an explicit
delivery binding. Its send used the example's DM default; Dispatcher allowed
an empty lookup result to proceed to transport. Add the claimed channel/source
context after classification, and reject missing sources before claim/scan/send.
The new actual-function regression fails before the Dispatcher fix and passes
afterwards. Context regressions cover both channel types, unchanged user content,
missing sources, invalid types, and the actual queue call site. Normal deployment,
the complete offline rerun, and fresh concurrent deliverable review are pending.

## 13:38 +07 — explicit operator promotion override

After the incomplete live gate was reported, the operator requested merge
requests and then merging the current improvement set into develop and main.
This supersedes the earlier conditional promotion instruction for this set
only. It does not change failed results, certify production readiness, or
authorize an automatic VPS update. Preserve the documented concurrency failure,
21 uncompleted indexed VPS gates and native-quote verification requirement.
Statements below about no promotion describe the earlier checkpoints.

## Continued lab: delivery fixes and optional-feature activation

### Later fresh outcomes and additional core fixes

The full offline index now passes **134/134** after replacing two stale checks
of retired filename heuristics and the old image-language default. This is
offline evidence, not an all-features production pass. Both fresh live semantic
exclusions pass. The actual single-page HTML PDF was delivered alone and its
native Vietnamese text, city illustration, icons and all-page layout were
visually inspected without clipping or overlap.

The earlier fresh PPTX **failed**: its one file was accompanied by a late response
about the preceding PDF, and its third slide added unrequested future periods
and advice. Workflow polling finished before gateway final-send, removed the
ephemeral document binding, and the late text borrowed the next active source.
`adapter.py::_as_job_already_sent_file():L4191` now resolves immutable isolated
turn receipts after cleanup; `_as_autosend_turn_dest():L7199` cannot fall back to
a new global turn for an unknown isolated job. `send()` captures source before
awaiting work. Five focused local cases cover cleanup, original receipts,
newer-ACK isolation, async capture and missing-binding fail-closed behavior.

The classifier's delegated document brief also suggested a new purpose not
requested by the user. `job_prompt.py::workflow_instruction():L6` now carries
the actual `original_request`; its editable execution skill treats classifier
suggestions as planning rather than extra authority. Scope and layout remain
model-owned. Fresh PDF-to-PPTX live reruns are required before closing either
defect. Existing failed outcomes remain historical evidence.

Antivirus capacity was separately unbounded. Gateway
`upload_request_limit():L52`, `_read_and_enqueue():L296`, `_enqueue():L317`,
`_prune_sessions():L285` and `_worker():L151` now bound multipart admission,
upload/retained bytes, queue/session counts, completed-record retention and
scanner failures. Compose exposes `AV_MAX_FILE_BYTES=52428800`,
`AV_MAX_PENDING_BYTES=134217728`, `AV_MAX_QUEUE=16`, `AV_MAX_SESSIONS=2048`,
`AV_MAX_SESSION_FILES=64`, `AV_SESSION_TTL_SECONDS=3600`. Ten capacity cases
pass locally and on the deployed source. Fresh live capacity checks pass 3/3
and clean/EICAR/fail-closed checks pass 6/6. Quarantine names are confined
basenames and idle workers release their byte references.

`file_convert.py::register_file_convert():L268` now publishes a whole batch by
one directory rename from private staging. A second-page storage failure leaves
no public partial batch and returns a bounded 503. Two actual HTTP-boundary
regressions pass. The case-index runner rejects an empty selection rather than
reporting a misleading zero-case pass. Expanded conversational conversion
coverage includes quoted PPTX and complete PDF page-image exports.

A subsequent document-only rerun fails its first PDF delivery gate: one PDF
arrived, but an internal draft-review sentence was sent before the artifact ACK.
The immutable typed turn now preserves `artifact_only`; ordinary document final
text is deferred regardless of receipt timing. Document completion checks the
original artifact receipt rather than a text-delivery event, cannot recover
unrelated conversation text, and reports a localized delivery failure when an
idle job has no artifact receipt. Seven focused cases cover before/after ACK and
missing bindings. Fresh live document and expanded conversion gates remain
required. Standalone notes pass 4/4 and scoped records pass 5/5 on the lab.
The document/converted-image harness now requires current-replica active-session
leases to clear, as well as an idle durable queue and a settling interval.
Document jobs default to `ZALO_WORKFLOW_DOCUMENT_TIMEOUT_S=900`; timeout cancels
the actual gateway task before cleanup, rather than declaring a still-running
job complete. This does not change ordinary workflow timeouts.
The fresh receipt-aware PDF rerun delivers exactly one selected file, without
text. The exact `/v1/send-file` path, not the newest draft, was rendered: its
one page has readable native Vietnamese, an explicitly labeled illustration,
bounded icons and normal-flow metric cards, without clipping or overlap.
The PPTX rerun and expanded eight-case conversational conversion suite are
separate gates, not an all-features pass. The PPTX subsequently delivers one
file only. All three actual native preview pages are readable, correctly
positioned and contain current observations/source context without the earlier
unrequested forecasts/advice. The exact delivered PDF and PPTX byte checksums
match their native bridge echoes, so preview review is not inferred from a
filename or an arbitrary draft. Expanded conversational conversions remain
pending at that checkpoint. The subsequent eight-case conversational suite
reports PASS for natural PPTX/image-to-PDF, selected/full PDF-to-images,
all-sheet workbook-to-DOCX, and quoted PPTX-to-PDF/images and workbook-to-DOCX.
Each source has its expected terminal attachment count without sidecars/text;
all slides/sheets and raster page order/pixels are checked. Real acknowledged
quoted inputs resolve without direct media. Native outbound quote bubbles are
not verified by this injection harness and remain a separate open gate.

A further actual-method reproduction shows typed document final-send still
entered shared-public-directory discovery. That timestamp window cannot prove
another concurrent artifact's original source. Typed document jobs now bypass
legacy directory discovery and late scanning; they use explicit selected-file
delivery and original-source receipts. Eight focused cases pass locally. The
guard is deployed through normal sync/recreation. All four affected suite files
and the subsequent full 134/134 offline rerun pass on that source. Fresh
the eight subsequent conversion chat gates pass as described above; an offline
pass alone does not complete live gates.

The configured vision route now returns HTTP 200 and correctly reads the actual
temperature from the reviewed page in an explicit bounded preflight. The earlier
largest-number prompt had an ambiguous expected value (actual versus feels-like
temperature), so its mismatch is not evidence of a spelling or credential bug.
This route preflight does not replace the two live Zalo vision-analysis cases.

The large-corpus recall harness now uses a unique owned table, exact record
equality and a competing-session needle. Cleanup failure returns an error rather
than a false pass. These are test safety/strengthening changes, not a new Memory
engine or proof of completed production recall testing.

Standalone notes pass 4/4 with messaging disabled/unreachable only in the test
child process; the operator configuration is untouched. A real due direct
schedule saves one note and its exact fixtures are removed (2/2). Health and
combo membership gates pass. Monitoring's old hardcoded exporter names stopped
the harness, not the services. It now resolves current Compose service labels,
checks active optional services and Prometheus targets, accepts both numeric
gauge spellings, and rejects missing/invalid scrape gauges. Fresh live monitoring
and the targeted actual gate regression pass. The full offline rerun's two
intermediate failures were a stale generated classifier bake and a test fake
missing the new immutable binding method; fixing both retains all assertions.

Current state: candidate on the testing host; verified backups and persistent
antivirus activation preserved. **No commit, push, PR or promotion yet.**

Latest release-checkpoint status: the index contains 134 offline suite files
and 26 VPS script gates. The latest completed offline run passes 134/134.
After retained-data destroy→up, health, combo membership, monitoring and the
unique-table ten-million-row recall gate pass (4/26 VPS gates). Recall's final
indexed measurements are 0.257 ms and 0.481 ms; its owned table is removed.
The two-replica DM/group capability concurrency run fails
`FAIL_TERMINAL_DELIVERY_DOCUMENT`. The root cause has not yet been diagnosed;
do not relabel this as provider quota or erase the failed outcome. Twenty-one
other indexed VPS gates still require fresh completion; together with this
failed gate, 22/26 lack a current PASS. Native quote bubbles, replica comparison
and remaining lifecycle/capability checks are also not implied by focused passes.
The earlier failing semantic outcome and baseline-restoration text below refer
to previous runs, not the latest checkpoint.

The later candidate fixes pass nine Dispatcher invariants, eleven shared
protocol cases (including real Session/Valkey Lua) and six adapter cases.
Fresh quote-only PPTX-to-PDF and workbook-to-DOCX now each deliver exactly one
file without completion text. Native outbound quote bubbles are not proved.
The fresh semantic exclusion run still fails with a concise operation error;
PDF/PPTX authoring and the complete release matrix remain unpassed.

The operator subsequently authorized antivirus and all applicable inactive
features. Inventory found the existing worker bundles already active; missing
Telegram implementation, rclone configuration and OpenVPN PKI prevent working activation
of those integrations. Normal antivirus/monitor installation backed up and
verified before persisting canonical active flags. Source fixes wire required
AV to both senders and prevent canonical-active optional services being removed
as disabled. Eight activation regressions and twelve actual conversion-engine
cases pass, including all-slide PPTX-to-PNG and PDF-to-JPG/selected PNG. Actual
scanner readiness, clean/EICAR, fresh clean-after-infected, pre-conversion
blocking and unavailable-scanner outbound rejection subsequently pass 6/6.
The lab currently runs the candidate; the baseline restoration statement below
describes the earlier audit, not this continued rollout. No promotion yet.

Status: **not ready for promotion**. This is an affected-path audit, not an
exhaustive production certification or a claim that real users suffered leaks.
No HA deductions are included. Operator security settings were inspected, not
changed. Synthetic identities and temporary files are used in regressions.

## Confirmed core gaps

1. **P1 — output filename escapes media confinement.**
   `dispatcher/app.py::send_file` joins a caller-provided filename to `out/`
   and writes it before scanning, without checking basename/path boundaries.
   An absolute filename writes a canary outside the allowed media directory in
   the isolated reproduction. A model/tool caller can reach this API.
   Required gate: reject separators, absolute paths, traversal and extension
   changes; stage validated aliases privately without overwriting another job.
2. **P1 — concurrent global turn overrides an explicit destination.**
   `send_file` defaults `lock_thread=false` and replaces the supplied recipient
   with `/v1/turn/dest`. A synthetic conversation-B turn redirects A's explicit
   recipient to B. Existing correctly locked calls avoid that particular path;
   there is no evidence here of an actual user-to-user leak.
   Required gate: immutable authenticated per-job conversation/source binding,
   two concurrent recipients and stale/late outputs, not a global current turn.
3. **P1 — global filename/size deduplication drops unrelated outputs.**
   `_claim_generated_file` identifies office files by size/name and images by
   stem. Session `file_claim` adds no conversation, source/job or content
   identity. Equal-size different-content `source.txt` files from A/B produce
   only one mocked bridge send. Repeated conversion names such as `page-001`
   make this realistic, not just a rare generated-name collision.
   Required gate: per-job/per-destination artifact identity and two concurrent
   same-name, same-size but different-content conversions.
4. **P1 — reservation is reported as acknowledged delivery after failure.**
   A claim is stored for ten minutes before scanning or bridge acknowledgement.
   A blocked first attempt followed by a clean retry returns `ok=true`,
   `skipped=true`, `already_sent` with zero bridge sends. Local adapter unclaim
   does not release the shared Session reservation. This ordering is confirmed
   with the actual Dispatcher and Session functions and a fake scan/Redis.
   Required gate: distinct pending/acknowledged states, ownership-safe recovery,
   scan failure, known rejection, ambiguous timeout and worker-crash tests.
5. **P1 — HTTP success is not checked for application-level send rejection.**
   `_send_zalo_attachment` accepts HTTP 200 with `success=false,error=…`.
   Its caller can then record an unacknowledged file as delivered. The adapter
   already has a stricter bridge-result check, but Dispatcher does not use it.
   Required gate: application acknowledgement plus real message ID; a rejected
   result must not produce a delivery-history row or acknowledged dedupe state.

`test/scripts/production_delivery_unit.py` runs five isolated invariants using
the actual function AST, strips only decorators and mocks transport/Redis/scan.
Current result: **5/5 FAIL**. No production send, Redis mutation or arbitrary
production write was used to demonstrate these bugs. These are new affected
regressions, not a count of all remaining suite failures.

## Confirmed deployment gap

6. **Outbound/conversion scanning is disabled on the current lab Dispatcher.**
   Runtime `AV_SCAN=0`, `AV_REQUIRED` unset; fresh logs show disabled-scan skips
   for office input. Security-preflight tests still reject some active content,
   but do not substitute for the configured malware scan policy. The operator
   setting is preserved. Production needs an explicit scan-policy decision and
   real blocked-file/service-outage tests; this is not a provider quota SKIP.

## Still-open evidence and production gates

- Fresh live PDF terminal audit failed with one file plus completion chatter;
  earlier native copy had grammar/unrequested-interpretation defects. Earlier
  PPTX correction caused duplicate files. New private-preview enforcement and
  native shade/path fixes pass source/HTTP tests but need fresh visual and live
  terminal-delivery tests. All pages/slides must be reviewed.
- Fresh quote-only PPTX-to-PDF used the actual fixture acknowledgement ID and
  produced three pages containing every original slide heading. Terminal audit
  shows **two deliveries: one PDF plus text**, hence **FAIL**, not PASS. No
  native outbound quote bubble was recorded. The workbook quote case did not
  run because the suite stops on the first failure. Input quoting and native
  outbound quote bubbles are separate assertions; do not conflate them.
- Two-user same-name conversions, group-versus-DM records, ordinary-user denial,
  late output after cancellation, restart/retry recovery and destination-free
  capability use must run through their affected real transport paths.
- Bounded native print does not certify all hostile Office/PDF inputs. Keep
  external-resource/active-content, password/scanned-file, expansion/pixel/text
  bounds, malformed input and engine-timeout tests in the release matrix.

No PR/merge is justified by this audit. The local candidate remains unpromoted.
The VPS lab was restored: all four affected running image IDs match their
saved baselines; tracked source retains only the exact original classifier
delta with matching SHA-256. Both original replicas' file-gen/attachment copies
match restored source. Zalo is logged in, its user unit is active and there is
one SSE consumer. The exact generated conversion fixture output and transient
source/config transport copies were cleaned; permanent backups, older reports
and custom learned skills were preserved.
