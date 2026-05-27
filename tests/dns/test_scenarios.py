"""Cenarios completos de interacao do user — v0.3.0 (dnscrypt-only).

Simula a logica de state-tracking da ResolversTab no novo mundo
single-mode. Cobre:

1. Apply server X -> marker "Em uso" em X
2. Troca de tab apos Apply -> cache preserva marker
3. Switch entre servers
4. Activation flow (ensure_dnscrypt_active)
5. Restore systemd-resolved (uninstall path)
"""

from __future__ import annotations

import pytest


class ResolversState:
    """Replica do state-machine da ResolversTab v0.3.

    refresh(expected_active_servers=None) -> usa hint > cache > sistema
    _apply atualiza cache se dados validos
    """

    def __init__(self) -> None:
        self.last_active_servers: list[str] = []

    def refresh(
        self,
        installed: bool,
        active: bool,
        system_servers: list[str],
        expected_servers: list[str] | None = None,
    ) -> list[str]:
        # Seed: hint > cache
        seed = expected_servers
        if seed is None:
            seed = list(self.last_active_servers)

        # Merge com sistema (apenas se installed E active)
        active_servers = list(seed)
        if installed and active:
            for s in system_servers:
                if s not in active_servers:
                    active_servers.append(s)

        # Atualiza cache
        if active_servers:
            self.last_active_servers = list(active_servers)
        return active_servers

    @staticmethod
    def is_server_active(server_id: str, active_servers: list[str]) -> bool:
        return server_id in active_servers


CLOUDFLARE = "cloudflare"
QUAD9 = "quad9-doh-ip4-port443-filter-pri"
MULLVAD = "mullvad-doh"


class TestApplyBasico:
    def test_apply_marca_server_ativo(self):
        s = ResolversState()
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[],  # sistema ainda nao propagou
            expected_servers=[CLOUDFLARE],
        )
        assert s.is_server_active(CLOUDFLARE, servers)

    def test_switch_provider(self):
        s = ResolversState()
        s.refresh(installed=True, active=True,
                  system_servers=[CLOUDFLARE], expected_servers=[CLOUDFLARE])
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[QUAD9], expected_servers=[QUAD9],
        )
        assert s.is_server_active(QUAD9, servers)


class TestTrocaDeTabPreservaMarker:
    """Bug-class: refresh sem hint usa cache."""

    def test_marker_persiste_apos_troca_de_tab(self):
        s = ResolversState()
        # Apply Cloudflare
        s.refresh(installed=True, active=True,
                  system_servers=[CLOUDFLARE], expected_servers=[CLOUDFLARE])
        # Troca tab -> refresh sem hint, sistema vazio
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[], expected_servers=None,
        )
        assert s.is_server_active(CLOUDFLARE, servers)

    def test_multi_troca_de_tab(self):
        s = ResolversState()
        s.refresh(installed=True, active=True,
                  system_servers=[CLOUDFLARE], expected_servers=[CLOUDFLARE])
        for _ in range(5):
            servers = s.refresh(installed=True, active=True, system_servers=[])
            assert s.is_server_active(CLOUDFLARE, servers)


class TestEstadosNaoAtivo:
    """Quando dnscrypt nao esta instalado/ativo."""

    def test_not_installed_no_servers(self):
        s = ResolversState()
        servers = s.refresh(installed=False, active=False, system_servers=[])
        assert servers == []

    def test_installed_but_inactive_uses_cache_seed_only(self):
        """Se instalado mas inativo, NAO consulta sistema mas mantem hint."""
        s = ResolversState()
        # Sem cache, sem hint
        servers = s.refresh(installed=True, active=False, system_servers=[CLOUDFLARE])
        # system_servers ignorado pois active=False
        assert servers == []

    def test_inactive_with_hint_still_shows_marker(self):
        """Edge case: durante o restart o user ja clicou Apply."""
        s = ResolversState()
        servers = s.refresh(
            installed=True, active=False,  # durante restart
            system_servers=[],
            expected_servers=[CLOUDFLARE],
        )
        # Marker mostrado mesmo com active=False (otimismo do hint)
        assert s.is_server_active(CLOUDFLARE, servers)


class TestCacheUpdate:
    def test_empty_refresh_preserves_cache(self):
        s = ResolversState()
        s.refresh(installed=True, active=True,
                  system_servers=[CLOUDFLARE], expected_servers=[CLOUDFLARE])
        original = list(s.last_active_servers)
        # Refresh com sistema vazio
        s.refresh(installed=True, active=True, system_servers=[])
        assert s.last_active_servers == original

    def test_sistema_novo_data_substitui(self):
        s = ResolversState()
        s.refresh(installed=True, active=True,
                  system_servers=[CLOUDFLARE], expected_servers=[CLOUDFLARE])
        # Sistema agora reporta Quad9 (alguem mudou via CLI)
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[QUAD9],
        )
        # Cache acumula — sistema reportou Quad9, mas Cloudflare ainda esta no cache
        # Comportamento documentado: ate proximo Apply via UI, cache esta "pegajoso"
        # mas o sistema vence pra marcar Quad9 tambem
        assert s.is_server_active(QUAD9, servers)


class TestFluxoCompletoDoUser:
    """End-to-end: instala, ativa, escolhe server, troca, restore."""

    def test_fluxo_completo(self):
        s = ResolversState()

        # 1. Primeira execucao: nao instalado
        servers = s.refresh(installed=False, active=False, system_servers=[])
        assert servers == []

        # 2. User instala dnscrypt-proxy (via Tool Installer). Refresh detecta.
        servers = s.refresh(installed=True, active=False, system_servers=[])
        # Ainda nao ativo — sem servers
        assert servers == []

        # 3. User clica "Ativar dnscrypt-proxy" na aba Status. Apos migration:
        #    dnscrypt-proxy roda, mas SEM server selecionado ainda
        servers = s.refresh(installed=True, active=True, system_servers=[])
        assert servers == []

        # 4. User aplica Cloudflare na aba Provedores
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[CLOUDFLARE],
            expected_servers=[CLOUDFLARE],
        )
        assert s.is_server_active(CLOUDFLARE, servers)

        # 5. Troca de tab varias vezes — cache preserva
        for _ in range(3):
            servers = s.refresh(installed=True, active=True, system_servers=[])
            assert s.is_server_active(CLOUDFLARE, servers)

        # 6. Switch pra Mullvad
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[MULLVAD],
            expected_servers=[MULLVAD],
        )
        assert s.is_server_active(MULLVAD, servers)

        # 7. User decide voltar pro systemd-resolved (restore)
        #    Apos restore: dnscrypt parado, cache invalidado (window.py faz isso)
        s.last_active_servers = []  # simulando invalidate
        servers = s.refresh(installed=True, active=False, system_servers=[])
        assert servers == []


class TestMultiServerSetup:
    """User pode aplicar varios servers de uma vez (set_servers_blocking)."""

    def test_multi_server_marca_todos(self):
        s = ResolversState()
        servers = s.refresh(
            installed=True, active=True,
            system_servers=[CLOUDFLARE, QUAD9],
            expected_servers=[CLOUDFLARE, QUAD9],
        )
        assert s.is_server_active(CLOUDFLARE, servers)
        assert s.is_server_active(QUAD9, servers)
