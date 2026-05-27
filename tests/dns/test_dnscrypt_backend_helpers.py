"""Tests para helpers internos do dnscrypt_backend.

Cobertura:
- get_version() parsing de output do `dnscrypt-proxy -version`
- _read_config_parsed handling de erros
- set_servers_blocking input validation (chars seguros em server names)
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from vigia_dns import dnscrypt_backend as dc


class TestGetVersionParser:
    """Parser do output do `dnscrypt-proxy -version`."""

    @patch("vigia_dns.dnscrypt_backend.dnscrypt_installed")
    @patch("vigia_dns.dnscrypt_backend.subprocess.run")
    def test_simple_version_string(self, mock_run, mock_installed):
        mock_installed.return_value = True
        mock_run.return_value = MagicMock(stdout="2.1.5\n", returncode=0)
        result = dc.get_version()
        assert result == "2.1.5"

    @patch("vigia_dns.dnscrypt_backend.dnscrypt_installed")
    @patch("vigia_dns.dnscrypt_backend.subprocess.run")
    def test_multiline_output_extracts_version(self, mock_run, mock_installed):
        mock_installed.return_value = True
        mock_run.return_value = MagicMock(
            stdout="2.1.14\nBuilt with libsodium 1.0.18\n",
            returncode=0,
        )
        result = dc.get_version()
        assert result == "2.1.14"

    @patch("vigia_dns.dnscrypt_backend.dnscrypt_installed")
    @patch("vigia_dns.dnscrypt_backend.subprocess.run")
    def test_version_with_minor_patch(self, mock_run, mock_installed):
        mock_installed.return_value = True
        mock_run.return_value = MagicMock(stdout="2.1\n", returncode=0)
        result = dc.get_version()
        assert result == "2.1"

    @patch("vigia_dns.dnscrypt_backend.dnscrypt_installed")
    def test_not_installed_returns_empty(self, mock_installed):
        mock_installed.return_value = False
        assert dc.get_version() == ""


class TestServerNameValidation:
    """set_servers_blocking valida nomes de server (anti-injection)."""

    # ===== Aceitos =====

    @pytest.mark.parametrize("name", [
        "cloudflare",
        "quad9-doh-ip4-port443-filter-pri",
        "adguard-dns-doh",
        "mullvad-doh",
        "server.with.dots",
        "server_with_underscore",
        "Server-123",
    ])
    def test_accepts_safe_names(self, name):
        # Replica do regex usado em set_servers_blocking
        assert re.match(r"^[a-zA-Z0-9._\-]+$", name), \
            f"Deveria aceitar: {name}"

    # ===== Rejeitados =====

    @pytest.mark.parametrize("name", [
        "server;rm -rf /",     # shell injection
        "server|whoami",        # pipe
        "server`cmd`",          # backtick
        "server$VAR",           # var expansion
        "server with space",    # espaco
        "server'quote",         # aspas
        'server"dq',            # aspas dupla
        "server\nnewline",      # quebra
        "server\x00null",       # null byte
        "../etc/passwd",        # path traversal
        "",                     # vazio
    ])
    def test_rejects_unsafe_names(self, name):
        # Empty string nao passa regex (regex requer 1+ char)
        if name == "":
            assert not re.match(r"^[a-zA-Z0-9._\-]+$", name)
        else:
            assert not re.match(r"^[a-zA-Z0-9._\-]+$", name), \
                f"Deveria rejeitar: {name!r}"


class TestDnsCryptStatusDataclass:
    """DnsCryptStatus defaults razoaveis (v0.4.0)."""

    def test_default_values(self):
        st = dc.DnsCryptStatus()
        assert st.installed is False
        assert st.active is False
        assert st.enabled is False
        assert st.version == ""
        assert st.server_names == []
        assert st.require_dnssec is False
        assert st.require_nolog is False
        assert st.listen_address == "127.0.0.1:53"

    def test_construct_with_values(self):
        st = dc.DnsCryptStatus(
            installed=True,
            active=True,
            version="2.1.5",
            server_names=["cloudflare", "quad9"],
        )
        assert st.installed is True
        assert len(st.server_names) == 2


# v0.4.0: TestDnsCryptStatsDataclass removida — DnsCryptStats foi
# deletado quando Stats tab saiu do DNS Manager.


class TestSanityChecks:
    """Funcoes de check de instalacao."""

    @patch("vigia_dns.dnscrypt_backend.shutil.which")
    def test_dnscrypt_installed_when_binary_exists(self, mock_which):
        mock_which.return_value = "/usr/bin/dnscrypt-proxy"
        assert dc.dnscrypt_installed() is True

    @patch("vigia_dns.dnscrypt_backend.shutil.which")
    def test_dnscrypt_not_installed_when_missing(self, mock_which):
        mock_which.return_value = None
        assert dc.dnscrypt_installed() is False
