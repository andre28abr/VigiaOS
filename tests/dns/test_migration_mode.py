"""Tests para migration.get_current_mode (detecta modo ativo).

A logica e:
  - 'advanced' se dnscrypt-proxy ativo E systemd-resolved inativo
  - 'simple' se systemd-resolved ativo E dnscrypt-proxy inativo
  - 'unknown' caso contrario (ambos ativos, ambos inativos)

Usa mock para isolar de subprocess.run.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from vigia_dns import migration


class TestGetCurrentMode:
    @patch("vigia_dns.dnscrypt_backend.is_active")
    @patch("vigia_dns.migration.systemd_resolved_active")
    def test_advanced_mode(self, mock_resolved, mock_dnscrypt):
        """dnscrypt ON + resolved OFF → advanced."""
        mock_dnscrypt.return_value = True
        mock_resolved.return_value = False
        assert migration.get_current_mode() == "advanced"

    @patch("vigia_dns.dnscrypt_backend.is_active")
    @patch("vigia_dns.migration.systemd_resolved_active")
    def test_simple_mode(self, mock_resolved, mock_dnscrypt):
        """resolved ON + dnscrypt OFF → simple."""
        mock_dnscrypt.return_value = False
        mock_resolved.return_value = True
        assert migration.get_current_mode() == "simple"

    @patch("vigia_dns.dnscrypt_backend.is_active")
    @patch("vigia_dns.migration.systemd_resolved_active")
    def test_both_active_is_unknown(self, mock_resolved, mock_dnscrypt):
        """Ambos ativos = conflito → unknown."""
        mock_dnscrypt.return_value = True
        mock_resolved.return_value = True
        assert migration.get_current_mode() == "unknown"

    @patch("vigia_dns.dnscrypt_backend.is_active")
    @patch("vigia_dns.migration.systemd_resolved_active")
    def test_both_inactive_is_unknown(self, mock_resolved, mock_dnscrypt):
        """Ambos inativos = no DNS → unknown."""
        mock_dnscrypt.return_value = False
        mock_resolved.return_value = False
        assert migration.get_current_mode() == "unknown"


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


class TestSystemdResolvedActiveSafety:
    """systemd_resolved_active deve nao crashar mesmo sem systemctl."""

    @patch("vigia_dns.migration.shutil.which")
    def test_no_systemctl_returns_false(self, mock_which):
        mock_which.return_value = None
        assert migration.systemd_resolved_active() is False
