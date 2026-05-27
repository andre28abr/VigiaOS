"""Tests para set_global_dns_elevated — v0.2.5.

Cobertura:
- force_global=True (default) adiciona `Domains=~.` ao conteudo
- force_global=False NAO adiciona Domains
- Conteudo contem DNS=, DNSOverTLS= corretamente
- Validacao falha antes de chamar pkexec quando IPs invalidos
- Wait loop apos restart no script
- flush-caches no script
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from vigia_dns import backend


class TestSetGlobalDnsScriptContent:
    """Inspeciona o script gerado por set_global_dns_elevated."""

    @patch("vigia_dns.backend._run")
    def test_force_global_adds_domains_directive(self, mock_run):
        """v0.2.5: Por padrao adiciona `Domains=~.` (forca DNS global)."""
        mock_run.return_value = (0, "", "")
        ok, _ = backend.set_global_dns_elevated(
            servers=["1.1.1.1"], dot=True,
        )
        assert ok
        # Pega o script enviado
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pkexec"
        script = cmd[3]
        assert "Domains=~." in script
        assert "DNS=1.1.1.1" in script
        assert "DNSOverTLS=yes" in script

    @patch("vigia_dns.backend._run")
    def test_no_force_global_omits_domains(self, mock_run):
        """force_global=False NAO adiciona Domains (preserva split-DNS)."""
        mock_run.return_value = (0, "", "")
        ok, _ = backend.set_global_dns_elevated(
            servers=["1.1.1.1"], dot=True, force_global=False,
        )
        assert ok
        script = mock_run.call_args[0][0][3]
        assert "Domains=~." not in script

    @patch("vigia_dns.backend._run")
    def test_script_includes_restart(self, mock_run):
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"])
        script = mock_run.call_args[0][0][3]
        assert "systemctl restart systemd-resolved" in script

    @patch("vigia_dns.backend._run")
    def test_script_includes_wait_loop(self, mock_run):
        """v0.2.5: script espera resolvectl ficar pronto apos restart."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"])
        script = mock_run.call_args[0][0][3]
        # Sleep loop pra dar tempo ao d-bus interface
        assert "resolvectl status" in script
        assert "sleep" in script

    @patch("vigia_dns.backend._run")
    def test_script_flushes_cache(self, mock_run):
        """v0.2.5: cache flushado apos restart pra remover entries stale."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"])
        script = mock_run.call_args[0][0][3]
        assert "resolvectl flush-caches" in script

    @patch("vigia_dns.backend._run")
    def test_script_includes_backup(self, mock_run):
        """Backup do original em vigia-backup (se nao existir)."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"])
        script = mock_run.call_args[0][0][3]
        assert "/etc/systemd/resolved.conf.vigia-backup" in script

    @patch("vigia_dns.backend._run")
    def test_dot_no(self, mock_run):
        """dot=False resulta em DNSOverTLS=no."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"], dot=False)
        script = mock_run.call_args[0][0][3]
        assert "DNSOverTLS=no" in script

    @patch("vigia_dns.backend._run")
    def test_multiple_servers(self, mock_run):
        """Multiplos servers separados por espaco."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1", "1.0.0.1"])
        script = mock_run.call_args[0][0][3]
        assert "DNS=1.1.1.1 1.0.0.1" in script

    @patch("vigia_dns.backend._run")
    def test_fallback_included_when_provided(self, mock_run):
        """FallbackDNS= incluido quando fallback nao vazio."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(
            servers=["1.1.1.1"], fallback=["9.9.9.9"],
        )
        script = mock_run.call_args[0][0][3]
        assert "FallbackDNS=9.9.9.9" in script

    def test_invalid_ip_returns_early(self):
        """Validacao rejeita IPs invalidos ANTES de chamar pkexec."""
        ok, err = backend.set_global_dns_elevated(servers=["nao-e-ip"])
        assert not ok
        assert "invalid" in err.lower() or "invalida" in err.lower()

    def test_empty_list_returns_early(self):
        """Lista vazia rejeitada."""
        ok, err = backend.set_global_dns_elevated(servers=[])
        assert not ok

    @patch("vigia_dns.backend._run")
    def test_auth_cancel_returns_user_message(self, mock_run):
        """rc 126/127 do pkexec = autenticacao cancelada."""
        mock_run.return_value = (126, "", "")
        ok, err = backend.set_global_dns_elevated(servers=["1.1.1.1"])
        assert not ok
        assert "cancel" in err.lower() or "autenti" in err.lower()


class TestForceGlobalRationale:
    """Documenta POR QUE Domains=~. e' o default em v0.2.5.

    Sem Domains=~., o DNS pushed via DHCP por interface (NetworkManager)
    sobrescreve o DNS global. Isso faz com que `DNS=1.1.1.1` em
    /etc/systemd/resolved.conf nao tenha efeito pratico — queries vao
    pro DNS do roteador.
    """

    @patch("vigia_dns.backend._run")
    def test_default_is_force_global(self, mock_run):
        """Default e' force_global=True (escolha pra LGPD/privacidade)."""
        mock_run.return_value = (0, "", "")
        backend.set_global_dns_elevated(servers=["1.1.1.1"])
        script = mock_run.call_args[0][0][3]
        # Default deve forcar global
        assert "Domains=~." in script
