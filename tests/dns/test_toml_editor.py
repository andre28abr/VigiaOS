"""Tests para o editor de TOML line-based do dnscrypt_backend.

dnscrypt-proxy.toml e' complexo (~300 linhas, com comentarios), e o
backend usa parser line-based pra preservar comments e ordem. Estes
tests validam que essa logica nao bagunce o config.
"""

from __future__ import annotations

import pytest

from vigia_dns.dnscrypt_backend import _update_toml_key


# ============================================================
# _update_toml_key — substitui key no escopo global (sem section)
# ============================================================


class TestUpdateTomlKey:
    def test_replace_existing_key(self):
        lines = [
            "# comentario\n",
            "server_names = []\n",
            "listen_addresses = ['127.0.0.1:53']\n",
        ]
        result = _update_toml_key(lines, "server_names", "['cloudflare']")
        text = "".join(result)
        assert "server_names = ['cloudflare']" in text
        # Comentario preservado
        assert "# comentario" in text
        # Outras keys nao mexem
        assert "listen_addresses = ['127.0.0.1:53']" in text

    def test_replace_preserves_indent(self):
        lines = [
            "  indented_key = old_value\n",
            "other = thing\n",
        ]
        result = _update_toml_key(lines, "indented_key", "new_value")
        text = "".join(result)
        # Indent preservado
        assert "  indented_key = new_value" in text

    def test_add_key_if_not_exists(self):
        lines = [
            "other_key = 1\n",
        ]
        result = _update_toml_key(lines, "new_key", "42")
        text = "".join(result)
        assert "new_key = 42" in text

    def test_does_not_touch_keys_in_sections(self):
        """Key dentro de section nao deve ser modificada."""
        lines = [
            "server_names = []\n",
            "\n",
            "[some_section]\n",
            "server_names = ['inside-section']\n",
        ]
        result = _update_toml_key(lines, "server_names", "['NEW']")
        text = "".join(result)
        # Top-level mudou
        assert "server_names = ['NEW']" in text
        # Dentro da section, NAO mudou
        assert "server_names = ['inside-section']" in text

    def test_comments_with_key_not_replaced(self):
        """Linhas comentadas que parecem 'key = ...' nao devem ser tocadas."""
        lines = [
            "# server_names = ['exemplo']\n",     # comment
            "server_names = []\n",                # real
        ]
        result = _update_toml_key(lines, "server_names", "['novo']")
        text = "".join(result)
        # Linha real mudou
        assert "server_names = ['novo']" in text
        # Comment intocado
        assert "# server_names = ['exemplo']" in text


# v0.4.0: TestUpdateTomlSectionKey removida — _update_toml_section_key
# era usado por enable_blocklist_in_config / enable_query_log_in_config
# (deletados na v0.4 quando blocklist/stats sairam do DNS Manager).


# ============================================================
# Idempotencia (chamar 2x deve ser equivalente a 1x)
# ============================================================


class TestIdempotence:
    def test_update_key_idempotent(self):
        lines = ["server_names = []\n"]
        once = _update_toml_key(lines, "server_names", "['cloudflare']")
        twice = _update_toml_key(once, "server_names", "['cloudflare']")
        assert once == twice

    # v0.4.0: test_update_section_key_idempotent removido junto com a funcao.
