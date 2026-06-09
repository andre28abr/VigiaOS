"""Testes do wrapper de notificação — contrato à prova de erro (sem GTK)."""

from __future__ import annotations

from vigia_common import notify


def test_send_without_app_returns_false():
    # Sem app (ou sem GTK), não levanta — só devolve False.
    assert notify.send(None, "id", "Título", "Corpo") is False


def test_send_with_broken_app_returns_false():
    class _Broken:
        def send_notification(self, *_a):
            raise RuntimeError("boom")

    # Mesmo com um "app" que explode, nunca propaga exceção.
    assert notify.send(_Broken(), "id", "t", "b") is False
