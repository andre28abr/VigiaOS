"""Tests pro modulo tray do Vigia Hub.

Cobre:
- checks.appindicator_lib_available com mock de subprocess.run
- checks.appindicator_extension_enabled com mock de gnome-extensions
- checks.tray_can_work agregando os 3 sinais
- checks.install_command / enable_extension_command (formato)
- manager.TrayManager state (is_running, start, stop)
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vigia_hub.tray import checks, manager


# ============================================================
# checks.appindicator_lib_available
# ============================================================


class TestAppIndicatorLibAvailable:
    @patch("vigia_hub.tray.checks.subprocess.run")
    def test_lib_available_when_subprocess_zero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert checks.appindicator_lib_available() is True

    @patch("vigia_hub.tray.checks.subprocess.run")
    def test_lib_unavailable_when_subprocess_nonzero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        assert checks.appindicator_lib_available() is False

    @patch("vigia_hub.tray.checks.subprocess.run")
    def test_lib_unavailable_on_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("python3", 5)
        assert checks.appindicator_lib_available() is False

    @patch("vigia_hub.tray.checks.subprocess.run")
    def test_lib_unavailable_when_python_missing(self, mock_run):
        mock_run.side_effect = FileNotFoundError("python3")
        assert checks.appindicator_lib_available() is False


# ============================================================
# checks.appindicator_extension_enabled
# ============================================================


class TestAppIndicatorExtensionEnabled:
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_no_gnome_extensions_cli(self, mock_which):
        mock_which.return_value = None
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is False
        assert enabled is False

    @patch("vigia_hub.tray.checks.subprocess.run")
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_extension_not_installed(self, mock_which, mock_run):
        """`gnome-extensions list` nao retorna o UUID -> nao instalada."""
        mock_which.return_value = "/usr/bin/gnome-extensions"
        # primeira chamada: list (sem o UUID)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="other-extension@example.com\n",
        )
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is False
        assert enabled is False

    @patch("vigia_hub.tray.checks.subprocess.run")
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_extension_installed_but_disabled(self, mock_which, mock_run):
        """UUID em `list` mas nao em `list --enabled`."""
        mock_which.return_value = "/usr/bin/gnome-extensions"
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="appindicatorsupport@rgcjonas.gmail.com\nother@x.com\n",
            ),
            MagicMock(
                returncode=0,
                stdout="other@x.com\n",  # nao habilitada
            ),
        ]
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is True
        assert enabled is False

    @patch("vigia_hub.tray.checks.subprocess.run")
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_extension_enabled(self, mock_which, mock_run):
        """UUID em `list` E em `list --enabled` -> habilitada."""
        mock_which.return_value = "/usr/bin/gnome-extensions"
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="appindicatorsupport@rgcjonas.gmail.com\n",
            ),
            MagicMock(
                returncode=0,
                stdout="appindicatorsupport@rgcjonas.gmail.com\n",
            ),
        ]
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is True
        assert enabled is True

    @patch("vigia_hub.tray.checks.subprocess.run")
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_locale_agnostic(self, mock_which, mock_run):
        """Bug fix: anterior usava `gnome-extensions info` parseando
        'State: ACTIVE' em ingles. Em pt-BR vem 'Estado: ACTIVE',
        nao casava. Agora usa `list` e `list --enabled` que so retornam
        UUIDs sem texto localizado.
        """
        mock_which.return_value = "/usr/bin/gnome-extensions"
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout="appindicatorsupport@rgcjonas.gmail.com\n",
            ),
            MagicMock(
                returncode=0,
                stdout="appindicatorsupport@rgcjonas.gmail.com\n",
            ),
        ]
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is True
        assert enabled is True

    @patch("vigia_hub.tray.checks.subprocess.run")
    @patch("vigia_hub.tray.checks.shutil.which")
    def test_list_command_fails(self, mock_which, mock_run):
        """Se `gnome-extensions list` retornar erro, retorna False."""
        mock_which.return_value = "/usr/bin/gnome-extensions"
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        installed, enabled = checks.appindicator_extension_enabled()
        assert installed is False
        assert enabled is False


# ============================================================
# checks.tray_can_work
# ============================================================


class TestTrayCanWork:
    @patch("vigia_hub.tray.checks.appindicator_extension_enabled")
    @patch("vigia_hub.tray.checks.appindicator_lib_available")
    def test_all_good(self, mock_lib, mock_ext):
        mock_lib.return_value = True
        mock_ext.return_value = (True, True)
        result = checks.tray_can_work()
        assert result.ok is True
        assert result.has_lib is True
        assert result.has_extension is True
        assert result.ext_enabled is True

    @patch("vigia_hub.tray.checks.appindicator_extension_enabled")
    @patch("vigia_hub.tray.checks.appindicator_lib_available")
    def test_missing_lib(self, mock_lib, mock_ext):
        mock_lib.return_value = False
        mock_ext.return_value = (True, True)
        result = checks.tray_can_work()
        assert result.ok is False
        assert result.has_lib is False
        assert "biblioteca" in result.error_msg.lower()

    @patch("vigia_hub.tray.checks.appindicator_extension_enabled")
    @patch("vigia_hub.tray.checks.appindicator_lib_available")
    def test_missing_extension(self, mock_lib, mock_ext):
        mock_lib.return_value = True
        mock_ext.return_value = (False, False)
        result = checks.tray_can_work()
        assert result.ok is False
        assert result.has_extension is False
        assert "extens" in result.error_msg.lower()

    @patch("vigia_hub.tray.checks.appindicator_extension_enabled")
    @patch("vigia_hub.tray.checks.appindicator_lib_available")
    def test_extension_disabled(self, mock_lib, mock_ext):
        mock_lib.return_value = True
        mock_ext.return_value = (True, False)
        result = checks.tray_can_work()
        assert result.ok is False
        assert result.has_extension is True
        assert result.ext_enabled is False
        assert "desativada" in result.error_msg.lower()


# ============================================================
# checks.install_command / enable_extension_command
# ============================================================


class TestCommands:
    def test_install_command_atomic(self, monkeypatch):
        import vigia_common.platform as plat
        monkeypatch.setattr(plat, "is_atomic", lambda: True)
        cmd = checks.install_command()
        assert cmd[0] == "pkexec"
        assert cmd[1] == "rpm-ostree"
        assert cmd[2] == "install"
        # Tem os 2 pacotes
        assert "libayatana-appindicator-gtk3" in cmd
        assert "gnome-shell-extension-appindicator" in cmd

    def test_install_command_workstation(self, monkeypatch):
        import vigia_common.platform as plat
        monkeypatch.setattr(plat, "is_atomic", lambda: False)
        cmd = checks.install_command()
        assert cmd[0] == "pkexec"
        assert cmd[1] == "dnf"
        assert cmd[2] == "install"
        assert "libayatana-appindicator-gtk3" in cmd
        assert "gnome-shell-extension-appindicator" in cmd

    def test_enable_extension_command_format(self):
        cmd = checks.enable_extension_command()
        assert cmd[0] == "gnome-extensions"
        assert cmd[1] == "enable"
        assert cmd[2] == checks.EXT_UUID

    def test_uuid_constant(self):
        assert checks.EXT_UUID == "appindicatorsupport@rgcjonas.gmail.com"

    def test_install_packages_list(self):
        assert "libayatana-appindicator-gtk3" in checks.INSTALL_PACKAGES
        assert "gnome-shell-extension-appindicator" in checks.INSTALL_PACKAGES


# ============================================================
# manager.TrayManager
# ============================================================


class TestTrayManager:
    def test_is_running_false_initially(self):
        mgr = manager.TrayManager()
        assert mgr.is_running() is False

    def test_stop_when_not_running_is_noop(self):
        mgr = manager.TrayManager()
        mgr.stop()  # nao deve crashar
        assert mgr.is_running() is False

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_start_uses_installed_binary_when_available(self, mock_which, mock_popen):
        mock_which.return_value = "/usr/local/bin/vigia-hub-tray"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        mgr = manager.TrayManager()
        ok, err = mgr.start()
        assert ok is True
        assert err == ""
        # Conferir que chamou com o exec correto
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/local/bin/vigia-hub-tray"

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_start_falls_back_to_module(self, mock_which, mock_popen):
        """Se vigia-hub-tray nao esta no PATH, roda como modulo."""
        mock_which.return_value = None
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        mgr = manager.TrayManager()
        ok, err = mgr.start()
        assert ok is True
        args = mock_popen.call_args[0][0]
        # Deve usar `-m vigia_hub.tray.indicator`
        assert "-m" in args
        assert "vigia_hub.tray.indicator" in args

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_start_returns_error_on_failure(self, mock_which, mock_popen):
        mock_which.return_value = "/usr/bin/vigia-hub-tray"
        mock_popen.side_effect = OSError("permission denied")

        mgr = manager.TrayManager()
        ok, err = mgr.start()
        assert ok is False
        assert "permission denied" in err.lower() or "falha" in err.lower()

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_start_idempotent_when_already_running(self, mock_which, mock_popen):
        mock_which.return_value = "/usr/bin/vigia-hub-tray"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # ainda rodando
        mock_popen.return_value = mock_proc

        mgr = manager.TrayManager()
        mgr.start()
        # Segunda chamada nao spawn novo
        mock_popen.reset_mock()
        ok, _ = mgr.start()
        assert ok is True
        mock_popen.assert_not_called()

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_stop_terminates_subprocess(self, mock_which, mock_popen):
        mock_which.return_value = "/usr/bin/vigia-hub-tray"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_popen.return_value = mock_proc

        mgr = manager.TrayManager()
        mgr.start()
        mgr.stop()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called()

    @patch("vigia_hub.tray.manager.subprocess.Popen")
    @patch("vigia_hub.tray.manager.shutil.which")
    def test_stop_kills_if_terminate_times_out(self, mock_which, mock_popen):
        mock_which.return_value = "/usr/bin/vigia-hub-tray"
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired("vigia-hub-tray", 2.0),
            None,  # segunda chamada (apos kill) retorna OK
        ]
        mock_popen.return_value = mock_proc

        mgr = manager.TrayManager()
        mgr.start()
        mgr.stop()
        mock_proc.kill.assert_called_once()
