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


# ============================================================
# Símbolos do kernel (ISF)
# ============================================================


def test_is_symbols_error():
    assert backend.is_symbols_error(
        "Unable to validate the plugin requirements: "
        "['plugins.PsList.kernel.symbol_table_name']") is True
    assert backend.is_symbols_error("symbol_table_name missing") is True
    assert backend.is_symbols_error("Dump não encontrado") is False
    assert backend.is_symbols_error("") is False


def test_release_from_banner():
    b = "Linux version 6.8.0-1.fc40.x86_64 (builder@fedora) (gcc ...) #1 SMP"
    assert backend._release_from_banner(b) == "6.8.0-1.fc40.x86_64"
    assert backend._release_from_banner("lixo") == ""
    assert backend._release_from_banner("") == ""


def test_symbols_steps_includes_release():
    s = backend.symbols_steps("6.8.0-1.fc40.x86_64")
    assert "6.8.0-1.fc40.x86_64" in s
    assert "dwarf2json" in s
    assert "$(uname -r)" in backend.symbols_steps("")


def test_dwarf2json_path_via_which(monkeypatch):
    monkeypatch.setattr(
        backend.shutil, "which",
        lambda b: "/usr/bin/dwarf2json" if b == "dwarf2json" else None)
    assert backend.dwarf2json_path() == "/usr/bin/dwarf2json"


def test_dwarf2json_path_absent(monkeypatch):
    monkeypatch.setattr(backend.shutil, "which", lambda _b: None)
    monkeypatch.setattr(backend, "_DWARF2JSON_EXTRA", [])
    assert backend.dwarf2json_path() is None


def test_build_vol_cmd_with_symbols(tmp_path):
    cmd = backend.build_vol_cmd("/d.lime", "linux.pslist.PsList", vol_bin="vol",
                                symbols_dir=tmp_path)
    assert cmd == ["vol", "-s", str(tmp_path), "-f", "/d.lime", "-r", "json",
                   "linux.pslist.PsList"]
    cmd2 = backend.build_vol_cmd("/d.lime", "linux.pslist.PsList", vol_bin="vol",
                                 symbols_dir=tmp_path / "nope")
    assert "-s" not in cmd2


def test_dump_banner_parses_linux_version(monkeypatch, tmp_path):
    dump = tmp_path / "d.lime"
    dump.write_text("x")
    monkeypatch.setattr(backend, "vol_binary", lambda: "vol")
    fake = json.dumps([{"Banner": "Linux version 6.8.0-1.fc40 (b@f)"}])
    monkeypatch.setattr(backend.proc, "run", lambda *a, **k: (0, fake, ""))
    assert backend.dump_banner(dump) == "Linux version 6.8.0-1.fc40 (b@f)"


def test_generate_symbols_no_banner(monkeypatch, tmp_path):
    dump = tmp_path / "d.lime"
    dump.write_text("x")
    monkeypatch.setattr(backend, "dump_banner", lambda _d, **k: "")
    res = backend.generate_symbols(dump)
    assert res.ok is False and "banner" in res.message.lower()


def test_generate_symbols_no_dwarf2json(monkeypatch, tmp_path):
    dump = tmp_path / "d.lime"
    dump.write_text("x")
    monkeypatch.setattr(backend, "dump_banner",
                        lambda _d, **k: "Linux version 6.8.0-1.fc40 (b@f)")
    monkeypatch.setattr(backend, "dwarf2json_path", lambda: None)
    res = backend.generate_symbols(dump)
    assert res.ok is False
    assert res.steps and "6.8.0-1.fc40" in res.steps


def test_generate_symbols_no_vmlinux(monkeypatch, tmp_path):
    dump = tmp_path / "d.lime"
    dump.write_text("x")
    monkeypatch.setattr(backend, "dump_banner",
                        lambda _d, **k: "Linux version 6.8.0-1.fc40 (b@f)")
    monkeypatch.setattr(backend, "dwarf2json_path", lambda: "/usr/bin/dwarf2json")
    monkeypatch.setattr(backend, "_find_vmlinux", lambda _r: None)
    res = backend.generate_symbols(dump)
    assert res.ok is False
    assert "debuginfo" in res.message.lower() or "vmlinux" in res.message.lower()
    assert res.steps
