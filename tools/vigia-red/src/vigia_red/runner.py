"""Execução cancelável de comandos externos — compartilhada pelos módulos do Red.

Roda um CLI longo (nmap, nuclei) e permite cancelá-lo (`cancel()` encerra o
processo). Convenção do projeto: argv em LISTA, nunca shell.
"""

from __future__ import annotations

import subprocess


class ScanProcess:
    """Roda um comando de forma cancelável. `cancel()` encerra o processo."""

    def __init__(self) -> None:
        self._proc = None
        self.cancelled = False

    def run(self, cmd: list[str], timeout: int = 600):
        if self.cancelled:
            return 1, "", ""
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except (OSError, ValueError):
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
        self._terminate()

    def _terminate(self) -> None:
        p = self._proc
        if p is None:
            return
        try:
            p.terminate()
            try:
                p.wait(timeout=3)
            except Exception:  # pylint: disable=broad-except
                p.kill()
        except Exception:  # pylint: disable=broad-except
            pass
