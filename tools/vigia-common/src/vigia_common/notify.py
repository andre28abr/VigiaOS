"""Notificações de desktop (Gio.Notification) — wrapper fino e à prova de erro.

Qualquer tool/produto chama `notify.send(app, ...)` pra avisar o usuário fora da
janela (update de segurança, IP bloqueado, varredura achou algo). O import de gi
é lazy; se algo falhar, retorna False sem derrubar nada.
"""

from __future__ import annotations


def send(app, ident: str, title: str, body: str,
         icon: str = "br.com.vigia.OS", default_action: str = "") -> bool:
    """Envia uma notificação de desktop pelo `app` (Gio/Adw Application).

    - ident: id estável (mesmo id substitui a notificação anterior).
    - default_action: ação do app ao clicar (ex: "app.show-settings"). Opcional.
    Retorna True se enviou.
    """
    if app is None:
        return False
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio

        n = Gio.Notification.new(title)
        n.set_body(body)
        try:
            n.set_icon(Gio.ThemedIcon.new(icon))
        except Exception:  # noqa: BLE001 — ícone é cosmético
            pass
        if default_action:
            n.set_default_action(default_action)
        app.send_notification(ident, n)
        return True
    except Exception:  # noqa: BLE001 — notificação nunca pode derrubar o app
        return False
