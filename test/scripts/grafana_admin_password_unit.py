#!/usr/bin/env python3
"""Unit: Grafana admin password is generated/kept and never left on the fallback."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "main" / "ensure-grafana-admin.py"


def _load():
    spec = importlib.util.spec_from_file_location("ensure_grafana_admin_unit", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(mod, *, active, env_pw, env_file_text=None):
    """Invoke main() in a temp STACK_ROOT and return (stdout, .env text)."""
    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        if env_file_text is not None:
            env_path.write_text(env_file_text, encoding="utf-8")
        saved = {k: os.environ.get(k) for k in ("STACK_ROOT", "ENABLE_GRAFANA", "GRAFANA_ADMIN_PASSWORD")}
        os.environ["STACK_ROOT"] = tmp
        os.environ["ENABLE_GRAFANA"] = "active" if active else "inactive"
        os.environ["GRAFANA_ADMIN_PASSWORD"] = env_pw
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = mod.main()
            out = buf.getvalue().strip()
            text = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return rc, out, text


def main() -> int:
    mod = _load()

    assert mod.is_placeholder("") is True
    assert mod.is_placeholder("CHANGE_ME_GRAFANA") is True
    assert mod.is_placeholder("changeme-set-in-env") is True
    assert mod.is_placeholder("A-real-secret") is False

    # upsert replaces an existing line and appends when absent
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / ".env"
        p.write_text("A=1\nGRAFANA_ADMIN_PASSWORD=CHANGE_ME_GRAFANA\nB=2\n", encoding="utf-8")
        mod.upsert(p, "GRAFANA_ADMIN_PASSWORD", "secret-x")
        assert "GRAFANA_ADMIN_PASSWORD=secret-x" in p.read_text(encoding="utf-8")
        assert "A=1" in p.read_text(encoding="utf-8") and "B=2" in p.read_text(encoding="utf-8")
        mod.upsert(p, "GRAFANA_ADMIN_NEW", "v")
        assert "GRAFANA_ADMIN_NEW=v" in p.read_text(encoding="utf-8")

    # Grafana inactive: no work, no output
    rc, out, text = _run(mod, active=False, env_pw="")
    assert rc == 0 and out == "" and text == ""

    # Enabled + placeholder everywhere: generates, writes .env, prints value
    rc, out, text = _run(mod, active=True, env_pw="", env_file_text="GRAFANA_ADMIN_PASSWORD=CHANGE_ME_GRAFANA\n")
    assert rc == 0 and len(out) >= 16
    assert f"GRAFANA_ADMIN_PASSWORD={out}" in text
    assert "CHANGE_ME_GRAFANA" not in text

    # Enabled + real env value (OpenBao-injected): keep, print, do not rewrite
    rc, out, text = _run(mod, active=True, env_pw="kept-secret", env_file_text="GRAFANA_ADMIN_PASSWORD=kept-secret\n")
    assert rc == 0 and out == "kept-secret"
    assert text == "GRAFANA_ADMIN_PASSWORD=kept-secret\n"

    # Enabled + empty env but real .env value: keep, print, do not rewrite
    rc, out, text = _run(mod, active=True, env_pw="", env_file_text="GRAFANA_ADMIN_PASSWORD=from-env-file\n")
    assert rc == 0 and out == "from-env-file"
    assert "from-env-file" in text

    # Wiring: run.sh seeds before Compose; check-security verifies the login.
    run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
    assert "ensure_grafana_admin_password()" in run_sh
    assert run_sh.count("ensure_grafana_admin_password\n") >= 2 or run_sh.count("ensure_grafana_admin_password") >= 3
    assert "reset-admin-password" in run_sh
    check = (ROOT / "scripts" / "main" / "check-security.sh").read_text(encoding="utf-8")
    assert "changeme-set-in-env" in check
    assert "/api/user" in check
    compose = (ROOT / "docker" / "docker-compose.security.yml").read_text(encoding="utf-8")
    assert "GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-" in compose
    assert "GRAFANA_ADMIN_PASSWORD:?" not in compose
    import sys

    sys.path.insert(0, str(ROOT / "scripts" / "main"))
    from openbao_common import SEED_KEYS  # noqa: E402

    assert "GRAFANA_ADMIN_PASSWORD" in SEED_KEYS

    print("grafana_admin_password_unit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
