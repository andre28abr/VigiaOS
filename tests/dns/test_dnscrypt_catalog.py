"""Tests para dnscrypt_catalog (catalogo do modo avancado).

Cobertura:
- SERVERS estrutura + sanity
- find_by_id, providers, default_servers
- Metadados (no_logs, no_filter, dnssec, protocol)
"""

from __future__ import annotations

import pytest

from vigia_dns.dnscrypt_catalog import (
    SERVERS,
    DnsCryptServer,
    default_servers,
    find_by_id,
    list_by_provider,
    providers,
)


class TestServersStructure:
    def test_servers_not_empty(self):
        assert len(SERVERS) > 0
        assert len(SERVERS) >= 5  # esperamos catalogo curado, nao trivial

    def test_all_servers_have_id(self):
        for s in SERVERS:
            assert s.id
            assert isinstance(s.id, str)
            # IDs validos para dnscrypt-proxy server_names (chars seguros)
            assert all(c.isalnum() or c in "._-" for c in s.id), \
                f"ID '{s.id}' tem chars invalidos"

    def test_all_servers_have_label(self):
        for s in SERVERS:
            assert s.label
            assert isinstance(s.label, str)

    def test_all_servers_have_provider(self):
        for s in SERVERS:
            assert s.provider

    def test_protocol_is_valid(self):
        valid_protos = {"DoH", "DoT", "DNSCrypt"}
        for s in SERVERS:
            assert s.protocol in valid_protos, \
                f"Protocol '{s.protocol}' de {s.id} invalido"

    def test_no_duplicate_ids(self):
        ids = [s.id for s in SERVERS]
        assert len(ids) == len(set(ids)), "IDs duplicados no catalogo"

    def test_at_least_one_no_filter(self):
        """Pelo menos 1 server sem filtros (escolha pro user paranoid)."""
        unfiltered = [s for s in SERVERS if s.no_filter]
        assert len(unfiltered) >= 1

    def test_at_least_one_with_filters(self):
        """Pelo menos 1 server com filtros (Pi-hole-like alternative)."""
        filtered = [s for s in SERVERS if not s.no_filter]
        assert len(filtered) >= 1

    def test_at_least_one_dnssec(self):
        with_dnssec = [s for s in SERVERS if s.dnssec]
        assert len(with_dnssec) >= 1


class TestFindById:
    def test_find_existing(self):
        # cloudflare deve existir
        result = find_by_id("cloudflare")
        assert result is not None
        assert result.id == "cloudflare"

    def test_find_non_existing(self):
        assert find_by_id("nao-existe-este-server") is None

    def test_find_empty_string(self):
        assert find_by_id("") is None


class TestProvidersListing:
    def test_providers_returns_list(self):
        result = providers()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_providers_no_duplicates(self):
        result = providers()
        assert len(result) == len(set(result))

    def test_providers_sorted(self):
        result = providers()
        assert result == sorted(result)

    def test_providers_includes_main_ones(self):
        result = providers()
        # Sanity: os 3 grandes devem estar
        assert "Cloudflare" in result
        assert "Quad9" in result
        # AdGuard tambem
        assert "AdGuard" in result


class TestListByProvider:
    def test_cloudflare_has_multiple_variants(self):
        cf = list_by_provider("Cloudflare")
        # Cloudflare tem default + security + family
        assert len(cf) >= 2

    def test_nonexisting_provider(self):
        result = list_by_provider("NaoExiste")
        assert result == []


class TestDefaultServers:
    def test_default_servers_returns_list(self):
        result = default_servers()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_default_servers_are_valid_ids(self):
        """Cada server default deve existir no catalogo."""
        for sid in default_servers():
            assert find_by_id(sid) is not None, f"Default server '{sid}' nao existe"


class TestDnsCryptServerDataclass:
    def test_construct(self):
        s = DnsCryptServer(
            id="test-id",
            label="Test",
            provider="TestCo",
            protocol="DoH",
            no_logs=True,
            no_filter=True,
            dnssec=True,
            description="desc",
        )
        assert s.id == "test-id"
        assert s.country == ""  # default
