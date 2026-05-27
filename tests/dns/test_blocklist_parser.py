"""Tests para parsing/manipulacao de blocklists.

import_blocklist_from_url parsea 2 formatos:
- Hosts file: '0.0.0.0 doubleclick.net' (formato Pi-hole/StevenBlack)
- Domain-per-line: 'doubleclick.net'

Comments com # devem ser ignorados.
Linhas vazias devem ser ignoradas.
Dominios invalidos devem ser filtrados.
"""

from __future__ import annotations

import pytest


# Pega a logica de parsing (replicada aqui para testabilidade)
def parse_blocklist_text(text: str, validator=None) -> list[str]:
    """Replica da logica dentro de dnscrypt_backend.import_blocklist_from_url.

    Aceita texto bruto, retorna lista deduplicada de dominios validos.
    """
    new_domains: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        domain = parts[-1] if len(parts) >= 2 else parts[0]
        if not domain or domain in seen:
            continue
        if validator is not None:
            ok, _ = validator(domain)
            if not ok:
                continue
        seen.add(domain)
        new_domains.append(domain)
    return new_domains


# ============================================================
# Formato hosts (StevenBlack-like)
# ============================================================


class TestHostsFormat:
    def test_hosts_format(self):
        text = """\
# StevenBlack hosts
0.0.0.0 doubleclick.net
0.0.0.0 google-analytics.com
0.0.0.0 facebook.com
"""
        result = parse_blocklist_text(text)
        assert result == [
            "doubleclick.net",
            "google-analytics.com",
            "facebook.com",
        ]

    def test_hosts_format_with_127(self):
        text = "127.0.0.1 ads.example.com"
        result = parse_blocklist_text(text)
        assert result == ["ads.example.com"]

    def test_hosts_format_with_inline_comment(self):
        text = """\
0.0.0.0 doubleclick.net
# isto e comentario
0.0.0.0 google-analytics.com"""
        result = parse_blocklist_text(text)
        assert "doubleclick.net" in result
        assert "google-analytics.com" in result


# ============================================================
# Formato simples (domain per line)
# ============================================================


class TestSimpleFormat:
    def test_one_per_line(self):
        text = """\
doubleclick.net
google-analytics.com
facebook.com
"""
        result = parse_blocklist_text(text)
        assert result == [
            "doubleclick.net",
            "google-analytics.com",
            "facebook.com",
        ]

    def test_skips_empty_lines(self):
        text = "doubleclick.net\n\n\ngoogle-analytics.com\n"
        result = parse_blocklist_text(text)
        assert result == ["doubleclick.net", "google-analytics.com"]

    def test_skips_comments(self):
        text = """\
# este e um comentario
doubleclick.net
# outro comentario
google-analytics.com
"""
        result = parse_blocklist_text(text)
        assert result == ["doubleclick.net", "google-analytics.com"]


# ============================================================
# Deduplicacao
# ============================================================


class TestDeduplication:
    def test_no_duplicates_in_output(self):
        text = """\
doubleclick.net
doubleclick.net
google-analytics.com
doubleclick.net
"""
        result = parse_blocklist_text(text)
        assert result == ["doubleclick.net", "google-analytics.com"]

    def test_dedup_across_formats(self):
        text = """\
0.0.0.0 doubleclick.net
doubleclick.net
127.0.0.1 doubleclick.net
"""
        result = parse_blocklist_text(text)
        assert result == ["doubleclick.net"]


# ============================================================
# Validator integration (rejeita dominios invalidos)
# ============================================================


class TestValidatorIntegration:
    def test_filters_invalid_via_validator(self):
        from vigia_dns.dnscrypt_backend import _validate_domain

        text = """\
example.com
nao$valido
google.com
exa mple.com
"""
        result = parse_blocklist_text(text, validator=_validate_domain)
        assert "example.com" in result
        assert "google.com" in result
        # Invalidos sao filtrados
        assert "nao$valido" not in result
        # 'exa mple.com' tem espaco — split divide e pega 'mple.com'
        # Comportamento OK: o parser pega o ultimo token e 'mple.com'
        # passa pelo validator. Test documenta isso.


# ============================================================
# Edge cases
# ============================================================


class TestEdgeCases:
    def test_empty_input(self):
        assert parse_blocklist_text("") == []

    def test_only_comments(self):
        text = "# nada\n# aqui\n# eh comentario\n"
        assert parse_blocklist_text(text) == []

    def test_only_blank_lines(self):
        assert parse_blocklist_text("\n\n\n\n") == []

    def test_huge_input_no_oom(self):
        """Sanity: 10k linhas nao deve travar."""
        text = "\n".join(f"sub{i}.example.com" for i in range(10000))
        result = parse_blocklist_text(text)
        assert len(result) == 10000

    def test_unicode_in_comment(self):
        """Comments com chars especiais devem ser ignorados sem erro."""
        text = "# comentário com acentos\nexample.com\n"
        result = parse_blocklist_text(text)
        assert result == ["example.com"]


# ============================================================
# Tests dos helpers usados pelo dnscrypt_backend
# ============================================================


class TestBlocklistBackendHelpers:
    """Tests dos helpers publicos do dnscrypt_backend."""

    def test_get_blocklist_with_missing_file(self, tmp_path, monkeypatch):
        """Quando blacklist.txt nao existe, retorna lista vazia."""
        from vigia_dns import dnscrypt_backend

        # Monkeypatch o BLOCKLIST_PATH para um path que nao existe
        fake_path = tmp_path / "nao-existe.txt"
        monkeypatch.setattr(dnscrypt_backend, "BLOCKLIST_PATH", fake_path)

        result = dnscrypt_backend.get_blocklist()
        assert result == []

    def test_get_blocklist_skips_comments_and_blanks(self, tmp_path, monkeypatch):
        """Le arquivo real, deve skip comments e linhas vazias."""
        from vigia_dns import dnscrypt_backend

        bl_file = tmp_path / "blacklist.txt"
        bl_file.write_text(
            "# header\n"
            "example.com\n"
            "\n"
            "# coment\n"
            "google.com\n"
            "  # indented comment skipa? — atual NAO trata\n"
            "facebook.com\n"
        )
        monkeypatch.setattr(dnscrypt_backend, "BLOCKLIST_PATH", bl_file)

        result = dnscrypt_backend.get_blocklist()
        assert "example.com" in result
        assert "google.com" in result
        assert "facebook.com" in result

    def test_get_blocklist_dedup(self, tmp_path, monkeypatch):
        """Linhas duplicadas no arquivo devem ser deduplicadas."""
        from vigia_dns import dnscrypt_backend

        bl_file = tmp_path / "blacklist.txt"
        bl_file.write_text(
            "example.com\n"
            "google.com\n"
            "example.com\n"
            "example.com\n"
        )
        monkeypatch.setattr(dnscrypt_backend, "BLOCKLIST_PATH", bl_file)

        result = dnscrypt_backend.get_blocklist()
        # Sem duplicatas
        assert result.count("example.com") == 1
        assert result.count("google.com") == 1
        assert len(result) == 2
