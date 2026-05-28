"""Tests pro modulo settings.py do Vigia Hub.

Cobre:
- Load/save round-trip
- Defaults quando arquivo nao existe
- Permissoes 0600
- Autostart install/remove/is_enabled
- autostart_sync (helper)
- Conteudo do .desktop (Exec line, GNOME hints)
- Robustez contra JSON corrompido
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vigia_hub import settings


# ============================================================
# Fixtures: isola STATE_PATH e AUTOSTART_PATH em tmp_path
# ============================================================


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Aponta STATE_PATH e AUTOSTART_PATH pra tmp_path."""
    state_dir = tmp_path / "vigia-hub"
    state_path = state_dir / "settings.json"
    autostart_dir = tmp_path / "autostart"
    autostart_path = autostart_dir / "vigia-hub.desktop"

    monkeypatch.setattr(settings, "STATE_DIR", state_dir)
    monkeypatch.setattr(settings, "STATE_PATH", state_path)
    monkeypatch.setattr(settings, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(settings, "AUTOSTART_PATH", autostart_path)

    return {
        "state_dir": state_dir,
        "state_path": state_path,
        "autostart_dir": autostart_dir,
        "autostart_path": autostart_path,
    }


# ============================================================
# load_settings / save_settings
# ============================================================


class TestLoadSettings:
    def test_returns_defaults_when_no_file(self, isolated_paths):
        s = settings.load_settings()
        assert s.autostart is False
        assert s.show_tray is False
        assert s.start_minimized is False
        assert s.password_lock is False
        # v0.6.0 — novos defaults
        assert s.theme == "system"
        assert s.auto_lock_minutes == 0

    def test_loads_existing_file(self, isolated_paths):
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(
            json.dumps({
                "autostart": True,
                "show_tray": True,
                "start_minimized": False,
                "password_lock": True,
            })
        )
        s = settings.load_settings()
        assert s.autostart is True
        assert s.show_tray is True
        assert s.start_minimized is False
        assert s.password_lock is True

    def test_returns_defaults_on_corrupted_json(self, isolated_paths):
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text("{not valid json")
        s = settings.load_settings()
        # Defaults sem crash
        assert s.autostart is False

    def test_handles_missing_keys(self, isolated_paths):
        """Backward compat: arquivos antigos sem todas as chaves."""
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(json.dumps({"autostart": True}))
        s = settings.load_settings()
        assert s.autostart is True
        assert s.show_tray is False  # default
        assert s.theme == "system"  # default
        assert s.auto_lock_minutes == 0

    def test_invalid_theme_falls_back_to_system(self, isolated_paths):
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(
            json.dumps({"theme": "neon-blue"})
        )
        s = settings.load_settings()
        assert s.theme == "system"

    def test_auto_lock_clamped_to_range(self, isolated_paths):
        """auto_lock_minutes deve ser clampado em [0, 120]."""
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(
            json.dumps({"auto_lock_minutes": 99999})
        )
        s = settings.load_settings()
        assert s.auto_lock_minutes == 120

    def test_auto_lock_negative_clamped_to_zero(self, isolated_paths):
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(
            json.dumps({"auto_lock_minutes": -5})
        )
        s = settings.load_settings()
        assert s.auto_lock_minutes == 0

    def test_auto_lock_non_int_falls_back_to_zero(self, isolated_paths):
        isolated_paths["state_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["state_path"].write_text(
            json.dumps({"auto_lock_minutes": "ten"})
        )
        s = settings.load_settings()
        assert s.auto_lock_minutes == 0


class TestSaveSettings:
    def test_saves_and_roundtrips(self, isolated_paths):
        s = settings.Settings(autostart=True, show_tray=True)
        assert settings.save_settings(s) is True
        # Roundtrip
        loaded = settings.load_settings()
        assert loaded.autostart is True
        assert loaded.show_tray is True

    def test_creates_state_dir_if_missing(self, isolated_paths):
        assert not isolated_paths["state_dir"].exists()
        settings.save_settings(settings.Settings(autostart=True))
        assert isolated_paths["state_dir"].is_dir()

    def test_state_file_is_0600(self, isolated_paths):
        """LGPD: arquivo nao pode ser lido por outros usuarios."""
        settings.save_settings(settings.Settings(password_lock=True))
        st = os.stat(isolated_paths["state_path"])
        # Mode bits low 9: rwxrwxrwx
        assert (st.st_mode & 0o777) == 0o600

    def test_atomic_write(self, isolated_paths):
        """Arquivo .tmp nao deve sobreviver apos save."""
        settings.save_settings(settings.Settings())
        tmp_files = list(isolated_paths["state_dir"].glob("*.tmp"))
        assert tmp_files == []


# ============================================================
# Autostart helpers
# ============================================================


class TestAutostartIsEnabled:
    def test_false_when_no_file(self, isolated_paths):
        assert settings.autostart_is_enabled() is False

    def test_true_when_file_exists(self, isolated_paths):
        isolated_paths["autostart_dir"].mkdir(parents=True, exist_ok=True)
        isolated_paths["autostart_path"].write_text("[Desktop Entry]\n")
        assert settings.autostart_is_enabled() is True


class TestAutostartInstall:
    def test_creates_desktop_file(self, isolated_paths):
        assert settings.autostart_install() is True
        assert isolated_paths["autostart_path"].is_file()

    def test_contains_exec_vigia_hub(self, isolated_paths):
        settings.autostart_install()
        content = isolated_paths["autostart_path"].read_text()
        assert "Exec=vigia-hub" in content

    def test_minimized_flag_in_exec(self, isolated_paths):
        settings.autostart_install(minimized=True)
        content = isolated_paths["autostart_path"].read_text()
        assert "Exec=vigia-hub --minimized" in content

    def test_default_no_minimized_flag(self, isolated_paths):
        settings.autostart_install(minimized=False)
        content = isolated_paths["autostart_path"].read_text()
        assert "Exec=vigia-hub\n" in content
        assert "--minimized" not in content

    def test_has_gnome_autostart_hints(self, isolated_paths):
        settings.autostart_install()
        content = isolated_paths["autostart_path"].read_text()
        assert "X-GNOME-Autostart-enabled=true" in content
        assert "X-GNOME-Autostart-Delay=" in content

    def test_creates_autostart_dir_if_missing(self, isolated_paths):
        assert not isolated_paths["autostart_dir"].exists()
        settings.autostart_install()
        assert isolated_paths["autostart_dir"].is_dir()


class TestAutostartRemove:
    def test_removes_existing_file(self, isolated_paths):
        settings.autostart_install()
        assert isolated_paths["autostart_path"].is_file()
        assert settings.autostart_remove() is True
        assert not isolated_paths["autostart_path"].exists()

    def test_no_error_when_already_removed(self, isolated_paths):
        # Sem arquivo, ainda retorna True (idempotente)
        assert settings.autostart_remove() is True


class TestAutostartSync:
    def test_sync_true_installs(self, isolated_paths):
        assert settings.autostart_sync(enabled=True) is True
        assert isolated_paths["autostart_path"].is_file()

    def test_sync_false_removes(self, isolated_paths):
        settings.autostart_install()
        assert settings.autostart_sync(enabled=False) is True
        assert not isolated_paths["autostart_path"].exists()

    def test_sync_minimized_passes_through(self, isolated_paths):
        settings.autostart_sync(enabled=True, minimized=True)
        content = isolated_paths["autostart_path"].read_text()
        assert "--minimized" in content
