"""Tests para o optimistic-update do refresh — v0.2.6.

O bug que motivou: depois do user clicar Aplicar, `backend.get_status()`
podia retornar dados stale (race com restart do systemd-resolved).
Sem global_dns populado, o marcador "Em uso" nao aparecia → user via
o botao "Aplicar" mesmo apos sucesso.

Fix: `refresh(expected_active_ips=[...])` aceita hint do que deve estar
ativo. Esse hint eh seed do `active_dns_ips` ANTES de consultar o
sistema — entao mesmo se o sistema retornar [], a UI marca certo.

Como nao podemos importar a UI (GTK precisa de display), testamos a
LOGICA de coleta isolada: dado um `expected_ips` + um `system_ips` que
pode estar vazio, o `active_dns_ips` final deve conter ambos sem dup.
"""

from __future__ import annotations

import pytest


def collect_active_ips(
    expected_ips: list[str],
    system_ips: list[str],
) -> list[str]:
    """Replica da logica do _refresh_worker v0.2.6.

    Seed com expected, merge com system, dedup mantendo ordem.
    """
    active: list[str] = list(expected_ips)
    for ip in system_ips:
        if ip not in active:
            active.append(ip)
    return active


def is_resolver_active(
    resolver_servers_v4: list[str],
    active_dns_ips: list[str],
) -> bool:
    """Replica do match em _apply_mode."""
    active_set = set(active_dns_ips)
    return any(s in active_set for s in resolver_servers_v4)


class TestOptimisticUpdate:
    """Fluxo: user clica Aplicar Cloudflare → expected_ips chega na UI."""

    def test_system_empty_but_expected_marks_active(self):
        """Caso critico: backend retornou vazio mas expected tem os IPs.

        Esse era exatamente o bug pre-v0.2.6.
        """
        # Sistema retornou vazio (race com restart)
        system_ips: list[str] = []
        # User aplicou Cloudflare
        expected_ips = ["1.1.1.1", "1.0.0.1"]

        active = collect_active_ips(expected_ips, system_ips)
        assert active == ["1.1.1.1", "1.0.0.1"]

        # Cloudflare row deve ficar marcada como ativa
        cloudflare_servers = ["1.1.1.1", "1.0.0.1"]
        assert is_resolver_active(cloudflare_servers, active) is True

    def test_system_has_data_no_expected(self):
        """Refresh normal (sem Apply recente) — so sistema importa."""
        system_ips = ["1.1.1.1", "1.0.0.1"]
        expected_ips: list[str] = []

        active = collect_active_ips(expected_ips, system_ips)
        assert "1.1.1.1" in active
        assert "1.0.0.1" in active

    def test_both_have_data_merge_no_dup(self):
        """Expected e sistema concordam — sem duplicacao."""
        expected_ips = ["1.1.1.1", "1.0.0.1"]
        system_ips = ["1.1.1.1", "1.0.0.1"]

        active = collect_active_ips(expected_ips, system_ips)
        assert active == ["1.1.1.1", "1.0.0.1"]
        assert len(active) == 2

    def test_system_has_extra_ips(self):
        """Sistema tem mais IPs que o expected (per-interface DNS)."""
        expected_ips = ["1.1.1.1"]
        system_ips = ["192.168.1.1", "1.1.1.1"]

        active = collect_active_ips(expected_ips, system_ips)
        # Mantem ordem: expected primeiro, depois system extras
        assert active[0] == "1.1.1.1"
        assert "192.168.1.1" in active

    def test_completely_different_ips(self):
        """User aplicou Cloudflare mas sistema mostra outra coisa.

        Edge case: race extrema ou sistema ainda nao propagou.
        """
        expected_ips = ["1.1.1.1"]  # Cloudflare
        system_ips = ["9.9.9.9"]    # Quad9 (stale)

        active = collect_active_ips(expected_ips, system_ips)
        # Ambos aparecem
        assert "1.1.1.1" in active
        assert "9.9.9.9" in active
        # Cloudflare row vai marcar (porque tem 1.1.1.1)
        assert is_resolver_active(["1.1.1.1", "1.0.0.1"], active) is True
        # Quad9 row tambem marca (porque tem 9.9.9.9 ainda no sistema)
        assert is_resolver_active(["9.9.9.9", "149.112.112.112"], active) is True

    def test_resolver_not_in_active_stays_inactive(self):
        """Resolver que nao bate com nada — nao deve marcar."""
        active = collect_active_ips(["1.1.1.1"], [])
        # Mullvad nao tem 1.1.1.1
        mullvad_servers = ["194.242.2.2", "194.242.2.3"]
        assert is_resolver_active(mullvad_servers, active) is False


class TestOptimisticUpdateAdvancedMode:
    """Mesma logica para dnscrypt-proxy server names."""

    def collect_active_servers(
        self, expected: list[str], system: list[str],
    ) -> list[str]:
        active = list(expected)
        for s in system:
            if s not in active:
                active.append(s)
        return active

    def test_system_empty_expected_marks_active(self):
        """Pos-Apply: dc.get_status pode demorar pra refletir."""
        system: list[str] = []
        expected = ["cloudflare-security"]

        active = self.collect_active_servers(expected, system)
        assert "cloudflare-security" in active

    def test_dedup_advanced(self):
        active = self.collect_active_servers(
            ["cloudflare"], ["cloudflare", "quad9"],
        )
        assert active.count("cloudflare") == 1
        assert "quad9" in active


class TestRefreshSignaturePreservesBackcompat:
    """O `refresh()` sem args deve continuar funcionando como antes."""

    def test_no_hints_means_empty_seed(self):
        """Chamada `refresh()` sem hints — expected fica []."""
        active = collect_active_ips([], ["1.1.1.1"])
        # So tem o que o sistema reporta
        assert active == ["1.1.1.1"]

    def test_none_treated_as_empty(self):
        """Caller passa None — deve ser tratado como []."""
        # A UI faz `expected_active_ips or []` ao chamar refresh
        normalized = None or []
        active = collect_active_ips(normalized, ["1.1.1.1"])
        assert active == ["1.1.1.1"]
