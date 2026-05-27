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
    """enable_query_log_in_config (v0.2.10) — script inteiro via pkexec."""

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_writes_file_directive(self, mock_read, mock_run):
        mock_read.return_value = SAMPLE_TOML_WITH_QUERY_LOG_DISABLED.splitlines(
            keepends=True
        )
        mock_run.return_value = (0, "", "")
        ok, _ = dc.enable_query_log_in_config()
        assert ok
        # Pega o script bash enviado
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pkexec"
        script = cmd[3]
        # Tem que mencionar o path
        assert "/var/log/dnscrypt-proxy/query.log" in script
        # E o file = ... no novo content embed
        assert "file = '/var/log/dnscrypt-proxy/query.log'" in script

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_when_section_missing_creates_it(self, mock_read, mock_run):
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_run.return_value = (0, "", "")
        ok, _ = dc.enable_query_log_in_config()
        assert ok
        script = mock_run.call_args[0][0][3]
        # Seção criada no content embedded
        assert "[query_log]" in script
        assert "file" in script

    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_fails_when_cant_read_config(self, mock_read):
        mock_read.return_value = []
        ok, err = dc.enable_query_log_in_config()
        assert not ok
        assert "config" in err.lower() or "ler" in err.lower()

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_script_creates_log_dir(self, mock_read, mock_run):
        """v0.2.10: script faz mkdir -p do diretorio do log."""
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_run.return_value = (0, "", "")
        dc.enable_query_log_in_config()
        script = mock_run.call_args[0][0][3]
        assert "mkdir -p" in script
        assert "/var/log/dnscrypt-proxy" in script

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_script_touches_log_file(self, mock_read, mock_run):
        """v0.2.10: cria o file vazio pra dar permissoes."""
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_run.return_value = (0, "", "")
        dc.enable_query_log_in_config()
        script = mock_run.call_args[0][0][3]
        assert "touch" in script
        assert "chmod 0640" in script

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_script_restarts_service(self, mock_read, mock_run):
        """v0.2.10: restart dnscrypt-proxy + wait loop."""
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_run.return_value = (0, "", "")
        dc.enable_query_log_in_config()
        script = mock_run.call_args[0][0][3]
        assert "systemctl restart dnscrypt-proxy" in script
        # Wait loop ate o servico voltar
        assert "is-active" in script
        assert "sleep" in script

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_removes_commented_file_lines(self, mock_read, mock_run):
        """v0.2.10: remove '# file = ...' redundantes em [query_log]."""
        # TOML com linha file comentada — deveria sumir
        toml_with_commented_file = """\
[query_log]
# file = '/var/log/dnscrypt-proxy/query.log'
# format = 'tsv'
"""
        mock_read.return_value = toml_with_commented_file.splitlines(keepends=True)
        mock_run.return_value = (0, "", "")
        dc.enable_query_log_in_config()
        script = mock_run.call_args[0][0][3]
        # Nao deve haver linha comentada com file
        assert "# file = '/var/log/dnscrypt-proxy/query.log'" not in script
        # Mas tem que ter a linha real
        assert "file = '/var/log/dnscrypt-proxy/query.log'" in script
        # Mantém comentário não-relacionado
        assert "# format" in script

    @patch("vigia_dns.dnscrypt_backend._run")
    @patch("vigia_dns.dnscrypt_backend._read_config_lines")
    def test_enable_auth_cancel(self, mock_read, mock_run):
        mock_read.return_value = SAMPLE_TOML_WITHOUT_QUERY_LOG_SECTION.splitlines(
            keepends=True
        )
        mock_run.return_value = (126, "", "")
        ok, err = dc.enable_query_log_in_config()
        assert not ok
        assert "cancel" in err.lower() or "autenti" in err.lower()


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
