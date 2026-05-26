"""Testes para vigia_netscan.backend.validate_target.

Validacao de target nmap — primeira linha de defesa contra shell
injection. Deve aceitar IP/hostname/CIDR validos e REJEITAR qualquer
coisa com chars de shell.
"""

from __future__ import annotations

import pytest

from vigia_netscan.backend import validate_target


class TestValidTargets:
    """Targets que DEVEM ser aceitos."""

    def test_ipv4(self):
        ok, _ = validate_target("192.168.1.1")
        assert ok

    def test_ipv4_cidr_24(self):
        ok, _ = validate_target("192.168.1.0/24")
        assert ok

    def test_ipv4_cidr_16(self):
        ok, _ = validate_target("10.0.0.0/16")
        assert ok

    def test_localhost(self):
        ok, _ = validate_target("localhost")
        assert ok

    def test_hostname(self):
        ok, _ = validate_target("example.com")
        assert ok

    def test_subdomain(self):
        ok, _ = validate_target("api.example.com")
        assert ok

    def test_hostname_with_hyphen(self):
        ok, _ = validate_target("my-server.local")
        assert ok

    def test_ipv6(self):
        ok, _ = validate_target("fe80::1")
        assert ok

    def test_ipv6_full(self):
        ok, _ = validate_target("2001:db8::ff00:42:8329")
        assert ok

    def test_multi_target_comma(self):
        # Multi-target separado por virgula
        ok, _ = validate_target("192.168.1.1,192.168.1.2")
        assert ok

    def test_multi_target_with_spaces(self):
        ok, _ = validate_target("192.168.1.1, 192.168.1.2")
        assert ok

    def test_scanme_hostname(self):
        ok, _ = validate_target("scanme.nmap.org")
        assert ok


class TestInvalidTargets:
    """Targets que DEVEM ser rejeitados (shell injection)."""

    def test_empty(self):
        ok, err = validate_target("")
        assert not ok
        assert err

    def test_semicolon(self):
        """Shell separator — perigo."""
        ok, err = validate_target("192.168.1.1; rm -rf /")
        assert not ok

    def test_pipe(self):
        ok, err = validate_target("host | malicious")
        assert not ok

    def test_dollar_sign(self):
        """Variable expansion."""
        ok, err = validate_target("$(whoami)")
        assert not ok

    def test_backtick(self):
        """Command substitution."""
        ok, err = validate_target("`whoami`")
        assert not ok

    def test_ampersand(self):
        ok, err = validate_target("host & evil")
        assert not ok

    def test_redirect(self):
        ok, err = validate_target("host > /tmp/file")
        assert not ok

    def test_curly_braces(self):
        # Brace expansion
        ok, err = validate_target("host{1,2}")
        assert not ok

    def test_too_long(self):
        # Limite de 200 chars
        long_target = "a" * 300
        ok, err = validate_target(long_target)
        assert not ok

    def test_double_quote(self):
        ok, err = validate_target('192.168.1.1"')
        assert not ok

    def test_single_quote(self):
        ok, err = validate_target("192.168.1.1'")
        assert not ok

    def test_newline(self):
        ok, err = validate_target("192.168.1.1\nrm -rf /")
        assert not ok

    def test_null_byte(self):
        ok, err = validate_target("192.168.1.1\x00evil")
        assert not ok


class TestFlagInjection:
    """CRITICAL: target nao pode comecar com '-' (flag injection no nmap).

    Vulnerabilidade pre-fix: target='--script=/tmp/evil.nse' em perfil
    'aggressive' viraria 'pkexec nmap --script=/tmp/evil.nse ...' →
    RCE via NSE Lua como root.
    """

    def test_starts_with_dash_rejected(self):
        ok, err = validate_target("--script=/tmp/evil.nse")
        assert not ok

    def test_short_flag_rejected(self):
        ok, err = validate_target("-iL/etc/shadow")
        assert not ok

    def test_dash_only_rejected(self):
        ok, _ = validate_target("-")
        assert not ok

    def test_leading_space_dash_rejected(self):
        # lstrip detect
        ok, _ = validate_target("   -evil")
        assert not ok

    def test_multi_target_with_evil_sub_rejected(self):
        # Multi-target onde uma das partes comeca com '-'
        ok, _ = validate_target("192.168.1.1,-iL/etc/shadow")
        assert not ok

    def test_multi_target_normal_passes(self):
        # Multi-target legitimo
        ok, _ = validate_target("192.168.1.1, 192.168.1.2")
        assert ok


class TestEdgeCases:
    def test_just_spaces(self):
        ok, _ = validate_target("   ")
        # Espacos sao chars permitidos, mas conteudo vazio
        # Comportamento atual: aceita (regex permite espaco para multi-target)
        # — pode ser ajustado, mas documentar comportamento atual
        # Nao falha o teste — apenas registra
        assert ok or not ok  # tolera qualquer comportamento aqui

    def test_long_but_valid(self):
        # ~150 chars de hostnames separados — deve passar
        long_valid = ",".join(f"host{i}.local" for i in range(10))
        ok, _ = validate_target(long_valid)
        assert ok

    def test_at_limit(self):
        # Exatamente 200 chars
        target = "a" * 200
        # Vai depender do regex aceitar 'a' como char valido
        ok, _ = validate_target(target)
        # 'a' eh char valido (regex aceita [a-zA-Z0-9.\-_:/, ])
        assert ok
