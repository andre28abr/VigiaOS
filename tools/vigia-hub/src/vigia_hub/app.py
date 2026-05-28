"""Application root (Adw.Application).

Comportamento de tray icon + background mode (v0.5.3):

- Se settings.show_tray esta ON:
  - app.hold() na inicializacao -> processo sobrevive a fechar janela
  - TrayManager spawna subprocess vigia-hub-tray (GTK3)
  - Close-request da janela: esconde em vez de matar
  - Tray invoca Gio actions: show-window / show-settings / quit-hub

- Se start_minimized=True (CLI flag --minimized):
  - Janela NAO aparece na inicializacao (so spawna o tray)

- Gio.SimpleAction registradas:
  - show-window  -> traz janela ao foco
  - show-settings -> mostra a aba Configuracoes
  - quit-hub      -> mata o app de vez (e o tray subprocess)
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from . import __app_id__
from .settings import load_settings
from .tray import TrayManager
from .window import VigiaHubWindow


class VigiaHubApp(Adw.Application):
    def __init__(self, start_minimized: bool = False) -> None:
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._start_minimized = start_minimized
        self._tray = TrayManager()
        self._hold_active = False

        self._setup_actions()
        self.connect("shutdown", self._on_shutdown)

    # ============================================================
    # Actions registradas no D-Bus (Gio.SimpleAction)
    # ============================================================

    def _setup_actions(self) -> None:
        """Registra actions invocaveis pelo tray via D-Bus."""
        for name, handler in (
            ("show-window", self._on_action_show_window),
            ("show-settings", self._on_action_show_settings),
            ("quit-hub", self._on_action_quit_hub),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

    def _on_action_show_window(self, *_args) -> None:
        """Tray pediu pra mostrar a janela."""
        win = self._ensure_window()
        win.set_visible(True)
        win.present()

    def _on_action_show_settings(self, *_args) -> None:
        """Tray pediu pra mostrar Configuracoes."""
        win = self._ensure_window()
        win.set_visible(True)
        win.present()
        win.show_settings_view()

    def _on_action_quit_hub(self, *_args) -> None:
        """Tray pediu pra sair de vez (mata processo + tray)."""
        # Release o hold pra app.quit() conseguir terminar
        if self._hold_active:
            self.release()
            self._hold_active = False
        self.quit()

    # ============================================================
    # Lifecycle
    # ============================================================

    def do_activate(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        settings = load_settings()

        # Tray + hold (se habilitado)
        if settings.show_tray:
            self._enable_tray()

        win = self._ensure_window()

        # Iniciar minimizado: so faz sentido se tray esta ON (senao
        # nao tem como o user trazer a janela de volta facil)
        if self._start_minimized and settings.show_tray:
            # Nao apresenta a janela. Tray ja' foi spawnado.
            return

        win.set_visible(True)
        win.present()

    def _ensure_window(self) -> VigiaHubWindow:
        """Retorna a janela existente ou cria uma nova."""
        win = self.get_active_window()
        if win is None:
            win = VigiaHubWindow(self)
            win.connect("close-request", self._on_window_close_request)
        return win  # type: ignore[return-value]

    def _on_window_close_request(self, win: VigiaHubWindow) -> bool:
        """Intercepta close. Se tray ON, esconde em vez de matar.

        Retorna True pra bloquear o close default. False pra deixar fechar.
        """
        settings = load_settings()
        if settings.show_tray and self._tray.is_running():
            win.set_visible(False)
            return True  # bloqueia close
        return False  # comportamento normal: fecha (e mata app)

    def _on_shutdown(self, *_args) -> None:
        """App vai morrer — garantir que o subprocess do tray morre junto."""
        self._tray.stop()

    # ============================================================
    # Tray helpers
    # ============================================================

    def enable_tray(self) -> tuple[bool, str]:
        """Liga o tray dinamicamente (chamado pelo switch da Config)."""
        return self._enable_tray()

    def disable_tray(self) -> None:
        """Desliga o tray dinamicamente."""
        self._tray.stop()
        if self._hold_active:
            self.release()
            self._hold_active = False

    def _enable_tray(self) -> tuple[bool, str]:
        ok, err = self._tray.start()
        if not ok:
            return (False, err)
        if not self._hold_active:
            self.hold()
            self._hold_active = True
        return (True, "")
