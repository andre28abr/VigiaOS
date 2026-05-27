"""Tests para o optimistic update do StatusTab — v0.2.8.

Bug reportado pelo user: depois de aplicar provedor em Provedores,
a aba Status demorava ~2min pra hero ficar verde (mostrava
"Sem DNS configurado" enquanto resolvectl status nao propagava).

Fix: StatusTab tambem usa cache (`_last_known_dns`/`_last_known_dot`)
+ hint (`expected_dns`/`expected_dot` no refresh). Window.py wirea
ResolversTab.on_provider_applied -> StatusTab.refresh(hint).

Como nao podemos importar GTK aqui (precisa de display), testamos a
LOGICA do _refresh_worker isoladamente — simula o merge de hint
+ cache + sistema.
"""

from __future__ import annotations

import pytest


def merge_status(
    system_current: list[str],
    system_global: list[str],
    system_dot: str,
    expected_dns: list[str],
    expected_dot: str,
    cache_dns: list[str],
    cache_dot: str,
) -> tuple[list[str], list[str], str, list[str], str]:
    """Replica da logica de merge do StatusTab._refresh_worker.

    Retorna (current_final, global_final, dot_final, cache_dns_new, cache_dot_new).
    """
    current = list(system_current)
    glb = list(system_global)
    dot = system_dot

    # Fallback se sistema vazio
    if not current and not glb:
        if expected_dns:
            glb = list(expected_dns)
        elif cache_dns:
            glb = list(cache_dns)
    if not dot:
        if expected_dot:
            dot = expected_dot
        elif cache_dot:
            dot = cache_dot

    # Atualiza cache apenas com dados nao-vazios
    if current or glb:
        cache_dns_new = list(current or glb)
    else:
        cache_dns_new = list(cache_dns)
    if dot:
        cache_dot_new = dot
    else:
        cache_dot_new = cache_dot

    return current, glb, dot, cache_dns_new, cache_dot_new


CLOUDFLARE = ["1.1.1.1", "1.0.0.1"]
QUAD9 = ["9.9.9.9", "149.112.112.112"]


class TestHintTrazHeroVerdeImediato:
    """Bug do user: 'demorou 2 min pra ficar verde'.

    Cenario: user aplica Cloudflare em Provedores, vai pra Status.
    Sistema ainda nao propagou (race), hero ficaria amarelo
    'Sem DNS configurado'. Fix: hint do Resolvers chega.
    """

    def test_sistema_vazio_mas_hint_resolve(self):
        """Hint salva quando sistema ainda nao reportou."""
        current, glb, dot, _, _ = merge_status(
            system_current=[],
            system_global=[],
            system_dot="",
            expected_dns=CLOUDFLARE,
            expected_dot="yes",
            cache_dns=[],
            cache_dot="",
        )
        # current ainda vazio (so global e' setado via hint)
        assert glb == CLOUDFLARE
        assert dot == "yes"
        # Apply hint quer dizer que a tela mostra DNS configurado

    def test_sistema_vazio_cache_resolve(self):
        """Sem hint, cache ainda salva (refresh manual apos Apply)."""
        current, glb, dot, _, _ = merge_status(
            system_current=[],
            system_global=[],
            system_dot="",
            expected_dns=[],
            expected_dot="",
            cache_dns=CLOUDFLARE,
            cache_dot="yes",
        )
        assert glb == CLOUDFLARE
        assert dot == "yes"

    def test_sistema_responde_substitui_hint(self):
        """Quando sistema retorna, usa o que ele disse."""
        current, glb, dot, _, _ = merge_status(
            system_current=["1.1.1.1"],
            system_global=CLOUDFLARE,
            system_dot="yes",
            expected_dns=CLOUDFLARE,
            expected_dot="yes",
            cache_dns=[],
            cache_dot="",
        )
        # Sistema venceu
        assert current == ["1.1.1.1"]
        assert glb == CLOUDFLARE


class TestCacheUpdate:
    """O cache deve atualizar apenas com dados nao-vazios."""

    def test_cache_atualiza_com_dados_validos(self):
        _, _, _, new_cache, new_dot = merge_status(
            system_current=["1.1.1.1"],
            system_global=CLOUDFLARE,
            system_dot="yes",
            expected_dns=[], expected_dot="",
            cache_dns=[], cache_dot="",
        )
        assert new_cache == ["1.1.1.1"]
        assert new_dot == "yes"

    def test_cache_preserva_se_sistema_vazio(self):
        """Se sistema retorna vazio, cache anterior preserva."""
        _, _, _, new_cache, new_dot = merge_status(
            system_current=[],
            system_global=[],
            system_dot="",
            expected_dns=[], expected_dot="",
            cache_dns=CLOUDFLARE, cache_dot="yes",
        )
        assert new_cache == CLOUDFLARE
        assert new_dot == "yes"

    def test_cache_substitui_quando_sistema_responde_diferente(self):
        """Cache antigo: Quad9. Sistema responde Cloudflare → cache vai pra Cloudflare."""
        _, _, _, new_cache, _ = merge_status(
            system_current=[],
            system_global=CLOUDFLARE,
            system_dot="yes",
            expected_dns=[], expected_dot="",
            cache_dns=QUAD9, cache_dot="yes",
        )
        assert new_cache == CLOUDFLARE


class TestSemDnsConfiguradoBugReporter:
    """O bug que o user reportou: 'Sem DNS configurado' demora 2min.

    Esse teste valida que com o fix, mesmo no pior cenario (sistema
    DEMORA muito), o hero NAO mostra 'Sem DNS configurado' por mais
    tempo do que necessario.
    """

    def test_apply_event_to_status_render(self):
        """Simula o fluxo: Apply -> Status com hint."""
        # Estado inicial: vazio (antes de Apply)
        _, glb1, _, cache1, _ = merge_status(
            system_current=[], system_global=[], system_dot="",
            expected_dns=[], expected_dot="",
            cache_dns=[], cache_dot="",
        )
        assert glb1 == []  # hero seria "Sem DNS configurado"

        # User clica Aplicar Cloudflare em Provedores. Window.py
        # chama status_tab.refresh(expected_dns=CLOUDFLARE).
        # Sistema ainda nao propagou.
        _, glb2, dot2, cache2, _ = merge_status(
            system_current=[], system_global=[], system_dot="",
            expected_dns=CLOUDFLARE, expected_dot="yes",
            cache_dns=cache1, cache_dot="",
        )
        # Hero agora ja eh verde com Cloudflare!
        assert glb2 == CLOUDFLARE
        assert dot2 == "yes"
        # Cache atualizou pra Cloudflare via hint
        assert cache2 == CLOUDFLARE

        # 30s depois, refresh manual ou auto. Sistema ainda lerdo.
        _, glb3, dot3, _, _ = merge_status(
            system_current=[], system_global=[], system_dot="",
            expected_dns=[], expected_dot="",
            cache_dns=cache2, cache_dot=dot2,
        )
        # Cache mantem Cloudflare visivel
        assert glb3 == CLOUDFLARE
        assert dot3 == "yes"

        # 2min depois, sistema finalmente responde.
        _, glb4, dot4, _, _ = merge_status(
            system_current=["1.1.1.1"], system_global=CLOUDFLARE, system_dot="yes",
            expected_dns=[], expected_dot="",
            cache_dns=cache2, cache_dot=dot2,
        )
        assert glb4 == CLOUDFLARE  # consistente, sem flick
        assert dot4 == "yes"
