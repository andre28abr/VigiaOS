"""Monitor de inatividade pra auto-lock do Hub.

Detecta inatividade do USER NO HUB (nao do sistema inteiro) usando o
event controller do GTK4 + timeout periodico. Quando o usuario fica
N minutos sem interagir com a janela do Hub, dispara callback.

Casos de uso:
- Auto-lock: esconde janela + forca reauth na proxima abertura
- (Futuro) Auto-cleanup de tabs sensiveis

Configuracao: settings.auto_lock_minutes (0 = desabilitado).

IMPORTANTE: monitora apenas eventos NA janela do Hub. Se user esta
usando outra app, ainda conta como inatividade do Hub — o que e' o
desejado pra LGPD (usuario nao olhou pro Hub por X min).
"""

from __future__ import annotations

import time
from typing import Callable, Optional


CHECK_INTERVAL_SEC = 30  # com que frequencia verifica idle


class IdleMonitor:
    """Reseta timer a cada evento na janela; dispara callback quando expira.

    Usage:
        mon = IdleMonitor(window, timeout_minutes=10, on_idle=lambda: ...)
        mon.start()
        ...
        mon.stop()  # quando trocar config ou destruir
    """

    def __init__(
        self,
        window,
        timeout_minutes: int,
        on_idle: Callable[[], None],
    ) -> None:
        self._window = window
        self._timeout_sec = max(60, timeout_minutes * 60)  # min 1 min
        self._on_idle = on_idle
        self._last_activity = time.monotonic()
        self._tick_source_id: Optional[int] = None
        self._motion_controller = None
        self._key_controller = None
        self._triggered = False

    def start(self) -> None:
        """Comeca monitorar. Idempotente."""
        if self._tick_source_id is not None:
            return

        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk, GLib
        except (ValueError, ImportError):
            return

        # Reset timer em mouse motion
        self._motion_controller = Gtk.EventControllerMotion()
        self._motion_controller.connect("motion", self._on_activity)
        self._window.add_controller(self._motion_controller)

        # Reset timer em tecla
        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-pressed", self._on_activity_key)
        self._window.add_controller(self._key_controller)

        # Tick periodico verificando timeout
        self._tick_source_id = GLib.timeout_add_seconds(
            CHECK_INTERVAL_SEC, self._on_tick
        )
        self._last_activity = time.monotonic()
        self._triggered = False

    def stop(self) -> None:
        """Para monitor. Idempotente."""
        if self._tick_source_id is not None:
            try:
                from gi.repository import GLib
                GLib.source_remove(self._tick_source_id)
            except (ValueError, ImportError):
                pass
            self._tick_source_id = None

        # Remove controllers do widget
        if self._motion_controller and self._window:
            try:
                self._window.remove_controller(self._motion_controller)
            except Exception:  # pylint: disable=broad-except
                pass
            self._motion_controller = None
        if self._key_controller and self._window:
            try:
                self._window.remove_controller(self._key_controller)
            except Exception:  # pylint: disable=broad-except
                pass
            self._key_controller = None

    def reset(self) -> None:
        """Reseta o timer manualmente (ex: apos auth)."""
        self._last_activity = time.monotonic()
        self._triggered = False

    # ============================================================
    # Internals
    # ============================================================

    def _on_activity(self, *_args) -> None:
        self._last_activity = time.monotonic()
        self._triggered = False

    def _on_activity_key(self, *_args) -> bool:
        self._last_activity = time.monotonic()
        self._triggered = False
        return False  # nao consume o evento

    def _on_tick(self) -> bool:
        if self._triggered:
            return True  # ja' disparou, mantem timeout vivo mas nao re-dispara
        elapsed = time.monotonic() - self._last_activity
        if elapsed >= self._timeout_sec:
            self._triggered = True
            try:
                self._on_idle()
            except Exception as e:  # pylint: disable=broad-except
                import logging
                logging.getLogger(__name__).warning(
                    "callback idle crashou: %s", e
                )
        return True  # continua timeout
