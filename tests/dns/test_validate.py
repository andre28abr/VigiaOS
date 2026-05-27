"""Tests para validators do DNS Manager (security-critical).

Cobertura:
- _validate_domain (anti-injection em blocklists)
- _validate_servers (anti-injection em resolved.conf)
- URL regex em import_blocklist_from_url
"""

from __future__ import annotations

import re

import pytest

from vigia_dns.dnscrypt_backend import _validate_domain


class TestValidateDomain:
    """Validacao de dominio para blocklist (anti-injection)."""

    # ===== Aceitos =====

    @pytest.mark.parametrize("domain", [
        "example.com",
        "sub.example.com",
        "a.b.c.d.example.com",
        "*.example.com",          # wildcard
        "192-static.host.com",     # numeros + hifen
        "x.co",                    # curto
        "very-long-but-valid-name.example.com",
    ])
    def test_accepts_valid(self, domain):
        ok, _ = _validate_domain(domain)
        assert ok, f"Deveria aceitar: {domain}"

    def test_underscore_not_accepted(self):
        """Validator atual NAO aceita underscore (regex strict).

        Documenta comportamento — RFC 1035 nao permite underscore em
        hostnames, mas alguns DNS (Microsoft AD) usam. Por seguranca,
        validator e' strict.
        """
        ok, _ = _validate_domain("underscore_test.com")
        assert not ok

    # ===== Rejeitados =====

    @pytest.mark.parametrize("domain", [
        "",                                # vazio
        "a" * 254,                         # > 253
        ".example.com",                    # comeca com .
        "example.com.",                    # termina com .
        "exa..mple.com",                   # .. duplicado
        "example com",                     # espaco
        "example;rm -rf",                  # shell injection
        "example|whoami",                  # pipe
        "example`cmd`",                    # backtick
        "example$VAR",                     # var expansion
        "exa'mple",                        # aspas
        'exa"mple',                        # aspas duplas
        "example\nnewline",                # newline
        "exa\x00mple",                     # null byte
        "exa/mple",                        # slash (path)
        "exa\\mple",                       # backslash
    ])
    def test_rejects_invalid(self, domain):
        ok, err = _validate_domain(domain)
        assert not ok, f"Deveria rejeitar: {domain!r}"
        assert err  # erro nao-vazio

    def test_too_long_rejected(self):
        ok, err = _validate_domain("a" * 254)
        assert not ok
        assert "longo" in err.lower() or "long" in err.lower()


# v0.3.0: removida TestValidateServers — `backend._validate_servers`
# era do systemd-resolved (deletado nessa versao). dnscrypt-proxy
# usa server names (validados em test_dnscrypt_backend_helpers.py),
# nao IPs.


class TestUrlValidationForBlocklistImport:
    """URL regex em dnscrypt_backend.import_blocklist_from_url.

    Pattern: ^https?://[a-zA-Z0-9._\\-/?=&#:%]+$
    """

    URL_PATTERN = re.compile(r"^https?://[a-zA-Z0-9._\-/?=&#:%]+$")

    @pytest.mark.parametrize("url", [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "https://easylist.to/easylist/easyprivacy.txt",
        "https://small.oisd.nl/",
        "http://example.com/list.txt",
        "https://example.com:443/path/to/list.txt",
        "https://example.com?q=1&r=2",
    ])
    def test_accepts_valid_urls(self, url):
        assert self.URL_PATTERN.match(url), f"Deveria aceitar: {url}"

    @pytest.mark.parametrize("url", [
        "",
        "ftp://example.com/list.txt",          # protocolo nao suportado
        "javascript:alert(1)",                  # XSS attempt
        "file:///etc/passwd",                   # local file
        "https://example.com/path with space",  # espaco
        "https://example.com/list.txt; cmd",    # injection
        "https://example.com/`cmd`",            # backtick
        "https://example.com/$(cmd)",           # subshell
        "https:// example.com/",                # espaco depois do scheme
    ])
    def test_rejects_invalid_urls(self, url):
        assert not self.URL_PATTERN.match(url), f"Deveria rejeitar: {url!r}"
