---
name: file-gen
description: "Create/edit office files (xlsx, docx, txt, pdf, csv, pptx, md) via Dispatcher. LLM authors full file content; worker renders. RESULT-ONLY (see media-out)."
---

# File generation → send (result only)

For an existing-file format conversion or page/slide image export, use
`file-convert` instead of authoring new content here.

In direct Hermes sessions without Zalo, use the same rendering API with
`send_zalo=false`; omit `thread_id`. Return the resulting file through the
session's native attachment mechanism or a usable artifact link. Never invent
a Zalo destination, activate Message Worker, or call Zalo send routes. Document
authoring and rendering requirements below are identical in both paths.

Follow skill **`media-out`**. When the user asks to **create / export / edit** an
**xlsx · csv · docx · txt · pdf · md · pptx** file:

## LLM authors content (required)

**You** decide structure, sections, tables, tone, and language.
Use the actual user request as the scope authority. A delegated classifier
brief is an execution suggestion, not additional permission. When they differ,
retain the requested subject, time period and purpose; do not add forecasts,
advice or analysis just to fill the requested page/slide count. Additional pages
can develop the requested details and clearly attributed source context.

### PDF (required format)

For `output_type=pdf`, the office-file `prompt` MUST be one of:

1. A complete **HTML document** (`<!DOCTYPE html>…`) with inline CSS for newly authored PDFs.
2. Raw PDF bytes or `PDF_BASE64:<base64>` only when preserving an existing PDF, not for new document design.

Dispatcher converts HTML→PDF (WeasyPrint). Do **not** send markdown card templates, `IMAGE:` markers, `TITLE:` / `OVERVIEW:` schemas, or expect ReportLab layout.

Choose a composition suited to the subject and requested page count, not a
fixed dashboard template. Use a meaningful image, selective accent color,
clear type hierarchy, and icons when they clarify the content. Keep image
captions as native document text. Reference only a confirmed generated or
approved local asset; never copy an illustrative filename into production HTML.
Use print-supported normal-flow sections and tables, preserve image aspect
ratio, and balance imagery against readable factual text. An illustration is
not a verified photograph of current conditions; label it appropriately.

Never emit placeholders like `<value after search>`. Choose labels and language from the user ask (not a fixed weather schema).

Use one visible document title. Do not repeat a location, subject, or short heading as a standalone line above a hero/title band that already names it. The HTML `<title>` metadata does not count as a visible heading.

Treat print geometry as a release constraint, not decoration. Keep all factual
text in normal document flow. Do not use negative margins, translated offsets,
absolute/fixed positioning, fixed-height text containers, or `overflow:hidden`
around headings, values, labels, tables, or footers. Use `box-sizing:border-box`,
content-driven heights, and explicit internal padding. Icons and decorative
shapes must occupy their own bounded cell and must not cross a text container's
edge. A footer belongs at the visual bottom of the composition; if the content
is short, deliberately distribute vertical spacing or choose a smaller page
size instead of leaving an accidental empty lower third.

Before sending the HTML, audit it top-to-bottom as if no element may overlap
another: the first and last visible glyph must remain inside page margins; every
large value must fit its parent at the declared font size; labels must meet
print contrast; and the same timezone notation must be used everywhere. Remove
any risky positioning rule rather than hoping the renderer will clip it safely.

Keep the sum of table-cell widths, padding, borders, and gaps inside the printed
content width. Do not size each column independently without accounting for
those additions. Keep a metric/row with its values across page boundaries;
avoid a final page consisting only of overflow fragments or sources. Renderer
errors `document_text_outside_page` and `document_sparse_trailing_page` require
recomposition, not bypassing validation, sending a diagnostic file, or changing
to local rendering. Prefer bounded inline SVG icons over emoji whose glyphs may
be missing from the available print fonts. Icon labels remain native text.

### PPTX / DOCX / XLSX / MD (presentation-ready)

For docx/md: compose structured markdown (`#` title, `##` sections,
`- Label: value`, short prose). For PPTX, the model owns the story, slide count,
section order, image choice, and layout. Use one `#` deck title and one `##`
section per content slide; therefore a requested three-slide deck has the title
slide plus exactly two `##` sections. Never substitute PDFs for a PPTX.

For a visual PPTX, first create one scenic still, then include these structural
directives in the PPTX body:

```text
IMAGE: /opt/data/media/out/<generated-image>
LAYOUT: full-bleed
```

`LAYOUT` may be `full-bleed`, `image-left`, `image-right`, or `minimal`. Choose
the layout that fits the actual content and requested visual hierarchy; do not
copy a fixed topic layout. The worker validates paths and renders the selected
composition. Repeat neither the image artifact nor the office artifact.
For xlsx: labeled header row + metric rows with filled values only.

Use the dominant language of the current user message for **every visible word**, including titles, headings, labels, conditions, notes, and captions, unless the user explicitly requests another language. Use measurement units customary for that language/locale as the primary display unless the user specifies units; convert sourced values accurately instead of exposing provider-default units. Do not add bilingual translations or duplicate unit systems merely for decoration.

Keep Vietnamese prose as native Unicode document text, not image-generated
glyphs. PDF HTML uses UTF-8 and an available Vietnamese-capable font such as
Noto Sans; office text remains editable with a Unicode-capable font. Proofread
the authored copy and inspect the rendered output for missing glyphs or spelling
errors. A font supports diacritics but cannot correct misspelled source text.
The image-gen English-copy default does not change the document's language.
Prefer text-free generated illustrations with native captions. If the user
explicitly requests text baked into an embedded image, apply image-gen's image
language policy to that asset only; do not translate the surrounding document.

Fetch live facts with `web_search` when needed. Resolve ambiguous place names against the requested city/region/country before authoring: verify that locality labels and any displayed coordinates/timezone refer to the intended place, retry with a more specific query when they do not, and omit unverified location metadata. For a current snapshot, take measurements from one clearly timestamped current-conditions source; do not merge conflicting values from different providers or timestamps as one observation. Preserve the source timestamp's declared timezone semantics: never label a local timestamp as UTC, never apply a timezone offset twice, and reject or re-query any supposedly current observation that is in the future or is not recent enough for the request.

Retrieve only the fields needed for the requested scope. Once one verified
source provides them, stop expanding the search; do not fetch daily sunrise,
forecast arrays or whole large API responses to decorate a current snapshot.
Keep tool results compact while retaining source, timestamp, timezone and units.
Distinguish measured observations from model-derived current conditions in the
source attribution; an Open-Meteo model value is not a verified station reading.
Apply that distinction to every heading, value label, caption and paragraph,
not only a footnote: model-derived values must not be described as “thực đo”,
“đo được” or “quan trắc”. Open-Meteo's `is_day` indicates day/night only; it
does not establish sunshine or its strength. Do not turn that boolean into a
claim such as “Trời có nắng yếu”. A compact current snapshot needs no causal
summary paragraph; omit unsupported explanations instead of decorating facts.

Translate coded categories from the provider's documented legend, not memory
or an invented compound phrase. For Open-Meteo, consult the WMO table at
https://open-meteo.com/en/docs#weathervariables: 51/53/55 are light/moderate/dense
drizzle; 95 denotes thunderstorm. Code 55 can be rendered in Vietnamese as
“Mưa phùn dày đặc”, never “Mưa phùn dông nhẹ”. Translate the condition and its
intensity together. If the legend cannot be verified, omit an unverified
description rather than inventing one; retain the sourced code if useful.

The requested time and subject scope is a hard boundary. If the user requests only a current snapshot, the artifact MUST contain only current observations: forecast tables, future-day sections, history, unrelated indices, and every recommendation or practical-advice sentence/card/strip are prohibited. A suggested action (for example, telling the reader to bring, wear, avoid, or do something) is a recommendation even when it is based on a current condition rather than a forecast. Include forecasts, history, recommendations, or expanded analysis only when the user asks for them. Never paste search-page chrome into the body. Do not invent causal explanations, event durations, forecasts, or other derived claims; even plausible domain knowledge is excluded unless the user requested analysis and the retrieved evidence directly supports it.

Before the final office-file call, self-review the authored body and correct every violation: one visible title; no standalone repetition of the subject before or after that title; one requested language with locale-appropriate units and no decorative translation; one verified locality and non-future current observation timestamp; one consistent set of current values from the cited source; no unrequested scope; no unsupported interpretation or advice; and no negative/absolute/translated positioning of content. Keep a compact snapshot on one page when its content fits; remove decorative overflow, forced page breaks, and footer fragments that would create accidental extra pages. Balance the layout across the chosen page size: do not leave a large unused lower area when resizing the page, increasing useful spacing, or simplifying the layout would produce a deliberate composition.

### Requested spatial layout

Treat every explicitly positioned content request as a layout constraint, not
as optional styling. Preserve all requested subjects and their relationships.
For ordinary document content, express left/right, top/bottom, centered, row,
column, and multi-region arrangements with normal-flow tables, table cells,
sections, and page breaks that the target renderer supports. Rebalance widths,
padding, typography, and page size when content grows; never omit a region or
allow two regions to cover one another.

When the user explicitly wants information placed over an image inside the
document, use **`image-gen`** to create one complete grounded, full-bleed image
whose prompt contains the exact visible copy and spatial constraints. Let the
image model balance typography and scene composition. Do not create a separate
base plate, post-process it with Pillow, add gray padding, or use risky HTML
positioning. Embed only the final generated image; the document renderer still
owns normal-flow page layout.

## Embedded visuals (pdf|pptx|docx|xlsx|md)

Use a generated visual when the user explicitly requests an image/photo inside
the document, or when a presentation request clearly calls for a designed
visual deck rather than plain text slides. The still remains an internal asset,
not a second deliverable. An attractive layout alone does not create a separate
image response.

1. **`web_search`** for live facts (labeled metrics only).
2. When explicitly requested, create one embeddable still via dispatcher (Omni keys on the worker — never built-in `image_generation`, never `execute_code`, never read `.env`):

Call `POST http://dispatcher:8090/v1/scenic-still` with the model-authored visual
brief, a safe filename, and the requested size. Do not copy a fixed subject,
place, medium, camera style, or layout from skill text.

Use the exact returned `hermes_path`, including its `.assets/` directory, in PDF HTML `<img src="…">` and office `IMAGE:` directives. Never invent a sample filename or substitute the returned basename. A requested image is required: if generation fails, do not claim the visual document is complete or leave a blank hero box. Report the unmet requirement concisely. If a visual was merely optional, remove its entire empty container before delivering the text document. Never mention credentials.
The still is an internal document asset. Do not send it separately; deliver only the requested office file.
3. Compose the **kind-specific body** (filled values only):
   - **pdf** — full HTML; WeasyPrint-safe CSS (`@page`, `display:table` metric rows — avoid Grid/Flex-only layouts).
   - **pptx|docx|md** — structured markdown slides/sections with metric bullets.
   - **xlsx** — clear metric sheet.
4. **`POST /v1/office-file`** with that body, the exact `output_type` / filename
extension, and **`draft=true, send_zalo=false`**. This creates a private draft,
not a delivery. A formatted non-draft request returns
`document_preview_required`; correct the request rather than bypassing review.

Never send diagnostic/test documents or library probes. Designed PDFs,
presentations, Word documents and workbooks require a private first render with
`draft=true, send_zalo=false`: drafts stay outside the public file watcher.
The response `review.pages` contains native rendered text and private page-image
paths. Proofread every visible word, compare all claims with the original request
and source evidence, and inspect every rendered page before delivery. Correct
spelling, grammar, unsupported explanations, unintended scope and layout privately.
Do not run another OCR or regenerate the scenic still just to review native text.
Deliver the selected reviewed artifact through `/v1/send-file` with its exact
returned `hermes_path`; direct sessions return that file natively without sending
through a messaging adapter. Do not publish successive
drafts or create another document after successful delivery. A first attachment
does not prove the request is complete; verify terminal completion and absence
of later sibling attachments when testing.

Never `write_file` draft HTML/markdown under `/tmp`. Compose the body in the tool call JSON only; office-file returns the exact private draft path.

Do **not** rely on the host search→office shortcut for designed presentation docs — you must compose.
Never greet, never `/help`, never narrate tools, never mention missing API keys.
Never silently remap pptx/docx/xlsx → pdf.

## Default (must) — Dispatcher office API

Do **not** install `pypdf` / `weasyprint` / `openpyxl` / `python-pptx` in Hermes. Do **not** call
`skill_view` / `skill_manage` for ambiguous names `pdf` / `docx` / `xlsx` / `pptx`.
Never narrate library installs. Dispatcher owns PDF/PPTX rendering server-side.

```bash
curl -sS -X POST http://dispatcher:8090/v1/office-file \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"<html document or pptx markdown you authored>",
    "thread_id":"<inbound thread id>",
    "source_message_id":"<original inbound source_message_id from delivery_binding>",
    "thread_type":"user",
    "filename":"<safe-name.pdf|safe-name.pptx>",
    "output_type":"pdf",
    "caption":"",
    "draft":true,
    "send_zalo":false
  }'
```

For PPTX: markdown body, `output_type=pptx`, filename ending `.pptx`.
Use one `#` cover title and one `##` section per additional slide; `SUBTITLE:`
sets an optional cover subtitle. Every section retains its own prose and
bullets. Keep copy readable within the requested slide count; the renderer
rejects overflowing copy rather than silently truncating text or sections.
Revise a private draft on that error, never drop required facts or publish an
unreviewed shortened alternative.

Requires Dispatcher with `OFFICE_FILE_GEN=active`; authoring has no Message
Worker dependency. `"ok":true` means the draft was rendered, NOT delivered.
Review all returned pages first. For a messaging destination, then POST
`/v1/send-file` with the exact returned `hermes_path`, the inbound thread ID/type,
`lock_thread=true` and an empty caption. Direct sessions attach that same file
natively, without calling a messaging route. After successful delivery stop;
retry transport using the existing artifact, never render another public copy.
User-facing result per **media-out**: **file only**, no confirmation text.

Dispatcher renders the file locally. Content generation reaches Router Worker,
which prefers the OmniRoute chat combo and may use an explicitly configured
chat-compatible provider when OmniRoute is unavailable.

## Fallback (txt/md only)

If office-file returns 503, write plain text then `send-file` (see prior skill text).

## Do not

- Pass the user's create sentence verbatim as `prompt`
- Dump SERP titles or navigation chrome into the PDF body
- Silently omit a user-required image or leave an empty visual placeholder
- Use ReportLab / markdown-card layouts for PDF

## Related

- `media-out`, `documents`, `image-gen`
