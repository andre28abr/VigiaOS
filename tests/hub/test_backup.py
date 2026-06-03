"""Tests pro modulo backup.py do Vigia Hub.

Cobre:
- backup_sources: so lista o que existe
- create_backup: zip valido, 0600, MANIFEST presente, roundtrip
- restore_backup: extrai de volta, perms 0600, dry_run nao escreve
- Seguranca: rejeita Zip-Slip (.., absoluto, dir fora de vigia)
- list_backups + default_backup_name
"""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from vigia_hub import backup


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isola CONFIG_HOME, DATA_HOME e BACKUP_DIR em tmp_path."""
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    backup_dir = data_home / "vigia-hub" / "backups"
    config_home.mkdir(parents=True, exist_ok=True)
    data_home.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(backup, "CONFIG_HOME", config_home)
    monkeypatch.setattr(backup, "DATA_HOME", data_home)
    monkeypatch.setattr(backup, "BACKUP_DIR", backup_dir)

    return SimpleNamespace(
        config_home=config_home,
        data_home=data_home,
        backup_dir=backup_dir,
        tmp=tmp_path,
    )


def _seed_sources(env) -> None:
    """Cria dados de exemplo nas fontes de backup."""
    hub_cfg = env.config_home / "vigia-hub"
    hub_cfg.mkdir(parents=True, exist_ok=True)
    (hub_cfg / "settings.json").write_text(
        json.dumps({"autostart": True}), encoding="utf-8"
    )
    av_data = env.data_home / "vigia-antivirus"
    av_data.mkdir(parents=True, exist_ok=True)
    (av_data / "scan-2026.json").write_text(
        json.dumps({"infected_files": 0}), encoding="utf-8"
    )


# ============================================================
# backup_sources
# ============================================================


class TestBackupSources:
    def test_empty_when_nothing_exists(self, env):
        assert backup.backup_sources() == []

    def test_lists_existing_dirs(self, env):
        _seed_sources(env)
        sources = backup.backup_sources()
        dirs = {s.dirname for s in sources}
        assert "vigia-hub" in dirs
        assert "vigia-antivirus" in dirs

    def test_ignores_nonexistent(self, env):
        _seed_sources(env)
        sources = backup.backup_sources()
        # vigia-installer nao foi criado (so' hub+antivirus) -> nao aparece
        assert all(s.dirname != "vigia-installer" for s in sources)


# ============================================================
# create_backup
# ============================================================


class TestCreateBackup:
    def test_fails_when_no_sources(self, env):
        ok, msg, path = backup.create_backup()
        assert ok is False
        assert path is None
        assert "Nada para backup" in msg

    def test_creates_zip_in_default_dir(self, env):
        _seed_sources(env)
        ok, msg, path = backup.create_backup()
        assert ok is True
        assert path is not None
        assert path.exists()
        assert path.parent == env.backup_dir
        assert path.suffix == ".zip"

    def test_zip_is_0600(self, env):
        """LGPD: backup pode conter dado sensivel — so o dono le."""
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        st = os.stat(path)
        assert (st.st_mode & 0o777) == 0o600

    def test_zip_contains_manifest_and_files(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
            assert "MANIFEST.json" in names
            assert "config/vigia-hub/settings.json" in names
            assert "data/vigia-antivirus/scan-2026.json" in names
            manifest = json.loads(zf.read("MANIFEST.json"))
        assert manifest["format"] == "vigia-backup"
        assert "created_at" in manifest
        assert "hub_version" in manifest

    def test_explicit_dest_gets_zip_suffix(self, env):
        _seed_sources(env)
        dest = env.tmp / "meu-backup"  # sem .zip
        ok, _, path = backup.create_backup(dest)
        assert ok
        assert path.suffix == ".zip"
        assert path.exists()

    def test_no_tmp_file_left(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        leftovers = list(env.backup_dir.glob("*.tmp"))
        assert leftovers == []


# ============================================================
# restore_backup (roundtrip)
# ============================================================


class TestRestoreRoundtrip:
    def test_restore_recreates_files(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok

        # Apaga as fontes
        import shutil as _sh
        _sh.rmtree(env.config_home / "vigia-hub")
        _sh.rmtree(env.data_home / "vigia-antivirus")

        ok, msg, labels = backup.restore_backup(path)
        assert ok is True
        assert (env.config_home / "vigia-hub" / "settings.json").is_file()
        assert (env.data_home / "vigia-antivirus" / "scan-2026.json").is_file()
        assert labels  # algum label humano

    def test_restored_files_are_0600(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        backup.restore_backup(path)
        settings_file = env.config_home / "vigia-hub" / "settings.json"
        st = os.stat(settings_file)
        assert (st.st_mode & 0o777) == 0o600

    def test_restored_content_matches(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        backup.restore_backup(path)
        data = json.loads(
            (env.config_home / "vigia-hub" / "settings.json").read_text()
        )
        assert data == {"autostart": True}

    def test_dry_run_does_not_write(self, env):
        _seed_sources(env)
        ok, _, path = backup.create_backup()
        assert ok
        import shutil as _sh
        _sh.rmtree(env.config_home / "vigia-hub")

        ok, msg, labels = backup.restore_backup(path, dry_run=True)
        assert ok is True
        # Nada foi escrito
        assert not (env.config_home / "vigia-hub").exists()
        assert labels


# ============================================================
# Seguranca: Zip-Slip
# ============================================================


class TestRestoreSecurity:
    def _make_zip(self, path: Path, entries: dict[str, str]) -> None:
        with zipfile.ZipFile(path, "w") as zf:
            for name, content in entries.items():
                zf.writestr(name, content)

    def test_rejects_missing_manifest(self, env):
        z = env.tmp / "nomanifest.zip"
        self._make_zip(z, {"config/vigia-hub/x.json": "{}"})
        ok, msg, _ = backup.restore_backup(z)
        assert ok is False
        assert "MANIFEST" in msg

    def test_rejects_parent_traversal(self, env):
        z = env.tmp / "evil.zip"
        self._make_zip(z, {
            "MANIFEST.json": "{}",
            "config/../../evil.txt": "pwned",
        })
        ok, msg, _ = backup.restore_backup(z)
        assert ok is False
        # Nada escrito fora
        assert not (env.tmp / "evil.txt").exists()

    def test_rejects_absolute_path(self, env):
        z = env.tmp / "abs.zip"
        self._make_zip(z, {
            "MANIFEST.json": "{}",
            "/tmp/evil.txt": "pwned",
        })
        ok, _, _ = backup.restore_backup(z)
        assert ok is False

    def test_rejects_non_vigia_dir(self, env):
        z = env.tmp / "weird.zip"
        self._make_zip(z, {
            "MANIFEST.json": "{}",
            "config/notvigia/x.json": "{}",
        })
        ok, _, _ = backup.restore_backup(z)
        assert ok is False

    def test_rejects_unknown_kind(self, env):
        z = env.tmp / "kind.zip"
        self._make_zip(z, {
            "MANIFEST.json": "{}",
            "etc/vigia-hub/x.json": "{}",
        })
        ok, _, _ = backup.restore_backup(z)
        assert ok is False

    def test_nonexistent_file(self, env):
        ok, msg, _ = backup.restore_backup(env.tmp / "nope.zip")
        assert ok is False
        assert "não encontrado" in msg


# ============================================================
# list_backups + helpers
# ============================================================


class TestListBackups:
    def test_empty_when_no_dir(self, env):
        assert backup.list_backups() == []

    def test_lists_after_create(self, env):
        _seed_sources(env)
        backup.create_backup()
        backups = backup.list_backups()
        assert len(backups) == 1
        assert backups[0]["name"].startswith("vigia-backup-")
        assert backups[0]["size"] > 0

    def test_default_backup_name_format(self):
        name = backup.default_backup_name()
        assert name.startswith("vigia-backup-")
        assert name.endswith(".zip")
