---
name: documents
description: "MODE=documents — LLM authors file content; Dispatcher office-file renders. RESULT-ONLY (see media-out)."
---

# Documents (md · txt · pdf · docx · xlsx · csv)

Follow skill **`media-out`** when `OFFICE_FILE_GEN=active`. Hard refuse music/video.
**Images** → **`image-gen`**.
**Convert an existing file** → **`file-convert`**. Do not recreate its subject or send an intermediate artifact.

Direct Hermes sessions use the same Dispatcher with `send_zalo=false` and no
thread ID; formatted documents additionally require `draft=true` and the
file-gen native-text/page-image review before exact-artifact native delivery. Zalo and
Message Worker are optional delivery adapters, not document prerequisites.

## Author before create (required)

**You** write the full file body: structure, headings, tables, and facts. Use `web_search`
for live data when the ask needs it. Pass your composed text as `prompt` — not the user's
bubble verbatim, and not a fixed template.

Use one clear title, concise subtitle, meaningful sections, and label/value facts
where suitable. Select hierarchy and density for the content rather than a fixed
topic template. PDF must use authored HTML/CSS; DOCX/PPTX/XLSX use structured
markdown that the renderer can turn into styled headings, cards/tables, readable
spacing, and presentation-safe pages/slides/sheets.

For HTML/PDF, keep factual content in normal flow with content-driven heights.
Never use negative margins, translated offsets, absolute/fixed positioning, or
hidden overflow on text containers. Keep icons in bounded cells, verify large
values fit with padding, maintain print-safe contrast, and balance the full page
instead of leaving an accidental empty lower third. Use one timezone notation
consistently. These are generic layout invariants, not a topic template.

## Render privately, review, then deliver (required)

Follow `file-gen` for the two-phase authoring/review contract. Always use
Dispatcher (HTML-to-PDF and Office engines are installed). Do **not** use Hermes
`pdf`/`docx`/`xlsx` skills (name collisions) or `pip install` inside the agent.

```bash
curl -sS -X POST http://dispatcher:8090/v1/office-file \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt":"<full content you authored>",
    "thread_id":"<inbound thread_id>",
    "thread_type":"user",
    "filename":"<safe>.pdf",
    "caption":"",
    "output_type":"pdf",
    "draft":true,
    "send_zalo":false
  }'
```

This response certifies rendering, not delivery. Inspect every returned
`review.pages` native text and private page image; correct copy/evidence/layout
privately. Then send the selected exact artifact once via `/v1/send-file` with
the inbound destination, `lock_thread=true` and an empty caption, or attach it
natively in a direct session. Never expose alternate drafts or an embedded still.

Examples:

| User | Call |
|------|------|
| tạo 1 file pdf và điền vào số 1 | `prompt` with your layout (e.g. a line containing `1`), `filename":"so_1.pdf"` |
| tạo 1 file text điền số 1 | same API (parser picks `.txt`) or `filename":"number.txt"` |

## Do not

- Narrate steps / claim success without `"ok":true`
- Ask for approval / invent “cannot send file on Zalo”
- Dump server paths
- Claim visual quality without rendering/inspecting the result
- Silently change the requested file extension when a renderer fails
- Impose weather card, dashboard, or screen layouts unless the user asked for that style
