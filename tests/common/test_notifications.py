"""Testes para vigia_common.notifications (Etapa D — notificacoes desktop).

O helper dispara `Gio.Notification` via a `Adw.Application` em execucao.
Como depende de PyGObject/GTK, os testes sao marcados `@pytest.mark.gtk`
(skipados em ambiente sem GI, ex: macOS de dev). Os imports de `gi` ficam
DENTRO dos testes/fixtures pra nao quebrar a *coleta* em maquinas sem
PyGObject — a coleta acontece antes do skip por marker.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def no_default_app(monkeypatch):
    """Forca o caminho 'sem app rodando' (no-op gracioso).

    O ideal seria `Gio.Application.set_default(None)`, mas o binding GI
    marca o argumento como nao-nulavel (`TypeError: Argument 0 does not
    allow None as a value`). Como nenhum teste registra uma GApplication
    default, basta garantir que `get_default()` devolva None —
    monkeypatchamos o metodo (restaurado no teardown pelo monkeypatch)."""
    from gi.repository import Gio
    monkeypatch.setattr(Gio.Application, "get_default", staticmethod(lambda: None))
    yield


@pytest.mark.gtk
class TestNotifyNoApp:
    """Sem app rodando, todo caminho deve ser no-op gracioso (False)."""

    def test_notify_returns_false(self, no_default_app):
        from vigia_common.notifications import notify
        assert notify("titulo", "corpo") is False

    def test_notify_if_unfocused_returns_false(self, no_default_app):
        from vigia_common.notifications import notify_if_unfocused
        assert notify_if_unfocused("titulo", "corpo") is False

    def test_never_raises_on_empty_or_bad_priority(self, no_default_app):
        from vigia_common.notifications import notify
        assert notify("", "") is False
        assert notify("x", priority="inexistente") is False


@pytest.mark.gtk
class TestPriorityMap:
    def test_all_constants_mapped(self):
        from gi.repository import Gio
        from vigia_common import notifications as n
        assert set(n._PRIORITY_MAP) == {
            n.PRIORITY_LOW,
            n.PRIORITY_NORMAL,
            n.PRIORITY_HIGH,
            n.PRIORITY_URGENT,
        }
        assert n._PRIORITY_MAP[n.PRIORITY_HIGH] == Gio.NotificationPriority.HIGH
        assert n._PRIORITY_MAP[n.PRIORITY_URGENT] == Gio.NotificationPriority.URGENT
