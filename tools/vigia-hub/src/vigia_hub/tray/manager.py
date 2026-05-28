"""Gerencia o subprocess do tray icon a partir do Hub (GTK4).

Lifecycle:
    manager = TrayManager()
    manager.start()  # spawna vigia-hub-tray (GTK3) em background
    ...
    manager.stop()   # SIGTERM no subprocess; aguarda 2s pra die clean
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from typing import Optional


class TrayManager:
    """Spawna/mata o subprocess do tray icon."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    # ============================================================
    # State
    # ============================================================

    def is_running(self) -> bool:
        """True se o subprocess do tray esta vivo."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    # ============================================================
    # Spawn / kill
    # ============================================================

    def start(self) -> tuple[bool, str]:
        """Spawna `vigia-hub-tray`. Retorna (sucesso, mensagem_erro)."""
        if self.is_running():
            return (True, "")

        cmd = self._resolve_command()
        if cmd is None:
            return (False, "Executavel 'vigia-hub-tray' nao encontrado no PATH.")

        try:
            # start_new_session=True: novo grupo de processos.
            # Se o Hub crashar, o tray fica orfao mas vivo (que e' o que
            # a gente quer? Nao — queremos que ele morra junto). Por
            # isso usamos preexec_fn pra PR_SET_PDEATHSIG (Linux only).
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=self._setup_child_death,
            )
            return (True, "")
        except (OSError, subprocess.SubprocessError) as e:
            self._proc = None
            return (False, f"Falha ao iniciar tray: {e}")

    def stop(self, timeout_sec: float = 2.0) -> None:
        """SIGTERM no subprocess. Espera ate timeout_sec; se nao morrer, SIGKILL."""
        if not self.is_running():
            self._proc = None
            return
        assert self._proc is not None
        try:
            self._proc.terminate()
            self._proc.wait(timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            try:
                self._proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass
        finally:
            self._proc = None

    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _resolve_command() -> Optional[list[str]]:
        """Encontra o comando do tray.

        Procura nessa ordem:
        1. `vigia-hub-tray` no PATH (instalado via pip)
        2. `python3 -m vigia_hub.tray.indicator` (modo dev)
        """
        exe = shutil.which("vigia-hub-tray")
        if exe:
            return [exe]
        # Fallback: rodar como modulo (modo dev / pip --user)
        return [sys.executable, "-m", "vigia_hub.tray.indicator"]

    @staticmethod
    def _setup_child_death() -> None:
        """Linux: faz o child receber SIGTERM se o pai (Hub) morrer.

        Usa prctl(PR_SET_PDEATHSIG, SIGTERM) via ctypes.
        Falha silenciosamente em sistemas nao-Linux.
        """
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            PR_SET_PDEATHSIG = 1
            libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
        except (OSError, AttributeError):
            pass
