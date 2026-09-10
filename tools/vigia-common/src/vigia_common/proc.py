"""Execução de subprocessos — wrapper único e seguro.

`run(cmd, timeout)` roda um comando capturando stdout/stderr e NUNCA levanta:
timeout ou binário ausente viram `(1, "", "")`. Centraliza o padrão idêntico
que estava duplicado em ~7 backends (antivirus, capabilities, rootkit,
dns, reports).

Convenção de segurança do projeto: `cmd` é SEMPRE uma lista de argumentos
(nunca string com `shell=True`) — sem superfície de injeção de shell.
"""

from __future__ import annotations

import subprocess


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Roda `cmd` (lista de args) e retorna `(returncode, stdout, stderr)`.

    Nunca levanta: qualquer `OSError` (binário ausente, permissão, etc.),
    `SubprocessError` (timeout) ou `ValueError` (decodificação de saída
    inválida, argumento ruim) vira `(1, "", "")`.

    Saída é decodificada com `errors="replace"`: bytes fora do UTF-8 (nomes
    de arquivo Latin-1 vindos de Windows, por exemplo) viram U+FFFD em vez
    de derrubar a thread com `UnicodeDecodeError`.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, errors="replace",
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1, "", ""


def terminate(process, *, grace: float = 3.0) -> bool:
    """Encerra um `Popen` com SIGTERM (depois SIGKILL) e faz `wait()`.

    Se o processo foi lançado via `pkexec` ele roda como **root**: o sinal
    direto dá `EPERM` (e o `subprocess` deixaria o processo órfão rodando).
    Nesse caso pede o kill via `pkexec kill -TERM <pid>` — um diálogo polkit.
    Devolve True se conseguiu sinalizar o processo. Nunca levanta.
    """
    if process is None:
        return False
    try:
        process.terminate()
    except PermissionError:
        return _kill_elevated(process.pid)
    except OSError:
        return False
    try:
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=grace)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return True


def _kill_elevated(pid: int) -> bool:
    """`pkexec kill -TERM <pid>` — único jeito de parar um filho root."""
    try:
        r = subprocess.run(
            ["pkexec", "kill", "-TERM", str(pid)],
            capture_output=True, text=True, errors="replace", timeout=120,
        )
        return r.returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
