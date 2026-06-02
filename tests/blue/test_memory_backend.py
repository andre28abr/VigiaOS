"""Testes do backend do Vigia Memory (catálogo + cmd + parser Volatility)."""

from __future__ import annotations

import json

from vigia_blue.modules.memory import backend


# ============================================================
# Catálogo
# ============================================================


def test_plugins_catalog():
    pls = backend.plugins()
    assert len(pls) >= 6
    ids = [p.id for p in pls]
    assert len(set(ids)) == len(ids)
    for p in pls:
        assert p.label and p.description
        assert p.os in ("linux", "windows")


def test_get_plugin():
    assert backend.get_plugin("linux.pslist.PsList") is not None
    assert backend.get_plugin("nao.existe") is None


# ============================================================
# Sanity (binário)
# ============================================================


def test_vol_binary_found(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which",
                        lambda b: "/usr/bin/vol" if b == "vol" else None)
    assert backend.vol_binary() == "vol"
    assert backend.vol_available() is True


def test_vol_binary_absent(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    assert backend.vol_binary() is None
    assert backend.vol_available() is False


# ============================================================
# build_vol_cmd
# ============================================================


def test_build_vol_cmd():
    cmd = backend.build_vol_cmd("/tmp/dump.raw", "linux.pslist.PsList",
                                vol_bin="vol")
    assert cmd == ["vol", "-f", "/tmp/dump.raw", "-r", "json",
                   "linux.pslist.PsList"]
    assert isinstance(cmd, list)


# ============================================================
# parse_vol_json
# ============================================================


def test_parse_vol_json_rows_and_columns():
    data = [
        {"PID": 1, "COMM": "systemd"},
        {"PID": 1234, "COMM": "sshd", "PPID": 1},
    ]
    cols, rows = backend.parse_vol_json(json.dumps(data))
    assert rows == data
    # colunas na ordem de aparição, união
    assert cols == ["PID", "COMM", "PPID"]


def test_parse_vol_json_skips_internal_keys():
    data = [{"PID": 1, "__children": [], "COMM": "x"}]
    cols, _ = backend.parse_vol_json(json.dumps(data))
    assert "__children" not in cols
    assert cols == ["PID", "COMM"]


def test_parse_vol_json_garbage():
    assert backend.parse_vol_json("não é json") == ([], [])
    assert backend.parse_vol_json(json.dumps({"x": 1})) == ([], [])  # não é lista
    assert backend.parse_vol_json("") == ([], [])


def test_row_summary():
    cols = ["PID", "COMM", "PPID"]
    assert backend.row_summary(cols, {"PID": 1234, "COMM": "sshd"}) == "1234 · sshd"
    assert backend.row_summary(cols, {}) == "(linha)"


# ============================================================
# run_plugin (sem volatility)
# ============================================================


def test_run_plugin_without_vol(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    res = backend.run_plugin("/tmp/dump.raw", "linux.pslist.PsList")
    assert res.error and res.rows == []


def test_run_plugin_missing_dump(monkeypatch, tmp_path):
    monkeypatch.setattr(backend.shutil, "which",
                        lambda b: "/usr/bin/vol" if b == "vol" else None)
    res = backend.run_plugin(tmp_path / "nao_existe.raw", "linux.pslist.PsList")
    assert "não encontrado" in res.error.lower() or "encontrado" in res.error.lower()


# ============================================================
# Captura de dump (AVML via pkexec)
# ============================================================


def test_avml_path_via_which(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which",
                        lambda b: "/usr/bin/avml" if b == "avml" else None)
    assert backend.avml_path() == "/usr/bin/avml"
    assert backend.avml_available() is True


def test_avml_path_extra_location(monkeypatch, tmp_path):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    fake = tmp_path / "avml"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(0o755)
    monkeypatch.setattr(backend, "_AVML_EXTRA_PATHS", [fake])
    assert backend.avml_path() == str(fake)
    assert backend.avml_available() is True


def test_avml_path_absent(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    monkeypatch.setattr(backend, "_AVML_EXTRA_PATHS", [])
    assert backend.avml_path() is None
    assert backend.avml_available() is False


def test_default_dump_path():
    p = backend.default_dump_path()
    assert str(p).endswith(".lime")
    assert p.parent == backend.TEST_DIR
    assert p.name.startswith("captura-")


def test_build_capture_cmd():
    cmd = backend.build_capture_cmd(
        "/home/u/teste/memory/d.lime", "/usr/bin/avml", owner="u")
    assert isinstance(cmd, list)
    assert cmd[0] == "pkexec"
    assert cmd[1].endswith("_mem_capture.sh")
    assert cmd[2] == "/usr/bin/avml"
    assert cmd[3] == "/home/u/teste/memory/d.lime"
    assert cmd[4] == "u"


def test_capture_dump_no_avml(monkeypatch):
    monkeypatch.setattr(backend, "avml_path", lambda: None)
    res = backend.capture_dump()
    assert res.ok is False
    assert "avml" in res.error.lower()
