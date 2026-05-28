"""Tests pro CLI `vigia` (vigia_hub.cli).

Cobre dispatch dos subcomandos status / backup / restore / version e o
default (sem subcomando -> status).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vigia_hub import backup, cli, settings, status


@pytest.fixture
def fake_status(monkeypatch: pytest.MonkeyPatch):
    """gather() retorna um SuiteStatus deterministico."""
    st = status.SuiteStatus(
        version="9.9.9",
        autostart=True,
        tray=False,
        lock=True,
        auto_lock_minutes=10,
        tools=[
            status.ToolStatus("antivirus", "Antivirus", "vigia-antivirus", True),
            status.ToolStatus("dashboard", "Dashboard", "vigia-dashboard", False),
        ],
        key_binaries=[
            status.BinaryStatus("clamscan", True),
            status.BinaryStatus("lynis", False),
        ],
        last_antivirus=status.ScanInfo(
            "antivirus", "2026-05-28T10:00:00", "há 2 h", True, "limpo · 100 arquivos"
        ),
        last_rootkit=None,
        backups_count=1,
        backups_latest_human="há 1 h",
    )
    monkeypatch.setattr(cli.status_mod, "gather", lambda: st)
    return st


class TestStatusCommand:
    def test_status_returns_zero(self, fake_status, capsys):
        rc = cli.main(["status"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Vigia Suite" in out
        assert "9.9.9" in out

    def test_status_json(self, fake_status, capsys):
        rc = cli.main(["status", "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["version"] == "9.9.9"
        assert data["tools_total"] == 2

    def test_no_args_defaults_to_status(self, fake_status, capsys):
        rc = cli.main([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Vigia Suite" in out


class TestVersionCommand:
    def test_version(self, capsys):
        rc = cli.main(["version"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "vigia" in out
        assert status.__version__ in out


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isola dirs do backup pro CLI (cli.backup_mod == modulo backup)."""
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    config_home.mkdir()
    data_home.mkdir()
    monkeypatch.setattr(backup, "CONFIG_HOME", config_home)
    monkeypatch.setattr(backup, "DATA_HOME", data_home)
    monkeypatch.setattr(backup, "BACKUP_DIR", data_home / "vigia-hub" / "backups")
    # cria uma fonte
    hub = config_home / "vigia-hub"
    hub.mkdir(parents=True)
    (hub / "settings.json").write_text(json.dumps({"autostart": False}))
    return tmp_path


class TestBackupCommand:
    def test_backup_creates_file(self, env, capsys):
        dest = env / "out.zip"
        rc = cli.main(["backup", str(dest)])
        assert rc == 0
        assert dest.exists()

    def test_backup_default_dir(self, env, capsys):
        rc = cli.main(["backup"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Backup criado" in out


class TestRestoreCommand:
    def test_restore_roundtrip(self, env, capsys):
        # cria backup
        dest = env / "bk.zip"
        cli.main(["backup", str(dest)])
        # apaga fonte
        import shutil as _sh
        _sh.rmtree(env / "config" / "vigia-hub")
        # restaura
        rc = cli.main(["restore", str(dest)])
        assert rc == 0
        assert (env / "config" / "vigia-hub" / "settings.json").exists()

    def test_restore_dry_run(self, env, capsys):
        dest = env / "bk.zip"
        cli.main(["backup", str(dest)])
        rc = cli.main(["restore", str(dest), "--dry-run"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "seriam restaurados" in out

    def test_restore_missing_file_nonzero(self, env, capsys):
        rc = cli.main(["restore", str(env / "nope.zip")])
        assert rc == 1


class TestParser:
    def test_build_parser_ok(self):
        parser = cli.build_parser()
        args = parser.parse_args(["status", "--json"])
        assert args.cmd == "status"
        assert args.json is True
