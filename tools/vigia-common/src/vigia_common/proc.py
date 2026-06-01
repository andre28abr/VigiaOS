"""Execução de subprocessos — wrapper único e seguro.

`run(cmd, timeout)` roda um comando capturando stdout/stderr e NUNCA levanta:
timeout ou binário ausente viram `(1, "", "")`. Centraliza o padrão idêntico
que estava duplicado em ~8 backends (antivirus, capabilities, deployments,
rootkit, dns, reports).

Convenção de segurança do projeto: `cmd` é SEMPRE uma lista de argumentos
(nunca string com `shell=True`) — sem superfície de injeção de shell.
"""

from __future__ import annotations

import subprocess


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Roda `cmd` (lista de args) e retorna `(returncode, stdout, stderr)`.

    Nunca levanta: qualquer `OSError` (binário ausente, permissão, etc.) ou
    `SubprocessError` (timeout) vira `(1, "", "")`.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""
