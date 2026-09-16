# 2026-09-15 — safe note mutations and composed-image delivery

## 09:10 +07 — note delete reported “saved” and over-matched wanted records

### Symptom

A user asked to delete every note that is not a Java recruitment posting
(`xoá toàn bộ ghi chú không phải tin tuyển dụng java`). The bot replied
`Đã lưu ghi chú.` (note saved) and the operation removed Java recruitment notes
the user wanted to keep, together with the intended non-recruitment notes.

### Root cause

Two independent defects produced the class:

1. The adapter mapped every successful non-lookup note mutation to the
   `notes.saved` copy, so a delete or update always reported “Đã lưu ghi chú”.
2. A bulk destructive mutation executed whatever one semantic-selection model
   pass returned. That single pass over the real candidate set is not
   deterministic; when it over-matched, wanted records were soft-deleted and the
   user could not have caught it before the write.

### Technical detail

- **Function:** `notes_client.py::execute_note_plan()` at
  `hermes/main/plugins/zalo/notes_client.py:L147`; the destructive confirmation
  boundary now returns `error=confirm` at `notes_client.py:L281–L288` and accepts
  `override_ids` to apply exactly the previewed records.
- **Function:** `adapter.py::_as_mark_pending_note_mutation():L1632`,
  `_as_take_pending_note_mutation()` / `_as_note_mutation_confirm():L1679`,
  `_as_run_confirmed_note_mutation():L1703`; confirmation interception before
  classify at `adapter.py:L2923`; `error=confirm` preview branch at
  `adapter.py:L3201`; delete copy at `adapter.py:L3178`.
- **Key/message:** `ux.json` `notes.saved` was reused for all outcomes; added
  `notes.deleted`, `notes.updated`, `notes.confirm` (`hermes/main/messages/ux.json`).
  New env overrides `ZALO_NOTES_DELETED_MSG`, `ZALO_NOTES_UPDATED_MSG`,
  `ZALO_NOTES_CONFIRM_MSG`.
- **Prompt:** `hermes/main/skills/classify/parts/notes.txt` now forbids
  `match_all` when any qualifier/exclusion is present and requires the complete
  predicate (negation preserved) in `semantic_query`;
  `hermes/main/skills/notes/prompts/select_records.txt` requires per-candidate
  overall-meaning evaluation and rejects excluded categories.
- **Field:** `note_selector.semantic_query` (e.g. `ghi chú không phải tin tuyển
  dụng Java`) and `note_selector.match_all` — an unqualified `match_all` was the
  dangerous shape.
- **Observed evidence:** `note_audit` recorded 28 soft-deletes at
  `2026-09-14 18:39:47 +07` including Java recruitment rows
  (`note_b1bff3e2dcf1`, `note_d51ecd600d9e`, …); the reply row carried
  `delivery_kind=gate` content `Đã lưu ghi chú.`

### AI decision

Bulk destructive record mutations need a human confirmation boundary; a single
LLM selection pass must never be the sole authority for deleting durable user
data. The prompt was corrected to preserve negation, but the host now also
previews the exact matched ids and applies only those after an explicit
standalone confirmation. Prompt wording is not treated as a safety control.

### Fix (core)

`execute_note_plan` previews a bulk delete/update (`len(candidates) > 1`) unless
the plan is already confirmed, and can execute on the exact `override_ids`.
The adapter stores the pending mutation per conversation, replies with a
preview and confirmation token, and executes it only on an explicit
confirmation. Delete/update now emit their own localized outcome copy.

### Todo list

- [x] Reproduce from `note_audit` / `zalo_message_history`.
- [x] Confirm classifier negation variance and selection behavior with live probes.
- [x] Fix source (confirmation boundary + messages + prompts).
- [x] Update `notes_crud_unit`; add `notes_bulk_confirm_unit`.
- [x] Live VPS verification with isolated fixtures (see below).
- [ ] Non-destructive live re-run of the exact original phrase (fixtures only).

### Prevent recurrence

`test/scripts/notes_bulk_confirm_unit.py` proves a bulk preview deletes nothing,
that confirmation applies exactly the previewed ids, that wanted records survive,
and that the vendored `artifact_delivery.py` copy stays in sync.
`notes_crud_unit.py` now asserts the confirmation boundary for bulk update and
delete.

## 09:10 +07 — composed image reported “Hiện chưa tạo được file này”

### Symptom

`vẽ hình ảnh hồ chí minh hiện tại có kèm thông tin thời tiết` returned
`Hiện chưa tạo được file này. Bạn thử lại sau hoặc rút gọn yêu cầu giúp mình.`
The host had generated the image, but delivery failed.

### Root cause

The adapter imports the shared delivery protocol as `from .artifact_delivery
import …`. The Hermes service mounts the repository plugin source read-only
(`docker/docker-compose.yml:L526` `./hermes/main/plugins:/opt/data/plugins:ro`),
which never contained `artifact_delivery.py`. `sync-zalo-plugins.sh:L47` copies
the canonical `architect/lib/artifact_delivery.py` into
`${HERMES_SHARED_DATA}/plugins/zalo`, but that path is shadowed by the mount, so
the running replicas had no such module. The shortcut direct-artifact path then
raised `ModuleNotFoundError`, was caught, and sent the generic media failure
line.

### Technical detail

- **Function:** `adapter.py::_as_autosend_file_claim():L7381` and
  `_as_autosend_file_fp():L7371` import `artifact_delivery`; the direct-send
  path `send_image_file`/`_as_record_attachment_delivery` imports
  `bridge_message_id` at `adapter.py:L9241`.
- **Line anchor:** `docker/docker-compose.yml:L526` (plugin source mount) vs
  `scripts/main/sync-zalo-plugins.sh:L47` (shadowed copy target).
- **File:** added `hermes/main/plugins/zalo/artifact_delivery.py` (byte-identical
  to `architect/lib/artifact_delivery.py`).
- **Log evidence:** `assistant-hermes-2` warning
  `Zalo: shortcut direct artifact send failed: ModuleNotFoundError` at
  `2026-09-14 18:42:31 +07`.

### AI decision

Keep one canonical protocol implementation in `architect/lib` and vendor it into
the plugin package (the repository already vendors `vision_ocr.py` and
`vision_refuse.py` the same way). This matches the read-only source mount instead
of relying on a runtime copy that the mount shadows.

### Fix (core)

`hermes/main/plugins/zalo/artifact_delivery.py` is now part of the plugin source,
so the mounted package resolves the relative import for every replica.

### Todo list

- [x] Reproduce the failure and locate the shadowed copy.
- [x] Vendor the module and guard it with a sync unit assertion.
- [x] Live VPS verification (composed image delivered).

### Prevent recurrence

`notes_bulk_confirm_unit.py` asserts the vendored copy equals the canonical file
after newline normalization. Packaging regressions are visible offline.

## Live VPS verification (authorized lab, `2026-09-15`)

- Composed image: injected `vẽ hình ảnh hồ chí minh hiện tại có kèm thông tin
  thời tiết`; delivered `composed-image-66872937-bbef1439.jpg` (1.5 MB) with an
  acknowledgement-backed `delivered` row (`attachment_kind=image`); no
  `ModuleNotFoundError` and no media failure line.
- Notes: seeded isolated `[LABFIX]` fixtures (two Java recruitment, two
  non-recruitment). `xoá toàn bộ ghi chú LABFIX không phải tin tuyển dụng java`
  returned the confirmation preview listing exactly the two non-recruitment
  fixtures and the reply `Đã xoá 2 ghi chú.` after `XÁC NHẬN`. The two Java
  fixtures stayed active; no operator note was touched. Fixtures were removed
  afterward.
- Offline regression subset (notes, classify assemble, delivery, media gate,
  run-case-index) passes locally; `notes_crud_unit` and
  `notes_bulk_confirm_unit` updated/added.

## 10:30 +07 — image analysis reported a fabricated apology (vision provider unavailable)

### Symptom

`hình gì` (with an attached image) replied
`Xin lỗi, hiện tại tôi không thể xem được hình ảnh này vì hệ thống xử lý ảnh chưa được kết nối...`
instead of describing the image.

### Root cause

OmniRoute's **VISION-BRIDGE** never let the model see the image. Two layers:

1. The `vision-ocr` combo had been refilled (2026-09-15T01:06:11Z) with only
   custom `openai-compatible-chat` (`ai-box/*`) members; OmniRoute's bridge
   logged `No vision-capable provider connected, cannot process image request`
   and replaced the image with `[Image 1]: (unavailable — no vision-capable
   provider connected)`.
2. After an OpenCode-class vision member was restored to the combo, the bridge
   then called its own external Vision API and got
   `Vision API error 401 AUTH_002 Invalid API key`.

`model_capabilities` in the OmniRoute store is empty (0 rows), which is why the
bridge considers every combo member text-only even though chat calls to the same
providers succeed (`opencode-go/qwen3.7-plus`, `publish-go/kimi-k2.7-code`,
`ai-box/kimi-k3` all return HTTP 200 for chat).

### Technical detail

- **Service/route:** OmniRoute `VISION-BRIDGE` log tag; combo `vision-ocr`; app
  log `/app/data/logs/application/app.log`.
- **Store:** OmniRoute `storage.sqlite` table `model_capabilities` (0 rows);
  `combos.data` for `vision-ocr` updated `2026-09-15T01:06:11Z`.
- **Config:** `scripts/main/first-setup-omnirouter.py::list_vision_models()` /
  `_is_vision_capable_model_row()` (catalog `supportsVision`) vs OmniRoute's
  runtime capability table.
- **Do not** add host-side natural-language apology markers: operator direction
  is that when no configured vision model can serve, the host must skip and
  inform (it already sends `Không mô tả được ảnh — gửi lại giúp mình.` on an
  empty read). No phrase list was retained.

### AI decision

A hardcoded model/provider fallback and a natural-language apology phrase list
were both rejected as fragile/non-general. The correct fix is to make the
configured OmniRoute vision provider serve the image; until then the vision cases
are blocked and reported rather than papered over.

### Fix (core)

- `scripts/main/first-setup-omnirouter.py` was left at its catalog-driven source
  (no hardcoded model ids); an intermediate OpenCode-leader experiment was
  reverted.
- The lab-harness report writer
  `test/scripts/zalo_tn_remaining_suite_remote.py` now writes
  `/tmp/hs-suite-report.json` via an atomic temp-file replace, so a prior
  sudo-backed run cannot leave a root-owned file that aborts the suite.

### Live VPS verification (authorized lab)

Case-index filter over the 11 previously-unpassed live gates (candidate
`574ceda`, `ZALO_TEST_USER_ID` supplied at runtime):

| Gate | Script | Result |
|------|--------|--------|
| 26 | zalo_weather_fuel_lab | PASS |
| history | zalo_tn_history_regression | PASS |
| memory-scale-10m | memory_scale_10m_lab | PASS |
| 27-fire | zalo_scheduled_composed_image_lab | PASS |
| archive | zalo_tn_archive_extract_lab | PASS |
| queue-failover | zalo_queue_failover_lab | PASS |
| active-cancel | zalo_active_cancel_lab | PASS |
| remaining | zalo_tn_remaining_suite_lab | PASS (after atomic-report fix) |
| 39 | zalo_tn_visual_weather_pdf_inject | BLOCKED — vision evaluator (OmniRoute vision) |
| flexible-layout | zalo_flexible_composed_layout_lab | BLOCKED — vision evaluator |
| 17 | zalo_user_latency | FAIL — 8056 ms vs 5000 ms SLO |

Case 39 generated a correct one-page Vietnamese PDF (1 page, 673 text chars,
`FINAL_SOURCE_DELIVERY_COUNT 1`) and failed only the vision-scored quality gate
(`Image unavailable`). Flexible-layout produced artifacts and failed only
`FAIL_VISUAL_EVALUATOR`. Both share the OmniRoute vision-bridge root cause.

## 11:00 +07 — visual-PDF oracle false positive and composed-image planner truncation

### Symptom

Two live gates failed: `39-zalo_tn_visual_weather_pdf_inject` reported
`known_weather_code_defects: ["open_meteo_model_mislabeled_measurement"]` on a
PDF that explicitly disclaimed measurement; `zalo_flexible_composed_layout_lab`
returned the media failure line because the composed-image plan was empty.

### Root cause

1. `visual_weather_pdf_gate.model_attribution_defects()` stripped only one
   negation shape (`không phải [dữ liệu] quan trắc|thực đo|đo được`). The live
   disclaimer `không phải số đo từ trạm quan trắc` left `quan trắc` in the
   positive text, so a correct attribution was flagged as a defect.
2. `media_shortcuts._omni_json_plan()` sent structured planning to the reasoning
   `classifier` combo with a fixed 4096-token budget. The model spent the budget
   on reasoning and returned `finish_reason=length` with a truncated JSON body;
   the plan parsed empty and the host sent `Hiện chưa tạo được file này`.

### Technical detail

- **Function:** `visual_weather_pdf_gate.py::model_attribution_defects()` —
  negation regex now also covers `(dữ liệu|số liệu|số đo|kết quả) (từ trạm …)?`
  before the measurement term.
- **Function:** `media_shortcuts.py::_omni_json_plan()` — split into
  `_omni_json_plan_once()` with `reasoning_effort: low` on the request and a
  bounded retry (`finish_reason=length` -> 2× budget, capped 16384).
- **Key:** `_COMPOSITION_PLAN_MAX_TOKENS`: `4096` -> `8192`.
- **Observation:** the live planner logged `finish_reason='length'
  content_chars=558 max_tokens=4096`.

### Fix (core)

Corrected the oracle negation handling and made structured planning request low
reasoning with a bounded retry. Tests updated:
`visual_weather_pdf_gate_unit` (live disclaimer phrasing),
`media_shortcuts_omni_unit` (retry on length, no retry otherwise),
`composed_image_prompt_unit` (new bound). All pass locally.

### Latency gate 17 (not a code defect)

The `hermes` chat call for a two-character message carried **92,644 input
tokens / 116 messages** (accumulated `web_search`/file-read tool results in the
shared DM gateway session, `session_reset.mode: none`,
`proactive_prune_tokens: 0`). A fresh two-message `hermes` call completes in
~1.5 s; the accumulated session takes ~6–9 s, above the 5 s SLO. Bounding the
gateway context is a Hermes/session-configuration decision, not a plugin fix.

## 12:15 +07 — duplicate composed-image delivery and duplicated copy

### Symptom

`zalo_flexible_composed_layout_lab` failed because the two artifacts resolved
to the SAME file, and (after that was fixed) image1 repeated every fact row in a
second `Panels` card.

### Root cause

1. `adapter.py::_as_autosend_turn_files()` never checked whether the current
   destination turn had already delivered media, so after the scheduled-fire
   shortcut sent its composed image the shared-output scan ran again and
   re-sent an older same-thread image under the new source.
2. `media_shortcuts._synthesize_composition_plan()` kept top-level `facts` and a
   panel containing the same rows; the renderer drew both, duplicating the
   informational copy in one region.

### Technical detail

- **Function:** `adapter.py::_as_autosend_turn_files()` — now returns early when
  `autosend.media_sent_in_turn(sent_map, tid, turn_token)` is true (same-turn
  media already delivered).
- **Function:** `media_shortcuts.py::_synthesize_composition_plan()` — when
  `panels` is non-empty, top-level fact rows whose `label:value` also appears in
  a panel are dropped (the panel carries the shared region; distinct rows stay).
- **Key:** `_COMPOSITION_PLAN_MAX_TOKENS`: `4096` -> `8192`; planner now sends
  `reasoning_effort: low` and retries once on `finish_reason=length`.

### Verification

- `autosend_unit` (window + same-turn guard), `media_shortcuts_omni_unit`
  (dedupe + retry), and `composed_image_prompt_unit` pass locally.
- Live rerun: artifacts became distinct (`b832ac29`/`e18eb53e`) and image1
  became one left region with correct data and language
  (`image1_left_single_region=true`, `language_correct=true`). The evaluator
  still returns `spelling_correct=false` / `quality_score=6` on minor copy
  polish (e.g. `30.7° C` spacing, a lowercase title fragment) — model copy
  quality, not a code defect.

### Gate 39 note

The weather-PDF request is a *designed* PDF (`process_original_message=true`), so
it correctly routes through the async Hermes workflow rather than the trivial
literal-fill office shortcut. The turn's slowness came from the job model writing
and running a local script (`/opt/data/media/gen_danang_weather_pdf.py`, which
errored) instead of using the file-gen/dispatcher office path; the PDF was then
generated and delivered correctly at ~227 s, past the gate deadline.

## 13:00 +07 — English-only image overlays

### Symptom

The flexible-layout visual evaluator kept returning `spelling_correct=false`.
Diagnosis showed image1 (English) had no errors while image2 (explicitly
requested Vietnamese) misspelled diacritics: `Thời thời`→`Thời tiết`,
`Mâu rào nhé`→`Mưa rào nhẹ`, `Gio`→`Gió`, `Cập thập tướt`→`Cập nhật`.

### Fix (per operator direction)

Image overlays are now always English. `image-runtime.json`
(`composition_system`, `composition_user_template`, `composition_render_template`)
no longer lets an explicit request change the image-text language; only exact
quoted wording supplied by the user may be rendered verbatim. English overlays
also use a Latin money form (`VND`, `VND per liter`) instead of the `đ`/`₫`
glyph, which raster models render unreliably. The flexible-layout gate's
scheduled request drops its explicit "bằng tiếng Việt" image-text directive, and
its evaluator now requires English copy in both branches.

### Result

Live verdict moved from `quality_score 6` to `7` with `language_correct=true`
and all layout/legibility checks true. `spelling_correct` remains false from
diffusion text-rendering defects on image2 (`Overcosd`→`Overcast`,
`NEE`→`NE`, `69 %`→`69%`) while image1 is clean. Guaranteeing spelling needs a
bounded post-generation vision check with a next-member retry, which the current
design deliberately does not perform.

## 13:15 +07 — autosend guard used before its import (regression)

### Symptom

A user asked `hồ chí minh hôm nay có mưa không?` in Zalo and got no reply; the
next messages received `Xin lỗi, tin trước xử lý quá lâu (hơn 15 phút)…` and
`Phiên làm việc bị gián đoạn, vui lòng thử lại sau.`

### Root cause

Registry f1fbabb added a same-turn media guard to
`adapter.py::_as_autosend_turn_files()` that calls `media_sent_in_turn(...)`
**before** the `from .autosend import (... media_sent_in_turn ...)` statement in
the same function. Python binds the name as a local for the whole function, so
every turn raised `UnboundLocalError: cannot access local variable
'media_sent_in_turn' where it is not associated with a value`. The gateway
logged `Error handling message:` and the adapter `queued part failed`; the
durable FIFO never advanced, so the queue turn deadline (900 s) answered later
messages with the timeout copy and the session was reported interrupted.

### Technical detail

- **Function:** `adapter.py::_as_autosend_turn_files()` — guard moved to after
  the autosend import block (before `grace = self._as_env_float(...)`).
- **Log anchors:** `gateway.platforms.base: [Zalo] Error handling message:
  cannot access local variable 'media_sent_in_turn'`;
  `hermes_plugins.zalo_platform.adapter: Zalo: queued part failed`.
- **Queue keys:** `assistant:gate:qactive`, durable FIFO (Valkey);
  `ZALO_QUEUE_TURN_TIMEOUT_S=900`.
- **Regression guard:** `test/scripts/autosend_unit.py` asserts the same-turn
  guard text appears after the `media_sent_in_turn,` import inside
  `_as_autosend_turn_files` (use-before-import cannot recur).

### Fix (core)

Order the guard after the import. Live VPS: the failing message returned the
correct HCMC weather answer, a follow-up answered normally, no
`media_sent_in_turn` errors, bridge `loggedIn` with one SSE consumer.

## 14:00 +07 — quote-reply resend misrouted and lost the quoted block

### Symptom

A user quote-replied `gửi lại` (resend) to the bot's previous weather answer and
the bot replied it saw no earlier content and asked what to resend.

### Root cause

Two compounding defects:
1. The classifier saw the quoted weather text and classified the turn by the
   quoted topic, returning `task_hint=search` / `web_search` instead of normal
   chat for the current instruction `gửi lại`.
2. On a live-search plan the adapter rebuilt `event.text` from the bare ask
   (`f"{bare_q}\n\n[Current lookup execution contract]…"`), discarding the
   `[Quoted message]` block it had just built. The model therefore never saw the
   quoted content and answered that none existed.

### Technical detail

- **Function:** `adapter.py::_as_queue…/_run_turn()` — the quote block is now
  built once into `quote_block` and kept in both rebuild texts
  (`f"{bare_q}{quote_block}\n\n[Current lookup execution contract]…"` and the
  search-then-note contract).
- **Prompt:** `hermes/main/skills/classify/parts/core.txt` CURRENT TURN — a
  resend/repeat/re-show request is normal chat referring to the quote;
  “Classify it by the current instruction, never by the topic of the quoted
  text.”
- **Bake:** `architect/models/router-worker/config/classify.json` regenerated
  via `scripts/main/sync_router_worker_skills.py`.
- **Fields:** classify `task_hint`/`task_type` (search → chat) for
  `gửi lại + [Quoted message]`.
- **Regression:** `test/scripts/quote_resend_unit.py`.

### Fix (core)

Classify by the current instruction (not the quoted topic) and preserve the
`[Quoted message]` block through the live-search contract rebuild. Live VPS: the
same `gửi lại` quote-reply now resends the quoted weather content, and the
Hermes turn carries the quote block with no forced search contract.

## 15:00 +07 — scope authorization tests and learn-approval wiring

### Scope authorization (tests)

Added `test/scripts/zalo_scope_authz_unit.py` (13 checks) and
`test/cases/77-scope-isolation-learn-approval.md`:
- a group member's current scope is exactly their group and a DM user's is
  exactly their DM;
- a non-admin cannot read another group/DM or `all` (fails closed before any
  record fetch);
- only the operator admin resolves another registered group/DM or `all`, and an
  unknown reference fails closed;
- schedules never cross a conversation (a group schedule is absent from a
  member's DM list; admin `all` sees both).

### Learn approval (core + tests)

- `architect/tools/ingest/app.py`: `LEARN_REQUIRE_APPROVE` used a falsey set
  (`0/false/no/off`), so the stack's standard switch value **`inactive` was
  treated as ON** (approval required). It now uses the on-value parse
  (`1/true/yes/on/active`), so `inactive`/`0` are both off.
- `docker/docker-compose.yml`: the ingest default now derives from the channel
  state — `LEARN_REQUIRE_APPROVE=${LEARN_REQUIRE_APPROVE:-${ENABLE_ZALO:-inactive}}`.
- `scripts/main/install-component.sh`: installing `message`/`zalo` sets
  `LEARN_REQUIRE_APPROVE=active`; removing it sets `inactive`.
- `.env.example`: documents the flag and the channel-derived default.
- `test/scripts/learn_approval_unit.py` (10 checks) covers the parse, the
  always-pending Zalo submit, the scan auto/approve branches, and the install
  wiring.

### Live VPS verification

- `POST /v1/learn/submit` -> `status=pending`, `notified=true` (admin told to
  `!zalo learn approve <id>`); reject cleans the fixture.
- Ingest rebuild: active channel -> `LEARN_REQUIRE_APPROVE=True`; `inactive` and
  `0` -> `False`; `1` -> `True`.
- Host `.env` set to `LEARN_REQUIRE_APPROVE=active` for the channel-active lab.

Existing hosts that still carry the retired `LEARN_REQUIRE_APPROVE=0` default
should run `bash run.sh install message` (or set `LEARN_REQUIRE_APPROVE=active`)
to require approval while a channel is active.

## 15:30 +07 — env switch parsers must treat inactive as off

### Symptom / class

Several boolean environment switches used a falsey set (`0/false/no/off`) that
omitted the stack's standard off value `inactive`, so an operator setting
`inactive` silently turned the switch ON.

### Fixed switches

- `architect/models/dispatcher/app.py::_timing_enabled()` (`MESSAGE_TIMING_RECORD`)
  now uses the on-value parse.
- `architect/memory/memory-worker/app.py::_timing_add()` (`MESSAGE_TIMING_RECORD`)
  now uses the on-value parse.
- `hermes/main/plugins/zalo/adapter.py::_zalo_rate_limit_cfg()` (`ZALO_RATE_LIMIT`)
  and `_as_already_answering_max()` (`HERMES_MAX_ANSWERING`/`HERMES_MAX_INFLIGHT`)
  now accept `inactive`.
- `hermes/main/plugins/zalo/queue_history.py::enabled()` (`ZALO_HISTORY_POSTGRES`),
  `session_memory.py::enabled()` (`ZALO_SESSION_VALKEY`), and
  `workflow_client.py::workflow_enabled()` (`HERMES_WORKFLOW`/`ZALO_WORKFLOW`)
  now use the on-value parse.
- `hermes/main/plugins/zalo/gate_valkey.py::from_env()` (`ASSISTANT_STORE_URL`/
  `REDIS_URL`) accepts `inactive` as disabled.

### Rule

On = `active|1|true|yes|on`; everything else (including `inactive`) is off. This
matches `run.sh::_env_active` and the ingest `LEARN_REQUIRE_APPROVE` fix.
Non-boolean enums (`ZALO_GROUP_MODE` = mention|all|off, approval decisions) keep
their own value sets.

### Regression

`test/scripts/env_switch_semantics_unit.py` (10 checks): behavior checks for the
importable switches plus source checks for the service parsers.

### Not applicable

`architect/zalo-api/app.py` `{"off","open","all"}` and `{"reject","deny","no"}`
are command/approval enums, not environment switches.

## 16:00 +07 — current docs carried stale configuration values

### Symptom / class

Current (non-historical) docs stated values that no longer matched the deployed
configuration, so an operator following them would set a switch wrong or copy an
environment key that does not exist.

### Corrections

- `LEARN_REQUIRE_APPROVE` was documented as "defaults to 0" / "when 0". It is
  channel-derived (`docker/docker-compose.yml` default
  `...:-${ENABLE_ZALO:-inactive}`; `scripts/main/install-component.sh` writes
  `active` for `message`/`zalo`, `inactive` otherwise) and uses the standard
  on-value parse. Off (`0`/`inactive`) auto-ingests scan/midnight; on stages
  pending. Zalo submit is always pending. Updated in
  `docs/07-worker-feature-catalog.md`, `architect/tools/README.md`,
  `architect/tools/ingest/README.md`, `hermes/main/setup/README.md`,
  `test/cases/12-skills-auto-learn.md`.
- `docs/config/DEFAULTS.md`: `VISION_OCR_COMBO` is not a key (real:
  `OMNIROUTER_VISION_COMBO`), `EMBEDDING_MODEL` is not a key (real:
  `EMBED_MODEL`; `OPENAI_EMBEDDING_MODEL` is the vendor pin), and `SKILLS_DIR`
  is not an env var (skills are a compose bind mount at `/opt/data/skills`).
- `AGENT_RULES.md` referenced retired alias `model-router`; the router is
  `router-worker`.
- `hermes/main/skills/file-gen/SKILL.md` referenced `HERMES_WRITE_SAFE_ROOT`,
  which exists nowhere in code.

### Method

Audited every env-shaped token in current `.md` files against `.env.example`,
compose, and code, then re-scanned current docs for retired names (`9Router`,
`Mem0`, `model-router`, `PaddleOCR`, `Tesseract`, `ComfyUI`, `video-gen`,
`Ollama`). Remaining mentions are intentional "retired/not supported"
statements; Ollama is still a real optional last-hop router-worker fallback
(`OLLAMA_BASE_URL`).

## 18:20 +07 — retention moved to env; daily compact and idle session rollover

### Symptom / class

Operational retention lived in OpenBao, so changing the backup rotation window
required editing the secret store. Memory housekeeping only ran when the optional
media worker was installed, and a short-term conversation session never rotated:
the Valkey TTL was refreshed on every turn, so an actively-used chat kept
unbounded short-term context across days.

### Root cause

- `scripts/main/openbao_common.py` seeded `BACKUP_RETENTION_DAYS` and
  `MEMORY_STAGED_RETENTION_DAYS` into OpenBao `RUNTIME_DEFAULTS` and scrubbed them
  from the host `.env` (`ENV_SCRUB_KEYS`), so they were not host-editable.
- `run.sh::do_compact()` began with `need_media compact || return 1` and the
  `assistant-compact.timer` unit was installed only inside the media/jobs branch.
- `architect/memory/session/app.py::put_session()` always extended the stored
  message list and refreshed the Redis TTL; there was no idle or daily boundary.

### Technical detail

- **Function:** `architect/memory/session/app.py::get_session()` / `put_session()` —
  now call `_should_rollover(updated_at, now, _idle_rollover_seconds())`; idle
  sessions are archived via `_archive_best_effort(...)` then replaced (PUT) or
  reported absent (GET).
- **Lines:** `architect/memory/session/app.py:L58–L145` (GET/PUT + helpers),
  `L161–L210` (`_archive_session_data`).
- **Key:** `SESSION_IDLE_ROLLOVER_SECONDS` default `3600` (0 disables);
  `BACKUP_RETENTION_DAYS` default `7`; `MEMORY_STAGED_RETENTION_DAYS` default `7`.
- **Key migration:** `scripts/main/openbao_common.py` `RETIRED_RUNTIME_KEYS`
  replaces `RUNTIME_DEFAULTS`; `first-setup-openbao.py::purge_obsolete()` removes
  them from OpenBao KV.
- **Script:** `run.sh::do_compact()`/`do_install_timers()` — compact is ungated and
  its daily timer is always installed; backup/compact units gained
  `EnvironmentFile=-${STACK_ROOT}/.env`.
- **Compose:** `docker/docker-compose.yml` session service passes
  `SESSION_IDLE_ROLLOVER_SECONDS=${SESSION_IDLE_ROLLOVER_SECONDS:-3600}`.

### AI decision

Retention is configuration, not a secret (§11.1): moved to the host environment
with a 7-day default and an idempotent OpenBao purge rather than leaving two
sources. Idle rollover was implemented in the session service (the short-term
source of truth the plugin hydrates from) rather than in the adapter, so every
caller gets the boundary. GET also invalidates so the first post-idle turn does
not hydrate stale context; archive failure is fail-soft and never breaks a turn.

### Fix (core)

Backup/compaction windows are host-editable and default to 7; memory compact runs
daily regardless of the media worker; a conversation idle for `1h` starts a new
session and the old one is archived to long-term memory.

### Todo list

1. Read governance + map retention/compact/session paths.
2. Move retention to env; purge OpenBao; wire units + compose.
3. Ungate and always-install daily compact.
4. Add idle rollover to the session service.
5. Unit tests (rollover, compact, openbao contract).
6. VPS verify + monitor logs; then MR → develop → main.

### Prevent recurrence

`test/scripts/session_idle_rollover_unit.py` asserts the predicate boundaries,
GET/PUT rollover, the disabled case, and env documentation;
`test/scripts/compact_daily_unit.py` asserts compaction is ungated and the timer
is always installed; `test/scripts/openbao_common_unit.py` asserts retention is
host-config and purged from OpenBao.

### Related stale test found during the full run

`test/scripts/media_capability_skills_unit.py` still asserted the retired
overlay-language contract ("Default … to concise English" / "an explicit
image-text language … overrides that default"). The shipped
`hermes/main/skills/classify/parts/image-runtime.json` `composition_system`
implements the English-only policy recorded in the 2026-09-15 13:00 changelog
(always English; an explicit other-language request does not override; only exact
quoted copy is verbatim). The assertions were updated to that contract — a test
alignment, not a weakening. This was pre-existing on `main` and `develop`.

## 19:00 +07 — Grafana dashboards consolidated; routing/queue metrics

### Symptom / class

Grafana shipped four dashboards with overlapping content (`assistant-overview`
already contained every `assistant-stack` panel, and `assistant-file-flow`
duplicated the logs dashboard), and the overview had a duplicated OmniRoute row.
Routing/queue/latency signals (LLM latency, errors, router selection, provider
fallback, queue depth, Qdrant latency, schedule lag) had no panels.

### Root cause

The overview and stack dashboards were built from the same queries and never
merged; the OmniRoute row was copy-pasted twice. The requested signals had no
metric source: Traefik metrics were not enabled/scraped, Router Worker exposed
no `/metrics`, and stack-exporter did not time Qdrant or read queue/schedule state.

### Technical detail

- **Files:** merged `assistant-file-flow` panels into
  `config/monitor/grafana/dashboards/json/assistant-logs.json`; removed
  `assistant-stack.json` and `assistant-file-flow.json`; added a
  *Routing, queues & latency* row to `assistant-overview.json`.
- **Traefik:** `architect/edge/traefik/traefik.yml` (+ `.acme`) `metrics.prometheus`
  with `entryPoint: metrics` on `:8082`.
- **Router Worker:** `architect/models/router-worker/metrics.py` and
  `app.py::_record_llm_metrics` middleware + `GET /metrics`
  (`router_worker_llm_requests_total`, `router_worker_llm_latency_seconds`,
  `router_worker_router_selection_total`, `router_worker_provider_fallback_total`).
- **stack-exporter:** `assistant_qdrant_query_seconds`, `assistant_queue_depth{queue}`,
  `assistant_schedule_lag_seconds` (`app.py::render_metrics`).
- **Scrape:** `config/monitor/prometheus.yml` jobs `router-worker:8096`, `traefik:8082`.
- **Keys:** `SCHEDULE_URL`, `WORKFLOW_QUEUE_KEY=wf:queue`,
  `ZALO_GATE_QUEUE_PATTERN=assistant:gate:q:*` (stack-exporter).

### AI decision

Consolidated by nature (logs to logs, metrics to overview) rather than dumping
log panels into the metrics dashboard. Added the missing sources at the central
services (Router Worker middleware avoids touching the routing hot path;
stack-exporter derives queue/latency without new services). Tokens reuse
OmniRoute counters instead of duplicating them; failure-derived metrics fail soft.

### Fix (core)

Two dashboards remain; the overview surfaces request/LLM/routing/queue/Qdrant/
schedule signals from real sources.

### Todo list

1. Merge dashboards; drop duplicates. 2. Enable Traefik + Router Worker metrics.
3. Extend stack-exporter. 4. Add panels. 5. Unit tests. 6. VPS verify.

### Prevent recurrence

`test/scripts/monitor_metrics_unit.py` asserts the dashboard set, the overview
expressions, scrape jobs, Traefik metrics config, and stack-exporter metrics;
`test/scripts/router_worker_metrics_unit.py` asserts the Router Worker metric
surface and route ordering. Remaining (not yet emitted): worker_duration,
OCR_duration, embedding_duration, Zalo_delivery_latency, queue_wait.

## 20:00 +07 — Grafana admin password was left on the insecure fallback

### Symptom / class

Grafana ran on `changeme-set-in-env` (the Compose fallback): `GRAFANA_ADMIN_PASSWORD`
was empty in `.env` and absent from OpenBao, and `check-security.sh` only probed
the unauthenticated `/api/health`, so the weak credential was never reported.

### Root cause

- Host `.env` had `GRAFANA_ADMIN_PASSWORD=` (empty); `first-setup-openbao` skips
  empty/`CHANGE_ME` values, so it was never seeded to OpenBao.
- Compose used `${GRAFANA_ADMIN_PASSWORD:-changeme-set-in-env}` (silent weak
  default), unlike required secrets that fail closed with `${VAR:?}`.
- No setup step generated or required it, and Grafana applies the admin password
  only on first DB init, so an existing `grafana_data` volume kept the old hash
  even after the environment value changed.

### Technical detail

- **Script:** `scripts/main/ensure-grafana-admin.py` — placeholder detection,
  generation, idempotent `.env` upsert.
- **Function:** `run.sh::ensure_grafana_admin_password()` /
  `_reset_grafana_admin_password()`, called after
  `do_prepare_openbao_env_for_compose` in the `up` case and `do_update`.
- **Key:** `GRAFANA_ADMIN_PASSWORD` (also in `SEED_KEYS`,
  `scripts/main/openbao_common.py`).
- **Compose:** `docker/docker-compose.security.yml` `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-...}`.
- **CLI:** `grafana-cli admin reset-admin-password` (Grafana persists the admin
  hash in `grafana_data`; the env value applies on first init only).
- **Check:** `scripts/main/check-security.sh` authenticated `/api/user` probe.

### AI decision

Kept the Compose `:-` fallback (a `:?` would break Compose parsing on hosts
without Grafana) but removed the silent path: generate + seed a real secret,
reconcile the DB, and verify the login. Reused the existing seed/scrub lifecycle
instead of adding a second credential store.

### Fix (core)

Enabling the monitor guarantees a real Grafana admin secret in OpenBao; the DB is
reconciled on `up`/`update`/`install`, and `check-security` fails on the
fallback/empty credential.

### Todo list

1. Reproduce (fallback in use, absent from OpenBao). 2. Generator + run.sh hook.
3. Grafana DB reset. 4. check-security authenticated probe. 5. Unit + VPS verify.

### Prevent recurrence

`test/scripts/grafana_admin_password_unit.py` asserts generation, idempotency, and
the run.sh/check-security wiring; `check-security.sh` fails closed on the fallback.

## 20:30 +07 — Grafana panels stacked in one column; regrouped by role

### Symptom / class

The consolidated overview dashboard rendered as a long single column: every panel
had `gridPos.x=0`, and full-width `row` separators split the page every few
panels without any clear role grouping.

### Root cause

The consolidation post-processing (`anneal_rows`) assigned `x=0` to every panel
while only advancing `y`, so panels could never sit side by side.

### Technical detail

- **Files:** `config/monitor/grafana/dashboards/json/assistant-overview.json`,
  `assistant-logs.json`.
- **Change:** panels are packed left-to-right using their existing widths (wrap
  at 24 columns) inside explicit role sections: Stack health, Traffic (Traefik),
  Hardware, OmniRoute LLM usage, Routing/queues/latency.
- **Change:** Traefik by-label targets use `{entrypoint="{{entrypoint}}"}`,
  `{service="{{service}}"}` and `{router="{{router}}"}` legend formats.
- **Result:** overview panels=49 sections=5 height=124; logs panels=12.

### AI decision

Kept the section rows (the operator wanted role grouping) but packed panels
within each section so a section is not one panel per line. Matched panels to
sections by exact title to avoid substring collisions (e.g. "LLM latency p95"
is not Traffic "Latency p95").

### Fix (core)

Overview renders as five role sections with packed panels; Traefik legends show
`{label="value"}`.

### Todo list

1. Pack panels. 2. Add role sections. 3. Legend formats. 4. Layout guard test.
5. VPS confirm via Grafana API.

### Prevent recurrence

`test/scripts/monitor_metrics_unit.py` asserts the section titles, that no
section is empty, that panels are not a single column, that no panel exceeds 24
columns, and the `{label="value"}` legend formats.
