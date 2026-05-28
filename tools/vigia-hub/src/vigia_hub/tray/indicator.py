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

import os
import shutil
import signal
import sys
from pathlib import Path


ICON_NAME = "br.com.vigia.Hub-symbolic"
ICON_USER_DIR = (
    Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps"
)


def _ensure_user_icon_installed() -> None:
    """Copia o icone do pacote pra ~/.local/share/icons/ se ainda nao esta.

    Permite que o tray use icone proprio mesmo sem instalacao system-wide
    (pip install --user nao copia data files pro /usr/share).
    """
    target = ICON_USER_DIR / f"{ICON_NAME}.svg"
    if target.exists():
        return

    # Procura na pasta data do pacote (pip install --user -e .)
    # vigia_hub/ -> ../../data/icons/...
    module_dir = Path(__file__).resolve().parent.parent
    candidate_paths = [
        module_dir.parent.parent
        / "data" / "icons" / "hicolor" / "scalable" / "apps"
        / f"{ICON_NAME}.svg",
        # Sistema (RPM/COPR no futuro)
        Path("/usr/share/icons/hicolor/scalable/apps") / f"{ICON_NAME}.svg",
    ]
    src = next((p for p in candidate_paths if p.is_file()), None)
    if src is None:
        return

    try:
        ICON_USER_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, target)
        # Refresh GTK icon cache (best effort)
        cache_dir = Path.home() / ".local" / "share" / "icons" / "hicolor"
        try:
            import subprocess
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(cache_dir)],
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    except OSError:
        pass  # fallback pro security-high-symbolic


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

    def call_action(action_name: str, params: list | None = None) -> None:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                APP_ID,
                OBJECT_PATH,
                "org.gtk.Actions",
                "Activate",
                GLib.Variant(
                    "(sava{sv})",
                    (action_name, params or [], {}),
                ),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
        except GLib.Error as e:
            sys.stderr.write(
                f"[vigia-hub-tray] D-Bus call '{action_name}' falhou: {e}\n"
            )

    def call_action_str(action_name: str, value: str) -> None:
        """Invoca uma action que recebe um parametro string (ex: show-tool)."""
        call_action(action_name, [GLib.Variant("s", value)])

    # ============================================================
    # Indicator + menu
    # ============================================================

    # Garante que o icone customizado esta em ~/.local/share/icons/
    _ensure_user_icon_installed()

    indicator = AppIndicator.Indicator.new(
        "vigia-hub",
        ICON_NAME,
        AppIndicator.IndicatorCategory.APPLICATION_STATUS,
    )
    # Fallback se icone customizado nao foi encontrado pelo tema
    indicator.set_icon_full(ICON_NAME, "Vigia Hub")
    indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
    # Title tambem aparece como tooltip ao passar mouse no icone
    indicator.set_title("Vigia Hub — Suite de seguranca LGPD")

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

    # Submenu: Abrir modulo (acoes rapidas — abre o Hub ja' na tool)
    QUICK_TOOLS = [
        ("Dashboard", "dashboard"),
        ("Antivirus", "antivirus"),
        ("Rootkit Scanner", "rootkit-scanner"),
        ("File Integrity", "file-integrity"),
        ("Hardening Checks", "hardening-checks"),
    ]
    modules_item = Gtk.MenuItem(label="Abrir modulo")
    modules_menu = Gtk.Menu()
    for label, tool_id in QUICK_TOOLS:
        mi = Gtk.MenuItem(label=label)
        mi.connect(
            "activate",
            lambda _w, tid=tool_id: call_action_str("show-tool", tid),
        )
        modules_menu.append(mi)
    modules_item.set_submenu(modules_menu)
    menu.append(modules_item)

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
    # Status vivo: tooltip (title) + item de info no topo do menu.
    # Reaproveita vigia_hub.status (puro Python — sem GTK4). Refresh
    # a cada 2 min: barato (so shutil.which + leitura de relatorios).
    # ============================================================

    def refresh_status() -> bool:
        line = "Vigia Hub"
        try:
            from .. import status as status_mod
            line = status_mod.tray_tooltip()
        except Exception as e:  # best-effort; nunca derruba o tray
            sys.stderr.write(f"[vigia-hub-tray] status falhou: {e}\n")
        indicator.set_title(line)
        info_item.set_label(line)
        return True  # mantem o timer GLib ativo

    refresh_status()
    GLib.timeout_add_seconds(120, refresh_status)

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
