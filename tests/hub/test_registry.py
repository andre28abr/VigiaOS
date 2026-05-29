"""Testes do registry do Hub.

Cobre visible_tools() (esconde atomic_only no Workstation — B3),
tools_by_category() e os metodos de ToolEntry.

NOTA de mock: registry.py faz `from vigia_common.platform import is_atomic`
no topo, entao monkeypatcha-se `registry.is_atomic` (NAO o de platform).
"""

from __future__ import annotations

from pathlib import Path

from vigia_hub import registry
from vigia_hub.registry import TOOLS, ToolEntry, tools_by_category, visible_tools


def _entry(id_, category="monitoramento", atomic_only=False, **kw):
    return ToolEntry(
        id=id_,
        name=id_,
        description="x",
        icon_path=Path("/nonexistent.svg"),
        exec_cmd=[id_],
        category=category,
        atomic_only=atomic_only,
        **kw,
    )


class TestVisibleTools:
    def test_atomic_shows_all(self, monkeypatch):
        monkeypatch.setattr(registry, "is_atomic", lambda: True)
        vis = visible_tools()
        assert len(vis) == len(TOOLS)
        assert any(t.id == "deployments-manager" for t in vis)

    def test_workstation_hides_atomic_only(self, monkeypatch):
        monkeypatch.setattr(registry, "is_atomic", lambda: False)
        vis = visible_tools()
        assert not any(t.id == "deployments-manager" for t in vis)
        # Calculado dinamicamente => sobrevive a novas tools atomic_only.
        expected = len([t for t in TOOLS if not t.atomic_only])
        assert len(vis) == expected

    def test_workstation_keeps_normal_tools(self, monkeypatch):
        monkeypatch.setattr(registry, "is_atomic", lambda: False)
        ids = {t.id for t in visible_tools()}
        assert "dashboard" in ids
        assert "dns-manager" in ids

    def test_result_is_subset_without_dupes(self, monkeypatch):
        monkeypatch.setattr(registry, "is_atomic", lambda: False)
        vis = visible_tools()
        assert all(t in TOOLS for t in vis)
        assert len({id(t) for t in vis}) == len(vis)


class TestToolsByCategory:
    def test_respects_category_order(self):
        tools = [
            _entry("a", category="relatorios"),
            _entry("b", category="monitoramento"),
            _entry("c", category="defesa"),
        ]
        # CATEGORIES_ORDER = monitoramento, privacidade, defesa, sistema, relatorios
        assert list(tools_by_category(tools).keys()) == [
            "monitoramento", "defesa", "relatorios",
        ]

    def test_empty_categories_dropped(self):
        grouped = tools_by_category([_entry("a", category="monitoramento")])
        assert list(grouped.keys()) == ["monitoramento"]

    def test_all_real_tools_grouped(self):
        grouped = tools_by_category(TOOLS)
        assert sum(len(v) for v in grouped.values()) == len(TOOLS)
        assert all(cat in registry.CATEGORY_LABELS for cat in grouped)

    def test_unknown_category_excluded(self):
        assert tools_by_category([_entry("a", category="inexistente")]) == {}


class TestToolEntryMethods:
    def test_available_fn_raising_is_false(self):
        assert _entry("x", available_fn=lambda: 1 / 0).is_available() is False

    def test_embeddable_true(self):
        e = _entry("x", available_fn=lambda: True, embedded_module="m.w")
        assert e.is_embeddable() is True

    def test_embeddable_false_when_unavailable(self):
        e = _entry("x", available_fn=lambda: False, embedded_module="m.w")
        assert e.is_embeddable() is False

    def test_embeddable_false_when_no_module(self):
        e = _entry("x", available_fn=lambda: True, embedded_module=None)
        assert e.is_embeddable() is False
