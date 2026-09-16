---
name: media-file
description: "Conditional media/file router: still diffusion always Omni combo image-gen; vision reads use vision-ocr combo or hermes when inactive. Never silently bypass an active worker."
---

# Media / file skill

Forced stack policy:

```text
IF Media/File Worker ACTIVE:
  still-image diffusion → OmniRoute /images/generations model image-gen
  vision / office → vision-ocr combo (ingest/jobs/dispatcher/Zalo) + dispatcher office-file
ELSE:
  still-image diffusion → OmniRoute /images/generations model image-gen (same combo)
  vision / chat fallback → Omni/OmniRoute combo hermes
  unsupported → explicit failure (never pretend success)
```

```text
Hermes → this skill
           ├── generate_media (always) → image-gen (Omni combo image-gen)
           ├── worker active
           │                     ├── vision-ocr (router-worker combo)
           │                     └── file create/convert
           └── worker inactive → combo hermes on Omni/OmniRoute (vision/chat only; not still diffusion)
```

| skill_action | Active worker | Inactive worker |
|---|---|---|
| `generate_media` | OmniRoute `POST /v1/images/generations` model `image-gen` (skill HD `size`) | Same: `model=image-gen` (never `hermes` for stills) |
| `process_file` / `process_image` | ingest/dispatcher vision-ocr combo | Omni/OmniRoute multimodal `hermes` |
| `create_file` | `file-gen` / office via dispatcher | report unavailable rendering capability; never install local office tools |

Existing-file conversion routes to `file-convert`, not image generation or
new document authoring. Exporting document pages/slides to images is conversion.
All capability routes work in direct Hermes sessions without Zalo; use native
artifact delivery and omit messaging identities. Rendering still requires the
shared file worker, not Message Worker.

## Must follow

1. Result-only after a file (`media-out`).
2. Output under `/opt/data/media/out/`.
3. Preserve host-bound `thread_id` only for messaging delivery; never invent one for direct sessions.
4. A supplied-image transformation routes to `image-edit`. Video creation and video editing are unavailable and must not be claimed or substituted.
5. Complex multi-panel briefs: `multi-purpose` (plan with `hermes`).

## Related

- `image-gen`, `image-edit`, `vision-ocr`, `embedding`, `multi-purpose`, `file-gen`, `file-convert`, `media-out`
