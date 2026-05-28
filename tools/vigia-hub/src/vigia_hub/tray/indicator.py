"""Standalone tray icon (GTK3 + AyatanaAppIndicator3).

Rodado como subprocess pelo Hub principal (GTK4) — GTK3 e GTK4 nao
podem coexistir num mesmo processo PyGObject.

Comunicacao com o Hub (que tem application_id 'br.com.vigia.Hub')
via D-Bus actions registradas pelo Adw.Application:
- 'show-window' -> trazer janela ao foco
- 'show-settings' -> abrir janela na aba Configuracoes
- 'quit-hub' -> matar o Hub de vez (e este tray junto)

Entry point: `vigia-hub-tray` (registrado no pyproject.toml).
"""

from __future__ import annotations

import signal
import sys


def main() -> int:
    """Cria o tray icon e roda mainloop GTK3."""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import (  # noqa: E402
            AyatanaAppIndicator3 as AppIndicator,
            Gio,
            GLib,
            Gtk,
        )
    except (ValueError, ImportError) as e:
        print(
            f"[vigia-hub-tray] Falha ao carregar dependencias: {e}\n"
            "Instale: rpm-ostree install libayatana-appindicator-gtk3",
            file=sys.stderr,
        )
        return 1

    APP_ID = "br.com.vigia.Hub"
    OBJECT_PATH = "/br/com/vigia/Hub"

    # ============================================================
    # D-Bus: invoca actions do Hub via Gio.DBusActionGroup
    # ============================================================

    def call_action(action_name: str) -> None:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                APP_ID,
                OBJECT_PATH,
                "org.gtk.Actions",
                "Activate",
                GLib.Variant(
                    "(sava{sv})",
                    (action_name, [], {}),
                ),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
        except GLib.Error as e:
            print(
                f"[vigia-hub-tray] D-Bus call '{action_name}' falhou: {e}",
                file=sys.stderr,
            )

    # ============================================================
    # Indicator + menu
    # ============================================================

    indicator = AppIndicator.Indicator.new(
        "vigia-hub",
        "br.com.vigia.Hub",  # icon name (precisa de .desktop + icon)
        AppIndicator.IndicatorCategory.APPLICATION_STATUS,
    )
    # Fallback icon caso o icone customizado nao seja encontrado
    indicator.set_icon_full("security-high-symbolic", "Vigia Hub")
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    indicator.set_title("Vigia Hub")

    menu = Gtk.Menu()

    # Item: titulo (info, dim, nao clicavel)
    info_item = Gtk.MenuItem(label="Vigia Hub - rodando")
    info_item.set_sensitive(False)
    menu.append(info_item)

    menu.append(Gtk.SeparatorMenuItem())

    # Item: Abrir Hub
    open_item = Gtk.MenuItem(label="Abrir Hub")
    open_item.connect("activate", lambda _: call_action("show-window"))
    menu.append(open_item)

    # Item: Configuracoes
    settings_item = Gtk.MenuItem(label="Configuracoes")
    settings_item.connect("activate", lambda _: call_action("show-settings"))
    menu.append(settings_item)

    menu.append(Gtk.SeparatorMenuItem())

    # Item: Sair (mata Hub + este subprocess)
    quit_item = Gtk.MenuItem(label="Sair do Vigia")
    quit_item.connect("activate", lambda _: call_action("quit-hub"))
    menu.append(quit_item)

    menu.show_all()
    indicator.set_menu(menu)

    # Clique simples (botao esquerdo): abrir Hub
    indicator.set_secondary_activate_target(open_item)

    # ============================================================
    # Sinais POSIX: SIGTERM/SIGINT pra sair limpo
    # ============================================================

    def _on_signal(*_args) -> None:
        Gtk.main_quit()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    # GLib precisa de unix_signal_add pra integrar com mainloop
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: _on_signal() or False)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: _on_signal() or False)

    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
