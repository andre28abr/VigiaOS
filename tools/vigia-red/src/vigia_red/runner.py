"""Execução cancelável de comandos externos — compartilhada pelos módulos do Red.

Roda um CLI longo (nmap, nuclei) e permite cancelá-lo (`cancel()` encerra o
processo). Convenção do projeto: argv em LISTA, nunca shell.
"""

from __future__ import annotations

import subprocess
import threading

from vigia_common import proc as _proc


class ScanProcess:
    """Roda um comando de forma cancelável. `cancel()` encerra o processo.

    Em modo admin (argv começa com `pkexec`) o processo roda como root e o
    SIGTERM direto dá EPERM; `cancel()` então pede `pkexec kill` (diálogo
    polkit) numa thread própria — nunca bloqueia a thread da GUI.
    """

    def __init__(self) -> None:
        self._proc = None
        self.cancelled = False
        self.cancel_failed = False

    def run(self, cmd: list[str], timeout: int = 600):
        if self.cancelled:
            return 1, "", ""
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors="replace")
        except (OSError, ValueError):
            return 1, "", ""
        if self.cancelled:  # cancel() chegou entre a checagem e o Popen
            self._terminate()
            return 1, "", ""
        try:
            out, err = self._proc.communicate(timeout=timeout)
            return (self._proc.returncode or 0), out, err
        except subprocess.TimeoutExpired:
            self._terminate()
            return 1, "", "tempo esgotado"
        except Exception:  # pylint: disable=broad-except
            return 1, "", ""

    def cancel(self) -> None:
        self.cancelled = True
        # Fora da thread da GUI: o wait/kill (e um eventual diálogo polkit)
        # não podem congelar a janela.
        threading.Thread(target=self._terminate, daemon=True).start()

    def _terminate(self) -> None:
        p = self._proc
        if p is None:
            return
        if not _proc.terminate(p):
            self.cancel_failed = True
