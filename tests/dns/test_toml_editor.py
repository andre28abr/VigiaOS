"""Tests para o editor de TOML line-based do dnscrypt_backend.

dnscrypt-proxy.toml e' complexo (~300 linhas, com comentarios), e o
backend usa parser line-based pra preservar comments e ordem. Estes
tests validam que essa logica nao bagunce o config.
"""

from __future__ import annotations

import pytest

from vigia_dns.dnscrypt_backend import (
    _update_toml_key,
    _update_toml_section_key,
)


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


# ============================================================
# _update_toml_section_key — substitui key dentro de [section]
# ============================================================


class TestUpdateTomlSectionKey:
    def test_replace_existing_key_in_section(self):
        lines = [
            "global_key = 1\n",
            "[blocked_names]\n",
            "block_file = '/old/path'\n",
            "\n",
            "[other]\n",
            "stuff = true\n",
        ]
        result = _update_toml_section_key(
            lines, "blocked_names", "block_file", "'/new/path'"
        )
        text = "".join(result)
        assert "block_file = '/new/path'" in text
        # Outros nao mexeram
        assert "global_key = 1" in text
        assert "stuff = true" in text

    def test_add_key_to_existing_empty_section(self):
        lines = [
            "[blocked_names]\n",
            "\n",
            "[other]\n",
            "stuff = true\n",
        ]
        result = _update_toml_section_key(
            lines, "blocked_names", "block_file", "'/path'"
        )
        text = "".join(result)
        assert "block_file = '/path'" in text

    def test_create_section_if_missing(self):
        lines = [
            "global_key = 1\n",
        ]
        result = _update_toml_section_key(
            lines, "new_section", "new_key", "42"
        )
        text = "".join(result)
        assert "[new_section]" in text
        assert "new_key = 42" in text
        # Original preservado
        assert "global_key = 1" in text

    def test_does_not_touch_same_key_in_other_section(self):
        lines = [
            "[section_a]\n",
            "shared_key = 'A'\n",
            "\n",
            "[section_b]\n",
            "shared_key = 'B'\n",
        ]
        result = _update_toml_section_key(
            lines, "section_a", "shared_key", "'CHANGED'"
        )
        text = "".join(result)
        assert "shared_key = 'CHANGED'" in text  # A mudou
        assert "shared_key = 'B'" in text          # B intacto

    def test_preserves_comments_in_section(self):
        lines = [
            "[blocked_names]\n",
            "# comentario importante\n",
            "block_file = '/path'\n",
        ]
        result = _update_toml_section_key(
            lines, "blocked_names", "block_file", "'/new'"
        )
        text = "".join(result)
        assert "# comentario importante" in text
        assert "block_file = '/new'" in text


# ============================================================
# Idempotencia (chamar 2x deve ser equivalente a 1x)
# ============================================================


class TestIdempotence:
    def test_update_key_idempotent(self):
        lines = ["server_names = []\n"]
        once = _update_toml_key(lines, "server_names", "['cloudflare']")
        twice = _update_toml_key(once, "server_names", "['cloudflare']")
        assert once == twice

    def test_update_section_key_idempotent(self):
        lines = ["[blocked_names]\n", "block_file = '/old'\n"]
        once = _update_toml_section_key(
            lines, "blocked_names", "block_file", "'/new'"
        )
        twice = _update_toml_section_key(
            once, "blocked_names", "block_file", "'/new'"
        )
        assert once == twice
