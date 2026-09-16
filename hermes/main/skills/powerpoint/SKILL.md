---
name: powerpoint-dispatcher
description: Create or revise presentation files through the shared document renderer in direct Hermes or messaging sessions.
---

# Presentation routing

Use `file-gen` for presentation authoring and Dispatcher `/v1/office-file`
with `output_type=pptx`. Author the complete slide story, exact requested slide
count, visual choice, layout, and native text in the user's language. Retrieve
fresh evidence when needed and stay within the user's requested time scope.

Do not install or run python-pptx, PIL, LibreOffice, or bundled presentation
scripts in the Hermes agent. Rendering and dependency ownership belong to the
Dispatcher. Do not convert a requested presentation to PDF or send a scenic
asset separately. Deliver only the requested completed file, once.

Direct sessions use `send_zalo=false` without a messaging destination. Messaging
sessions use the host-bound destination and the single-delivery rules in
`media-out`. Do not require Zalo or Message Worker for direct file creation.
