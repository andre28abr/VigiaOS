"""Inspecao de processo via `strace -c` (resumo de syscalls).

Roda `pkexec timeout -s INT <dur> strace -f -c -p <pid>` por alguns
segundos e parseia o resumo que o `strace -c` imprime no **stderr** ao
detachar (no SIGINT enviado pelo timeout). E' **read-only** — apenas
observa as chamadas de sistema, nao altera o processo.

Por que pkexec: anexar (ptrace) a um processo que nao e' filho do
chamador exige root na maioria das configs (yama ptrace_scope=1). Ler
syscalls de outro processo e' sensivel (LGPD) — escalonamento explicito
via polkit e' o certo.

NOTA: o modulo nao se chama `inspect.py` de proposito — colidiria com o
modulo `inspect` da stdlib.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class SyscallRow:
    syscall: str
    calls: int
    errors: int
    time_pct: float


@dataclass
class InspectResult:
    pid: int
    rows: list[SyscallRow] = field(default_factory=list)
    total_calls: int = 0
    error: str = ""


def strace_installed() -> bool:
    return shutil.which("strace") is not None


def parse_strace_summary(text: str) -> tuple[list[SyscallRow], int]:
    """Parseia o resumo do `strace -c`.

    Formato (stderr):

        % time     seconds  usecs/call     calls    errors syscall
        ------ ----------- ----------- --------- --------- ----------------
         45.00    0.001234          12       100         2 read
         30.00    0.000800          10        80           write
        ------ ----------- ----------- --------- --------- ----------------
        100.00    0.002740                   500         5 total

    Robusto a versoes: ignora cabecalho, separadores e a linha 'total'
    (o total e' recalculado somando as rows). Ordena por %time desc.
    """
    rows: list[SyscallRow] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        if parts[-1] in ("syscall", "total"):  # cabecalho / total
            continue
        try:
            time_pct = float(parts[0])
            calls = int(parts[3])
        except (ValueError, IndexError):
            continue  # separador "----", linha de ruido do pkexec, etc.
        errors = 0
        if len(parts) >= 6:
            try:
                errors = int(parts[4])
            except ValueError:
                errors = 0
        rows.append(SyscallRow(parts[-1], calls, errors, time_pct))
    rows.sort(key=lambda r: r.time_pct, reverse=True)
    return rows, sum(r.calls for r in rows)


def inspect_process_blocking(pid: int, duration: int = 5) -> InspectResult:
    """Anexa ao `pid` por `duration`s e retorna o resumo de syscalls.

    Bloqueante — rode em worker thread. Nao modifica o processo.
    """
    res = InspectResult(pid=pid)
    if not strace_installed():
        res.error = "strace nao instalado. Instale pelo Vigia Instalador (categoria Monitoramento)."
        return res

    # timeout -s INT: apos `duration`s manda SIGINT pro strace, que entao
    # detacha do processo e imprime o resumo -c. (SIGTERM nao imprime.)
    cmd = [
        "pkexec", "timeout", "-s", "INT", str(duration),
        "strace", "-f", "-c", "-p", str(pid),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=duration + 60
        )
    except subprocess.TimeoutExpired:
        res.error = "Inspecao excedeu o tempo limite."
        return res
    except (FileNotFoundError, OSError):
        res.error = "pkexec, timeout ou strace nao encontrado."
        return res

    if proc.returncode in (126, 127):
        res.error = "Autenticacao cancelada."
        return res

    rows, total = parse_strace_summary(proc.stderr)
    if not rows:
        tail = (proc.stderr or "").strip().splitlines()
        last = tail[-1] if tail else ""
        res.error = (
            "Sem dados de syscall. O processo pode ter terminado, nao fez "
            "syscalls no periodo, ou o strace nao conseguiu anexar."
            + (f"\n\n{last[:200]}" if last else "")
        )
        return res

    res.rows = rows
    res.total_calls = total
    return res
