#!/usr/bin/env python3
"""Unit: archive member path containment (INV-SEC-001 / INV-SEC-003).

Exercises the real ``architect/tools/ingest/archive_media.py`` guard: traversal
and absolute member names are rejected and never escape the destination
directory, and only media members are extracted.
"""
from __future__ import annotations

import importlib.util
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "architect" / "tools" / "ingest" / "archive_media.py"


def _load():
    spec = importlib.util.spec_from_file_location("archive_media_unit", MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    m = _load()

    # basename normalizes separators and keeps only the last segment
    assert m.member_basename("a/b/c.pdf") == "c.pdf"
    assert m.member_basename("a\\b\\c.pdf") == "c.pdf"

    # traversal / absolute member names are rejected
    for bad in ("", "/etc/passwd", "/abs.pdf", "../x", "a/../../b", "a/..", "..",
                ".", "a/../b", "..\\x", "a/..\\b"):
        assert m.member_path_safe(bad) is False, bad
    for good in ("report.pdf", "doc/report.pdf", "a/b/c.png"):
        assert m.member_path_safe(good) is True, good

    # only media members are processable; nested archives are skipped
    assert m.is_media_member("report.pdf")
    assert m.is_media_member("photo.PNG")
    assert m.is_media_member("notes.txt")
    assert not m.is_media_member("nested.zip")
    assert not m.is_media_member("bundle.tar.gz")
    assert not m.is_media_member("noext")
    assert not m.is_media_member("../secret.pdf")
    assert not m.is_media_member("/abs.pdf")

    # Executable/script members are never extracted (INV-SEC-006)
    for exe in ("payload.exe", "run.bat", "a.cmd", "a.ps1", "lib.dll", "setup.msi", "x.sh", "y.js"):
        assert not m.is_media_member(exe), exe

    assert m.archive_kind("a.zip") == "zip"
    assert m.archive_kind("a.tar.gz") == "tar"
    assert m.archive_kind("a.tgz") == "tar"
    assert m.archive_kind("a.txt") == "none"

    # Real extraction: traversal members never leave dest_dir.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out = tmp / "out"
        archive = tmp / "in.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("good.pdf", "%PDF-1.4 ok")
            zf.writestr("../evil.pdf", "%PDF-1.4 evil")
            zf.writestr("/abs.pdf", "%PDF-1.4 abs")
            zf.writestr("a/../../x.txt", "escaped")
            zf.writestr("nested.zip", "PK")
            zf.writestr("payload.exe", "MZ")
        result = m.extract_media_members(archive, out)
        assert result["ok"] is True, result
        assert [w["name"] for w in result["written"]] == ["good.pdf"], result["written"]
        assert (out / "00_good.pdf").is_file()
        assert not (tmp / "evil.pdf").exists()
        assert not (tmp / "x.txt").exists()
        assert not (tmp.parent / "evil.pdf").exists()

    # Resource limits: oversized members are skipped and the member count is capped.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out = tmp / "out2"
        archive = tmp / "many.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            for i in range(5):
                zf.writestr(f"f{i}.txt", "0123456789")
            zf.writestr("big.pdf", "x" * 50)
        m.MAX_MEDIA_MEMBERS = 2
        m.MAX_MEMBER_BYTES = 20
        m.MAX_TOTAL_BYTES = 1000
        try:
            capped = m.extract_media_members(archive, out)
        finally:
            m.MAX_MEDIA_MEMBERS = 30
            m.MAX_MEMBER_BYTES = 25 * 1024 * 1024
            m.MAX_TOTAL_BYTES = 80 * 1024 * 1024
        names = [w["name"] for w in capped["written"]]
        assert "big.pdf" not in names, names  # 50 > MAX_MEMBER_BYTES(20)
        assert len(names) == 2, names  # MAX_MEDIA_MEMBERS cap

    # Source contract: destination is built from the basename and members are
    # gated by is_media_member (no path escape by construction).
    src = MODULE.read_text(encoding="utf-8")
    assert 'dest_dir / f"{len(written):02d}_{base}"' in src
    assert "if not is_media_member(name):" in src
    assert "if size > MAX_MEMBER_BYTES:" in src
    assert "if len(written) >= MAX_MEDIA_MEMBERS:" in src

    print("archive_member_path_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
