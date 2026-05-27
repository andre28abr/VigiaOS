"""Tests para migration.py — v0.3.0 (setup helpers).

A v0.2.x tinha `get_current_mode()` retornando simple/advanced/unknown.
A v0.3 removeu (dnscrypt-proxy e' o unico backend). Restou:

- `dnscrypt_active_ready()` — esta tudo configurado e rodando?
- `ensure_dnscrypt_active_blocking()` — primeira ativacao (idempotente)
- `restore_systemd_resolved_blocking()` — uninstall path
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vigia_dns import migration


class TestSystemdResolvedActiveSafety:
    """systemd_resolved_active deve nao crashar mesmo sem systemctl."""

    @patch("vigia_dns.migration.shutil.which")
    def test_no_systemctl_returns_false(self, mock_which):
        mock_which.return_value = None
        assert migration.systemd_resolved_active() is False


class TestHasResolvedBackup:
    def test_no_backup_returns_false(self, tmp_path, monkeypatch):
        fake = tmp_path / "nao-existe.conf"
        monkeypatch.setattr(migration, "RESOLVED_BACKUP", fake)
        assert migration.has_resolved_backup() is False

    def test_existing_backup_returns_true(self, tmp_path, monkeypatch):
        backup = tmp_path / "resolved.conf.vigia-backup"
        backup.write_text("[Resolve]\nDNS=1.1.1.1\n")
        monkeypatch.setattr(migration, "RESOLVED_BACKUP", backup)
        assert migration.has_resolved_backup() is True


class TestDnsCryptActiveReady:
    """dnscrypt_active_ready: dnscrypt rodando + resolv.conf apontando."""

    @patch("vigia_dns.dnscrypt_backend.is_active")
    def test_returns_false_if_dnscrypt_not_active(self, mock_dc_active):
        mock_dc_active.return_value = False
        assert migration.dnscrypt_active_ready() is False

    @patch("vigia_dns.dnscrypt_backend.is_active")
    def test_returns_true_when_resolv_conf_points_to_127(
        self, mock_dc_active, tmp_path, monkeypatch,
    ):
        mock_dc_active.return_value = True
        # Mock resolv.conf apontando pra 127.0.0.1
        fake_resolv = tmp_path / "resolv.conf"
        fake_resolv.write_text(
            "# managed by vigia\nnameserver 127.0.0.1\n"
        )
        monkeypatch.setattr(migration, "RESOLV_CONF", fake_resolv)
        assert migration.dnscrypt_active_ready() is True

    @patch("vigia_dns.dnscrypt_backend.is_active")
    def test_returns_false_when_resolv_points_elsewhere(
        self, mock_dc_active, tmp_path, monkeypatch,
    ):
        """resolv.conf nao tem 127.0.0.1 — dnscrypt nao esta sendo usado."""
        mock_dc_active.return_value = True
        fake_resolv = tmp_path / "resolv.conf"
        fake_resolv.write_text(
            "nameserver 192.168.1.1\n"
        )
        monkeypatch.setattr(migration, "RESOLV_CONF", fake_resolv)
        assert migration.dnscrypt_active_ready() is False


class TestEnsureDnsCryptActive:
    """ensure_dnscrypt_active_blocking — idempotente + escapes corretos."""

    @patch("vigia_dns.migration.dnscrypt_active_ready")
    @patch("vigia_dns.migration._run")
    @patch("vigia_dns.migration.shutil.which")
    def test_idempotent_when_already_ready(
        self, mock_which, mock_run, mock_ready,
    ):
        """Se ja esta ready, retorna ok sem chamar pkexec."""
        mock_which.return_value = "/usr/bin/pkexec"
        mock_ready.return_value = True
        ok, _ = migration.ensure_dnscrypt_active_blocking()
        assert ok
        # pkexec NAO foi chamado
        mock_run.assert_not_called()

    @patch("vigia_dns.migration.dnscrypt_active_ready")
    @patch("vigia_dns.migration._run")
    @patch("vigia_dns.migration.shutil.which")
    def test_runs_pkexec_when_not_ready(
        self, mock_which, mock_run, mock_ready,
    ):
        mock_which.return_value = "/usr/bin/pkexec"
        mock_ready.return_value = False
        mock_run.return_value = (0, "", "")
        ok, _ = migration.ensure_dnscrypt_active_blocking()
        assert ok
        # Script bash via pkexec
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pkexec"
        script = cmd[3]
        # Script faz backup, stop, redirect, start
        assert "systemctl stop systemd-resolved" in script
        assert "systemctl enable --now dnscrypt-proxy" in script
        assert "nameserver 127.0.0.1" in script

    @patch("vigia_dns.migration.shutil.which")
    def test_no_pkexec_returns_error(self, mock_which):
        mock_which.return_value = None
        ok, err = migration.ensure_dnscrypt_active_blocking()
        assert not ok
        assert "pkexec" in err.lower()

    @patch("vigia_dns.migration.dnscrypt_active_ready")
    @patch("vigia_dns.migration._run")
    @patch("vigia_dns.migration.shutil.which")
    def test_auth_cancel_returns_user_message(
        self, mock_which, mock_run, mock_ready,
    ):
        mock_which.return_value = "/usr/bin/pkexec"
        mock_ready.return_value = False
        mock_run.return_value = (126, "", "")
        ok, err = migration.ensure_dnscrypt_active_blocking()
        assert not ok
        assert "cancel" in err.lower() or "autenti" in err.lower()


class TestRestoreSystemdResolved:
    """restore_systemd_resolved_blocking — script correto."""

    @patch("vigia_dns.migration._run")
    @patch("vigia_dns.migration.shutil.which")
    def test_script_stops_dnscrypt_and_starts_resolved(
        self, mock_which, mock_run,
    ):
        mock_which.return_value = "/usr/bin/pkexec"
        mock_run.return_value = (0, "", "")
        ok, _ = migration.restore_systemd_resolved_blocking()
        assert ok
        script = mock_run.call_args[0][0][3]
        assert "systemctl stop dnscrypt-proxy" in script
        assert "systemctl enable --now systemd-resolved" in script

    @patch("vigia_dns.migration._run")
    @patch("vigia_dns.migration.shutil.which")
    def test_script_restores_resolv_conf(
        self, mock_which, mock_run,
    ):
        mock_which.return_value = "/usr/bin/pkexec"
        mock_run.return_value = (0, "", "")
        migration.restore_systemd_resolved_blocking()
        script = mock_run.call_args[0][0][3]
        # Restaura do backup OU usa stub
        assert "stub-resolv.conf" in script or "RESOLV_BACKUP" in script

    @patch("vigia_dns.migration.shutil.which")
    def test_no_pkexec_returns_error(self, mock_which):
        mock_which.return_value = None
        ok, err = migration.restore_systemd_resolved_blocking()
        assert not ok
        assert "pkexec" in err.lower()
