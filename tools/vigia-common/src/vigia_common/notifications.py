"""Notificacoes desktop nativas (GNOME Shell) via Gio.Notification.

As tools da Vigia Suite rodam *embedded* no Hub (mesmo processo). Este
helper pega a aplicacao em execucao (`Gio.Application.get_default()`) e
dispara uma notificacao que o GNOME Shell renderiza como qualquer app
nativo: banner no topo + entrada na lista do relogio. A notificacao
persiste mesmo com a janela do Hub escondida (modo tray/background) —
exatamente o caso "rodei um scan e fui fazer outra coisa".

Design:
- **No-op gracioso** se nao houver app rodando (tool standalone fora do
  Hub, ambiente de testes/headless). Nunca levanta excecao pro caller.
- **notif_id estavel**: reenviar com o mesmo id SUBSTITUI a notificacao
  anterior (evita spam de notificacoes repetidas do mesmo evento).
- **Prioridades** com nomes amigaveis ('low'/'normal'/'high'/'urgent').
- **default_action**: por padrao 'app.show-window' (clicar a notif traz
  o Hub ao foco). So e' anexada se a action existir no app — em tool
  standalone, que nao registra 'show-window', a notif fica sem clique.
"""

from __future__ import annotations

from gi.repository import Gio, GLib  # noqa: E402


PRIORITY_LOW = "low"
PRIORITY_NORMAL = "normal"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"

_PRIORITY_MAP = {
    PRIORITY_LOW: Gio.NotificationPriority.LOW,
    PRIORITY_NORMAL: Gio.NotificationPriority.NORMAL,
    PRIORITY_HIGH: Gio.NotificationPriority.HIGH,
    PRIORITY_URGENT: Gio.NotificationPriority.URGENT,
}


def notify(
    title: str,
    body: str = "",
    *,
    notif_id: str | None = None,
    priority: str = PRIORITY_NORMAL,
    icon_name: str | None = None,
    default_action: str | None = "app.show-window",
) -> bool:
    """Dispara uma notificacao desktop nativa. Retorna True se enviada.

    Args:
        title: titulo (linha em negrito).
        body: corpo (texto secundario, pode conter `\\n`).
        notif_id: id estavel — reenviar com o mesmo id substitui a notif
            anterior. Default: id unico por timestamp (cada chamada e' nova).
        priority: 'low' | 'normal' | 'high' | 'urgent'.
        icon_name: nome de icone do tema (ex: 'security-high-symbolic').
            None -> GNOME usa o icone do `.desktop` do app (icone do Vigia).
        default_action: action 'app.xxx' disparada ao clicar a notif.
            Default 'app.show-window' (traz o Hub ao foco). Passe None
            pra notif sem acao de clique.

    Returns:
        True se a notificacao foi enviada; False se nao ha app rodando
        (no-op gracioso) ou se algo falhou. Nunca levanta excecao.
    """
    app = Gio.Application.get_default()
    if app is None:
        return False
    try:
        notif = Gio.Notification.new(title)
        if body:
            notif.set_body(body)
        notif.set_priority(
            _PRIORITY_MAP.get(priority, Gio.NotificationPriority.NORMAL)
        )
        if icon_name:
            notif.set_icon(Gio.ThemedIcon.new(icon_name))
        if default_action and _action_exists(app, default_action):
            notif.set_default_action(default_action)
        if not notif_id:
            notif_id = f"vigia-{GLib.get_monotonic_time()}"
        app.send_notification(notif_id, notif)
        return True
    except Exception:  # pylint: disable=broad-except
        # Notificacao e' best-effort; nunca derruba o caller.
        return False


def notify_if_unfocused(title: str, body: str = "", **kwargs) -> bool:
    """Como `notify()`, mas no-op se uma janela do Vigia estiver focada.

    Caso de uso "scan terminou": se o user ainda esta olhando a tool, o
    dialog in-app ja' avisa — um banner do sistema em cima seria ruido.
    Se ele saiu pra outro app ou minimizou pro tray, o banner e' o unico
    aviso que ele recebe.

    Returns:
        True se enviou; False se uma janela do Vigia estava focada (ou
        se `notify()` nao enviou).
    """
    if _vigia_window_focused():
        return False
    return notify(title, body, **kwargs)


def _vigia_window_focused() -> bool:
    """True se uma janela da app Vigia em execucao esta focada agora."""
    app = Gio.Application.get_default()
    if app is None:
        return False
    try:
        win = app.get_active_window()
        return win is not None and win.is_active()
    except Exception:  # pylint: disable=broad-except
        return False


def _action_exists(app, detailed_action: str) -> bool:
    """Confere se 'app.foo' existe no app (evita warning ao clicar a notif)."""
    try:
        name = detailed_action.split(".", 1)[1] if "." in detailed_action else detailed_action
        return app.lookup_action(name) is not None
    except Exception:  # pylint: disable=broad-except
        return False
