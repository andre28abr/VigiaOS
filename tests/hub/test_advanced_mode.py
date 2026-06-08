"""Testes do Modo Avançado (filtro do catálogo do Hub) — puro, sem GTK."""

from __future__ import annotations

from vigia_hub.registry import ADVANCED_TOOLS, TOOLS, visible_tools

ALL_IDS = {t.id for t in TOOLS}


def test_advanced_tools_are_real_ids():
    # toda tool marcada como avançada existe mesmo no catálogo
    assert ADVANCED_TOOLS <= ALL_IDS


def test_advanced_set_is_the_expected_five():
    assert ADVANCED_TOOLS == frozenset({
        "activity-log", "selinux-gui", "file-integrity",
        "capabilities-inspector", "reports",
    })


def test_simple_mode_hides_advanced():
    ids = {t.id for t in visible_tools(TOOLS, advanced=False)}
    assert ids.isdisjoint(ADVANCED_TOOLS)
    assert ids == ALL_IDS - ADVANCED_TOOLS


def test_advanced_mode_shows_everything():
    assert {t.id for t in visible_tools(TOOLS, advanced=True)} == ALL_IDS


def test_simple_keeps_the_essentials():
    simple_ids = {t.id for t in visible_tools(TOOLS, advanced=False)}
    for essential in ("privacy-controls", "dns-manager", "firewall-gui",
                      "antivirus", "rootkit-scanner", "hardening-checks"):
        assert essential in simple_ids


def test_visible_tools_returns_new_list():
    # não devolve o objeto original (evita mutação acidental do registry)
    out = visible_tools(TOOLS, advanced=True)
    assert out is not TOOLS
    assert out == TOOLS
