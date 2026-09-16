# -*- coding: utf-8 -*-
"""Unit: Zalo autosend file window (no VPS)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hermes" / "main" / "plugins" / "zalo"))

from autosend import canonical_send_name, file_in_send_window  # noqa: E402

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    t0 = 1_000_000.0
    # File during the part
    if not file_in_send_window(t0 + 10, t0, t0):
        print("FAIL in-part file")
        return 1
    # File just before part clock (dispatcher write vs send race)
    if not file_in_send_window(t0 - 3, t0, t0, grace_s=8):
        print("FAIL grace")
        return 1
    # Next compound part: part_t0 jumped; seq_t0 keeps the image eligible
    part2 = t0 + 120
    img = t0 + 110
    if not file_in_send_window(img, part2, t0, grace_s=8):
        print("FAIL seq window")
        return 1
    # Unrelated old file
    if file_in_send_window(t0 - 600, part2, t0, grace_s=8):
        print("FAIL old file kept")
        return 1
    # Isolated job ceiling: later file belongs to the next job
    if file_in_send_window(t0 + 800, t0, t0, grace_s=8, ceiling=t0 + 100):
        print("FAIL ceiling leaked later file")
        return 1
    if not file_in_send_window(t0 + 50, t0, t0, grace_s=8, ceiling=t0 + 100):
        print("FAIL in-job file under ceiling")
        return 1
    from autosend import (  # noqa: E402
        bridge_response_ok,
        claimed_composite_is_terminal,
        existing_media_path,
        file_ready_for_send,
        looks_invalid_param,
        prefer_remuxed_video,
        video_dedupe_stem,
        workflow_job_defers_sidecars,
    )

    if file_ready_for_send(t0, t0 + 0.1, min_age_s=0.8):
        print("FAIL growing file treated ready")
        return 1
    if not file_ready_for_send(t0, t0 + 2.0, min_age_s=0.8):
        print("FAIL settled file not ready")
        return 1
    if not looks_invalid_param("Tham số không hợp lệ"):
        print("FAIL invalid param detect")
        return 1

    if not bridge_response_ok({"success": True, "result": {"msgId": "1"}}):
        print("FAIL plugin success")
        return 1
    if bridge_response_ok({"error": "file not found: x"}):
        print("FAIL plugin error body")
        return 1
    if bridge_response_ok({"success": True, "error": "file not found"}):
        print("FAIL success+error")
        return 1
    if bridge_response_ok({}):
        print("FAIL empty body")
        return 1
    if not claimed_composite_is_terminal("/tmp/weather-report.pdf"):
        print("FAIL claimed PDF not terminal")
        return 1
    if not claimed_composite_is_terminal("/tmp/weather-report.docx"):
        print("FAIL claimed DOCX not terminal")
        return 1
    if claimed_composite_is_terminal("/tmp/weather-hero.jpg"):
        print("FAIL image sidecar treated as final document")
        return 1
    if not workflow_job_defers_sidecars(
        {"task_type": "file_processing", "output_type": "pdf"}
    ):
        print("FAIL PDF workflow did not defer sidecars")
        return 1
    if not workflow_job_defers_sidecars({"file_format": ".pptx"}):
        print("FAIL PowerPoint workflow did not defer sidecars")
        return 1
    if workflow_job_defers_sidecars(
        {"task_type": "media_generation", "output_type": "image"}
    ):
        print("FAIL image workflow deferred final media")
        return 1
    import tempfile

    if video_dedupe_stem("city.mp4") != video_dedupe_stem("city.zalo.mp4"):
        print("FAIL video stem")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "city.mp4"
        remux = Path(tmp) / "city.zalo.mp4"
        raw.write_bytes(b"x" * 2000)
        remux.write_bytes(b"y" * 2000)
        if Path(prefer_remuxed_video(str(raw))).name != "city.zalo.mp4":
            print("FAIL prefer remux")
            return 1

    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "scene.png"
        png.write_bytes(b"png")
        hit = existing_media_path(str(Path(tmp) / "scene.jpg"))
        if Path(hit).name != "scene.png":
            print("FAIL sibling png")
            return 1
    adapter_source = (
        ROOT / "hermes" / "main" / "plugins" / "zalo" / "adapter.py"
    ).read_text(encoding="utf-8")
    claimed_guard = adapter_source.find(
        "if claimed_composite_is_terminal(str(dest_send)):"
    )
    next_candidate = adapter_source.find("continue", claimed_guard)
    if claimed_guard < 0 or "break" not in adapter_source[claimed_guard:next_candidate]:
        print("FAIL adapter can fall through from claimed document to image sidecar")
        return 1
    # Both the local send-name cache and shared session claim must terminate;
    # otherwise the first cache hit bypasses the shared-claim guard entirely.
    import ast
    tree = ast.parse(adapter_source)
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)
                  and node.name == "_as_autosend_turn_files")
    guard = next(node for node in ast.walk(method) if isinstance(node, ast.If)
                 and isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Attribute)
                 and node.test.func.attr == "_as_autosend_already_sent")
    assert any(isinstance(node, ast.Break) for statement in guard.body for node in ast.walk(statement))
    assert canonical_send_name("/tmp/report.docx") == "report.docx"
    assert canonical_send_name("/tmp/send-report.docx") == "report.docx"
    assert canonical_send_name("/tmp/send-send-report.docx") == "report.docx"
    from autosend import media_sent_in_turn  # noqa: E402
    sent = {"t1": 5}
    if not media_sent_in_turn(sent, "t1", 5):
        print("FAIL current-turn media not detected")
        return 1
    if media_sent_in_turn(sent, "t1", 6):
        print("FAIL stale media token treated as current")
        return 1
    if media_sent_in_turn(sent, "t2", 5):
        print("FAIL other-thread media treated as current")
        return 1
    if media_sent_in_turn(sent, "t1", 0):
        print("FAIL zero token treated as media sent")
        return 1
    if "media_sent_in_turn(sent_map, tid, turn_token)" not in adapter_source:
        print("FAIL adapter lacks same-turn media autosend guard")
        return 1
    # The guard must run AFTER the autosend import in the same function; using
    # the name first raises UnboundLocalError and aborts the whole turn.
    start = adapter_source.index("async def _as_autosend_turn_files(")
    next_def = adapter_source.find("\n    def ", start)
    next_async = adapter_source.find("\n    async def ", start)
    ends = [pos for pos in (next_def, next_async) if pos > 0]
    body = adapter_source[start:min(ends)] if ends else adapter_source[start:]
    guard_at = body.find("media_sent_in_turn(sent_map, tid, turn_token)")
    import_at = body.find("media_sent_in_turn,")
    if not (0 <= import_at < guard_at):
        print("FAIL same-turn guard precedes its autosend import (UnboundLocalError)")
        return 1
    print("PASS autosend window and staged-copy identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
