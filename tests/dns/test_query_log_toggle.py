"""Tests para enable/disable_query_log_in_config — v0.2.9.

A v0.2.9 adiciona botao 'Habilitar' direto na aba Stats que chama
`dc.enable_query_log_in_config()`. Esses tests validam o conteudo
escrito no .toml.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vigia_dns import dnscrypt_backend as dc


SAMPLE_TOML_WITH_QUERY_LOG_DISABLED = """\
# dnscrypt-proxy config
server_names = ['cloudflare']

[blocked_names]
block_file = '/etc/dnscrypt-proxy/blacklist.txt'

[query_log]
# file = '/var/log/dnscrypt-proxy/query.log'
"""

SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION = """\
# dnscrypt-proxy config
server_names = ['cloudflare']

[blocked_names]
block_file = '/etc/dnscrypt-proxy/blacklist.txt'
"""


class TestEnableQueryLog:
    """enable_query_log_in_config escreve file = '...' em [query_log]."""

    @patch("vigia_dns.dnscrypt_backend._atomic_write_config_via_pkexec")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_writes_file_directive(self, mock_read, mock_write):
        mock_read.return_value = SAMPLE_TOML_WITH_QUERY_LOG_DISABLED.splitlines(
            keepends=True
        )
        mock_write.return_value = (True, "")
        ok, _ = dc.enable_query_log_in_config()
        assert ok
        # Pega o conteudo escrito
        written = mock_write.call_args[0][0]
        # Tem que ter file = '/var/log/dnscrypt-proxy/query.log'
        assert "file" in written
        assert "/var/log/dnscrypt-proxy/query.log" in written

    @patch("vigia_dns.dnscrypt_backend._atomic_write_config_via_pkexec")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_when_section_missing_creates_it(self, mock_read, mock_write):
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_write.return_value = (True, "")
        ok, _ = dc.enable_query_log_in_config()
        assert ok
        written = mock_write.call_args[0][0]
        # Seção criada
        assert "[query_log]" in written
        assert "file" in written

    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_fails_when_cant_read_config(self, mock_read):
        mock_read.return_value = []
        ok, err = dc.enable_query_log_in_config()
        assert not ok
        assert "config" in err.lower() or "ler" in err.lower()


class TestDisableQueryLog:
    """disable_query_log_in_config seta file = ''."""

    @patch("vigia_dns.dnscrypt_backend._atomic_write_config_via_pkexec")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_disable_sets_empty_file(self, mock_read, mock_write):
        sample = """\
[query_log]
file = '/var/log/dnscrypt-proxy/query.log'
"""
        mock_read.return_value = sample.splitlines(keepends=True)
        mock_write.return_value = (True, "")
        ok, _ = dc.disable_query_log_in_config()
        assert ok
        written = mock_write.call_args[0][0]
        # file = '' (string vazia → desabilita)
        assert "file = ''" in written


class TestPrivacyConfirmation:
    """A UI tem que pedir confirmacao do user antes de habilitar.

    Esses tests validam estado, nao UI. UI tem dialog em stats.py
    com aviso LGPD claro.
    """

    def test_constant_query_log_path_documented(self):
        """Path do query log e' uma constante conhecida."""
        assert str(dc.QUERY_LOG_PATH) == "/var/log/dnscrypt-proxy/query.log"

    def test_dataclass_default_is_disabled(self):
        """DnsCryptStatus default eh query_log_enabled=False."""
        st = dc.DnsCryptStatus()
        assert st.query_log_enabled is False
