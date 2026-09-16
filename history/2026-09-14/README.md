# 2026-09-14 — scoped records and visual document delivery

## Continued verification and feature inventory

The current [worker/feature catalog](../../docs/07-worker-feature-catalog.md)
lists all 41 Compose services, worker bundles, user capabilities, security
switches, prerequisites/scaffolds and maintenance timers with fresh defaults.
It distinguishes the continued testing host's active settings from repository
defaults. Updated indexes expose this catalog for architecture revision.
Required antivirus activation and native PDF/PPTX-to-image checks are recorded
in [the continued production audit](./production-gap-audit.md); fresh semantic
selection now passes both exclusions. Visual authoring/release gates remain
open: pre-ACK private-review chatter exposed another document handoff gap.
Eight focused cases cover immutable bindings, result-only delivery and bypass of
unattributed shared-directory discovery. The latest deployed-source offline
index passes 134/134; fresh antivirus capacity/scanner gates pass 3/3 and 6/6.
Fresh PDF and PPTX terminal single-file deliveries and every native page/slide
pass review; selected artifact bytes match bridge echoes. Expanded conversions
and the broader clean-deployment matrix remain separate gates. No merge yet.

## 07:00 — Preserve complete note predicates

### Symptom
An exclusion lookup returned a record in the excluded category.

### Root cause
The notes client retried individual query words after a miss; Memory also
discarded text/tag filters in a date-only fallback. Neither evaluated the full
semantic predicate before presenting those broader candidates as matches.

### Technical detail
- `notes_client.py::execute_note_plan()` at `hermes/main/plugins/zalo/notes_client.py:L147`;
  `query_notes()` at `architect/memory/memory-worker/app.py:L470`.
- `note_selector.semantic_query` preserves the complete predicate. Model
  selection in `_semantic_candidates():L69` is bounded by
  `NOTES_SELECTION_MAX_BYTES=131072` and accepts only supplied candidate IDs.
- Both classifier coercers preserve the new selector fields; scope/date SQL
  remains deterministic. Saturated/oversized or uncertain selections fail closed.

### AI decision
Move semantic understanding to an editable model prompt, not multilingual
negative-keyword rules. Remove implicit broadening rather than adding exceptions.

### Fix (core)
Strict backend queries and explicit model-owned semantic selection; no
individual-word retry. Count/mutation windows do not claim completeness when full.

### Todo list
- [x] Inspect and reproduce the broadening path.
- [x] Fix source and add strict-query/selection regressions.
- [x] Verify two Vietnamese exclusions through real Zalo with marker fixtures.
- [ ] Complete full affected live release gates and promotion.

### Prevent recurrence
`memory_note_query_unit.py`, `scoped_records_unit.py`, and marker-isolated
`scoped_documents_smoke_lab.py` cover strict filters, excluded category versus
same-keyword non-category records, and uncertain/invented model IDs.

## 07:01 — Authorize record scope independently of delivery

### Symptom
Cross-conversation record administration was absent for notes and unchecked for
some schedule targets; requester IDs could expose a group schedule in a DM.

### Root cause
Scope selection and reply destination were coupled, and schedule visibility
treated audit identity fields as conversation IDs.

### Technical detail
- `record_scope.py::resolve_record_target()` at
  `hermes/main/plugins/zalo/record_scope.py:L7` checks trusted host admin identity.
- `schedules_for_thread()` at `hermes/main/plugins/zalo/schedule_client.py:L548`
  no longer matches requester/sender audit IDs.
- Selector `scope=current|group|dm|all` and `scope_ref` are typed separately from
  `target_channel`; `NoteQueryReq.scope_ids` performs one registered-scope query.

### AI decision
Reuse the authenticated channel registry and existing operator-admin identity;
never accept a model-provided role or invent another identity/configuration store.

### Fix (core)
Group/DM defaults remain isolated. Explicit admin access resolves a known
conversation. All-scope access is read-only; mutations require a specific scope.

### Todo list
- [x] Inspect existing group notes, registry, and sole-admin boundary.
- [x] Add typed selectors, authorization, and audit-ID isolation regressions.
- [x] Verify actual group/DM/admin record access on the lab (five core cases).

### Prevent recurrence
Tests cover non-admin cross-group/DM/all rejection before transport, admin
creation ownership, batched all-scope reads, and all-scope mutation denial.

## 07:02 — Keep document assets private and render them reliably

### Symptom
A PDF had a blank hero and no embedded image. One presentation request delivered
an illustration and two PPTX files; the supplied screenshot is not evidence of
a PDF sidecar.

### Root cause
Office media roots omitted Dispatcher’s actual `/data/media` mount and did not
translate Hermes aliases. Failed WeasyPrint resource fetches only warned, so
blank images counted as success. Other office formats ignored or silently lost
image directives. Scenic assets were written into public autosend space; the
first already-sent cache guard continued to older files instead of stopping.

### Technical detail
- `office_file.py::_resolve_media_path():L217`, `write_pdf_from_html():L325`,
  `_office_visual():L584`; `MEDIA_CACHE_DIR` maps worker/Hermes/host aliases.
- `app.py::scenic_still():L821` returns an exact `.assets/` `hermes_path`.
- `adapter.py:L7433` local-cache claim guard now terminates like the shared
  claim guard. Office publication uses `.build` then atomic replacement.

### AI decision
Fix resource/path ownership and delivery boundaries, not a hardcoded topic
layout. Keep visual authoring in skills and native Unicode document text.

### Fix (core)
Private document assets; strict local resource fetching and raster validation;
shared path translation across PDF/DOCX/XLSX/PPTX; no silent required-image
omission; atomic office publication and terminal document claim checks.

### Todo list
- [x] Inspect every page of the supplied PDF and the screenshot.
- [x] Fix source, image embedding, and skill constraints.
- [x] Run eight real-renderer tests on the VPS.
- [x] Run the shared-volume alias variant and inspect all fresh pages/slides.
- [x] Confirm one requested file, no separately delivered image/alternate draft.
- [ ] Restore lab source/configuration and verify stable logs.

### Prevent recurrence
`document_resources_unit.py` covers valid/absent/corrupt/unsafe resources,
embedding in every office format, and shared-volume aliases. Real-plugin smoke
tests require acknowledgement-backed single-file delivery, followed by manual
artifact review. A standard update rewrote a pre-existing baked classifier
delta; the original bytes were recovered from the baseline router container and
verified by matching SHA-256 before continuing. Preserve those bytes at restore.

## Current verification state
Candidate only. Two real-Zalo exclusion cases pass. Initial document gates fail:
the PDF turn ultimately sent five PDFs plus one image, and the actual weather
PDF has a nearly empty second page and a missing icon. The PPTX arrived after
the old harness deadline but violates requested current-only/language scope.
The strengthened harness waits for queue acknowledgement before auditing all
attachments; a first attachment is not terminal success. Fresh document reruns
now deliver exactly one requested attachment. The final PDF is one readable
page with its image intact, but still includes unrequested forecast/interpretive
content and inconsistent labels. The fresh three-slide PPTX has readable
Vietnamese text and images, but missing icon glyphs and unrequested future/advice
sections. Both content-quality gates remain FAIL, not release PASS. Five live
scoped core cases and four live standalone note CRUD cases pass. No merge-gate override applies to this
change set. No MR or production deployment is authorized before fresh PASS.

## 08:15 — Standalone capabilities and presentation routing

### Symptom
Direct document creation demanded a messaging thread, and explicitly local
schedule sessions could be routed to the Zalo bridge. Live presentation work
used unavailable local libraries despite the shared renderer's instructions.

### Root cause
The office HTTP boundary required `thread_id` regardless of `send_zalo`.
Schedule routing treated any thread field as Zalo even when a different
platform was explicit. Bootstrap suppressed PDF/DOCX/XLSX bundled skills but
not PowerPoint; the later bundled presentation skill prescribed local rendering.

### Technical detail
- `register_office_file()` in `architect/models/dispatcher/office_file.py:L1100`:
  `send_zalo=false` permits destination-free creation; `draft=true` writes under
  `out/.drafts/` and cannot be delivered automatically. Responses include exact
  `path` and `hermes_path` so clients do not guess artifact locations.
- `sendBack()` in `architect/schedule-worker/main.go:L529`:
  `origin.platform=hermes` takes precedence over local thread fields.
- `hermes/main/docker/hermes-replica-entry.sh:L135`: suppressed names now include
  `powerpoint` and `pptx`; the source-owned presentation wrapper routes file-gen.
- `execute_note_plan()` in `notes_client.py:L147`: the trusted standalone
  `current_scope_id` is configured by `HERMES_RECORD_SCOPE`, never a model plan;
  caller-provided `scope_ids` cannot broaden authorization.
- `docker/docker-compose.yml:L67`: source build path is `memory-worker/`;
  deployment component key/container remains `memory`, with no data migration.

### AI decision
Reuse capability services and deterministic host boundaries. Keep messaging
optional rather than inventing identities or introducing a parallel scheduler,
memory store, renderer, or local library installation path.

### Fix (core)
Destination-free office API, private previews with exact paths, direct notes
command, explicit Hermes schedule routing, presentation startup suppression,
and compatible Memory Worker source rename. Current docs describe both paths.

### Todo list
- [x] Local standalone scope denial and model-scope broadening tests.
- [x] Direct live Memory count through the notes command without chat identity.
- [x] Go handoff test with Zalo deliberately unavailable.
- [x] Nine real-renderer resource variants on the VPS.
- [x] Complete three real office HTTP tests and four standalone live note CRUD cases.
- [x] Inspect all fresh document pages/slides and terminal delivery audit.
- [x] Verify renamed component build/setup, five scoped core cases, and lab restore.

### Prevent recurrence
`standalone_records_unit.py`, `office_api_unit.py`, and schedule worker's Go
test cover these host boundaries. Presentation collision tests now cover the
bundled PowerPoint/PPTX names, not merely PDF/DOCX/XLSX. Historical paths retain
their original names; current paths and architecture use Memory Worker.

## 08:46 — Existing-file conversion and asynchronous standalone schedules

### Symptom
Cross-format conversion had no shared capability contract. Standalone schedule
fires waited for a complete model response on the short transport timeout.
Live scoped testing also rejected a valid DM returned by the channel registry.

### Root cause
File creation was incorrectly treated as a substitute for conversion. Hermes
chat completions are synchronous work, not an admission queue. Channel resolve
returns `dm` while registry listings use `user`; the boundary assumed one spelling.

### Fix (core)
`file_convert.py` and skill `file-convert` implement native Office print export,
bounded page/slide rasterization, image PDFs, and explicit editable content
reflow. Private output paths prevent intermediate/sibling deliveries. Existing
scan policy runs before parsing; macro/external-resource/archive and raster
limits fail closed. Reflow preserves section/sheet data with formula-like strings
inert, and honestly discloses lost layout/images/charts/animations/formulas.
Scanned text requires OCR, not blank extraction disguised as conversion.
`sendBack()` now uses Hermes `/v1/runs`, requires HTTP 202 with a run ID,
and sends an execution idempotency key. This confirms handoff, not task completion.
The scope boundary normalizes authenticated registry `dm` to protocol `user`.

### Verification and prevention
- [x] Ten real LibreOffice/PyMuPDF/Office-library conversion cases, including
  selected slides, multiple sheets, formula-text preservation/inert imports,
  invalid targets/pages, external resources, direct HTTP and security denial.
- [x] Six dependency-free production preflight variants reject renamed macro
  relationships, active embedded objects, external spreadsheet functions and
  oversized archives while allowing inert hyperlinks. These are local source
  checks, not a substitute for fresh real-engine/chat conversion gates.
- [x] Live destination-free PPTX-to-PDF API returns one private output.
- [x] Seven runtime skills pass the provided skill-creator validator.
- [x] Two Go native-admission/confirmed-run-ID regressions pass.
- [x] Actual 30-second standalone schedule fires and persists an isolated note;
  the exact fixture note and schedule are removed afterward.
- [x] Five actual registry/Memory/Schedule scoped core cases pass after DM fix.
- [ ] Conversion chat/attachment routing and wider direct-feature release matrix.
- [ ] Fix fresh PDF/PPTX content-quality failures and repeat visual/live gates.
- [x] Complete lab baseline restoration and post-restore monitoring.

### Restore evidence
VPS tracked source returns to its original main baseline with only the
pre-existing classifier delta; its SHA-256 matches the original saved bytes.
Memory, Dispatcher and Router Worker running image IDs match saved baseline
images; Schedule Worker is rebuilt from restored main source. Both original
Hermes replicas reload restored plugins/skills. Zalo remains logged in with
one SSE consumer, all relevant service health checks are stable, and exact
test-note/schedule active counts are zero. Read-only semantic comparison against
the verified backup confirms all seven combos and six provider configurations
unchanged; runtime usage/quota/OAuth-refresh fields are intentionally not
treated as operator configuration. Evidence is retained in the ignored lab
report directory. Temporary source/config archives and credential-bearing
SQLite comparison copies are cleaned up; permanent verified backups remain.

No MR, push or merge: current conditional PASS decision is not satisfied.

## Follow-up — quoted conversions and review-before-publication (candidate)

### Symptom and root cause
Staged quoted office attachments were ignored because local quote inheritance
accepted image suffixes only. Formatted document generation also allowed public
delivery before native-text and page-image review; a fresh PDF turn sent extra
chat text and earlier PPTX correction produced duplicate files. A presentation
shade used a non-serialized transparency property, hiding the scenic image.
Markdown cleanup could corrupt double underscores in an opaque asset filename.

### Core changes and prevention
`attachment.py` resolves bounded shared-volume office quotes as file media and
rejects traversal. `quote_file_conversion_unit.py` covers real TQuote payload
shapes, staged PPTX/workbook paths, invalid sources and direct-source priority.
`file_conversion_smoke_lab.py` includes two quote-only cases using actual
acknowledgement IDs, all-source-content checks and terminal delivery audits;
native quote bubbles are recorded separately, never assumed. Selected PDF-page
exports additionally compare actual source/output pixels, not filenames alone.
`office-file` rejects non-draft formatted authoring; the owning skill reviews
native rendered words and every page image before sending the selected artifact.
Presentation shading serializes native DrawingML alpha and retains asset paths.

### Verification status
- [x] Five local quoted-source contract regressions and existing quoted-image
  regression pass.
- [x] Seven local document-contract cases pass, including native shade alpha
  and a double-underscore asset filename.
- [ ] Fresh quoted conversational conversions, review-enforcement HTTP cases,
  document visual/delivery gates and full affected release matrix.

Follow-up actual HTTP result: six office boundary cases pass in the Dispatcher
runtime, including private native PDF/three-slide previews and rejection of
unreviewed formatted publication. Fresh quoted PPTX conversion retains all
three original slide headings, but terminal delivery sends one PDF plus text:
**FAIL**; native outbound quote was not recorded. Workbook quote remains
unrun after first-failure stop. See `production-gap-audit.md` for five further
isolated core delivery failures and the disabled-scan runtime setting.

The candidate remains unpromoted; prior live failures remain failures. This
scoped lab is restored against its own baseline: four running images match,
source retains only the original classifier delta with matching checksum,
both replicas' file-gen/attachment files match original source and Zalo remains
logged in with one SSE consumer. Exact conversion fixture output and temporary
source/config transport copies were cleaned. Permanent backups and custom
learned skills are preserved. The production audit's five core regressions
currently fail and require core fixes plus fresh real-transport tests.
