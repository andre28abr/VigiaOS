"""Itens do sininho de notificações do rail — modelo puro + builders.

Distinto de `vigia_common.notifications` (esse dispara notificações *desktop*
via `Gio.Notification` e puxa `gi`). Aqui **não** há GTG/gi: é só o dado que o
widget `NotificationsBell` (em `notifications_bell.py`) renderiza. Assim o
backend do instalador monta `Notification` sem puxar PyGObject, e a lógica
fica testável no macOS/CI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Notification:
    """Uma linha do popover do sininho."""

    title: str
    subtitle: str = ""
    icon: str = "software-update-available-symbolic"


def module_dep_notifications(items) -> "list[Notification]":
    """Monta notificações de dependência faltando.

    `items`: iterável de `(nome_modulo, [labels_faltando])`. Gera uma
    notificação por módulo que tem alguma dependência externa ausente.
    """
    out: list[Notification] = []
    for name, missing in items:
        missing = [m for m in missing if m]
        if missing:
            out.append(Notification(
                f"{name}: falta dependência",
                "Instale: " + ", ".join(missing),
                "dialog-warning-symbolic",
            ))
    return out
