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

Comportamento de password_lock + autostart + minimized (v0.5.10):

  Combinacao | Quando pede senha
  -----------|------------------
  Lock=ON, sem autostart, sem minimized -> startup (sync, antes de mostrar janela)
  Lock=ON, autostart+minimized          -> quando user clicar 'Abrir Hub' no tray
  Lock=ON, autostart sem minimized      -> startup (janela vai ser mostrada)

  Logica: se vai iniciar SEM janela visivel (minimized), nao tem porque
  pedir senha agora — a sessao 'real' so comeca quando user expandir
  pelo tray. Adia o prompt pra esse momento.

  Apos primeira autenticacao na sessao (self._authed=True), futuras
  expansoes do tray NAO pedem senha de novo.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from . import __app_id__
from .auth import check_auth, check_auth_async
from .logging_setup import get_logger
from .settings import load_settings
from .theme import apply_theme, normalize_mode
from .tray import TrayManager
from .window import VigiaHubWindow


_log = get_logger("vigia_hub.app")


class VigiaHubApp(Adw.Application):
    def __init__(self, start_minimized: bool = False) -> None:
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._start_minimized = start_minimized
        self._tray = TrayManager()
        self._hold_active = False
        self._authed = False  # True apos passar o check_auth da sessao

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
        """Tray pediu pra mostrar a janela. Pode precisar de auth primeiro."""
        self._auth_then(self._present_window)

    def _on_action_show_settings(self, *_args) -> None:
        """Tray pediu pra mostrar Configuracoes."""
        def after_auth():
            self._present_window()
            win = self.get_active_window()
            if win is not None and hasattr(win, "show_settings_view"):
                win.show_settings_view()  # type: ignore[union-attr]
        self._auth_then(after_auth)

    def _on_action_quit_hub(self, *_args) -> None:
        """Tray pediu pra sair de vez (mata processo + tray)."""
        # Release o hold pra app.quit() conseguir terminar
        if self._hold_active:
            self.release()
            self._hold_active = False
        self.quit()

    def _present_window(self) -> None:
        """Mostra a janela (cria se nao existe)."""
        win = self._ensure_window()
        win.set_visible(True)
        win.present()

    def _auth_then(self, callback) -> None:
        """Se precisa auth, pede async e chama callback() apos sucesso.

        Se nao precisa (lock OFF ou ja' autenticado), chama callback direto.
        Se auth falhar, NAO chama callback — mantem o tray, ignora a acao.
        """
        settings = load_settings()
        if not settings.password_lock or self._authed:
            callback()
            return

        def on_auth(ok: bool, err: str) -> None:
            if not ok:
                _log.info("auth recusada no tray click: %s", err)
                # Mantem tray rodando; nao mostra janela
                return
            self._authed = True
            callback()

        check_auth_async(on_auth)

    # ============================================================
    # Lifecycle
    # ============================================================

    def do_activate(self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        settings = load_settings()

        # Aplica tema escolhido (sistema/light/dark)
        apply_theme(normalize_mode(settings.theme))

        # Determina se vai iniciar minimizado (sem janela visivel)
        will_start_minimized = (
            self._start_minimized and settings.show_tray
        )

        # Tray + hold (se habilitado) — antes do auth pra ja' estar
        # spawnado caso o user CANCELE o prompt de senha (cenario nao
        # minimizado)
        if settings.show_tray:
            self._enable_tray()

        # Lock por senha — politicas:
        # 1. NAO vai iniciar minimizado (janela vai aparecer): pede agora
        #    (sync OK porque janela ainda nao apresentada)
        # 2. VAI iniciar minimizado: pula. Auth acontecera quando user
        #    clicar 'Abrir Hub' no tray (via _auth_then -> check_auth_async)
        if (
            settings.password_lock
            and not self._authed
            and not will_start_minimized
        ):
            ok, err = check_auth()
            if not ok:
                _log.warning("Autenticacao falhou no startup: %s", err)
                # Se tray ON, mantem o tray rodando — user pode tentar
                # de novo clicando em 'Abrir Hub'. Janela nao aparece.
                if not settings.show_tray:
                    self.quit()
                return
            self._authed = True

        # Garantir window object existe (pra Gio actions terem alvo)
        win = self._ensure_window()

        if will_start_minimized:
            # Nao apresenta janela. Auth virá no tray click.
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
