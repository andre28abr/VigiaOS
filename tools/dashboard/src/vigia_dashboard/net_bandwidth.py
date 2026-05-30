"""Banda de rede por processo via `nethogs` (snapshot pontual).

Roda `pkexec env LC_ALL=C nethogs -t -c N -d 1` por alguns segundos e
parseia o tracemode (uma linha por processo: caminho/pid/uid, KB/s
enviado, KB/s recebido). Snapshot one-shot — nao mantem root aberto.

Por que pkexec: nethogs usa libpcap (CAP_NET_RAW + mapear socket->pid),
exige root. Ver banda por processo e' sensivel (exfiltracao/LGPD) —
escalonamento explicito via polkit e' o certo. Read-only: so' observa.

Por que LC_ALL=C: nethogs formata os numeros conforme o locale; em pt-BR
sairiam com virgula decimal e o float() quebraria (mesma licao do
inspetor strace). pkexec sanitiza o env, entao o LC_ALL=C vai como
argumento do `env`.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class ProcBandwidth:
    program: str           # programa, ou endpoint remoto se nao-atribuido
    pid: int               # 0 = nethogs nao mapeou pra um processo
    sent_kbps: float       # KB/s enviado
    recv_kbps: float       # KB/s recebido
    attributed: bool = True


@dataclass
class BandwidthResult:
    rows: list[ProcBandwidth] = field(default_factory=list)
    error: str = ""


def nethogs_installed() -> bool:
    return shutil.which("nethogs") is not None


def _unattributed_label(head: str) -> str:
    """Trafego sem processo (pid 0): mostra o endpoint REMOTO da conexao
    (`local:porta-remoto:porta`) — ainda util pra exfiltracao (voce ve
    pra onde vai). Sem '-' (ex: 'unknown TCP') -> 'desconhecido'."""
    if "-" in head:
        return head.rsplit("-", 1)[-1].strip() or head
    return "desconhecido"


def parse_nethogs_trace(text: str) -> list[ProcBandwidth]:
    """Parseia a saida do `nethogs -t` (tracemode).

    Cada linha de dado: ``<campo>/<pid>/<uid>\\t<enviado>\\t<recebido>``
    (KB/s). O ``<campo>`` e' o CAMINHO do programa quando o nethogs
    atribui a conexao a um processo (ex: `/usr/lib/firefox/firefox`), OU
    a propria CONEXAO (`local:porta-remoto:porta`) com pid 0 quando NAO
    consegue (conexao pre-existente, kernel, etc.).

    - pid > 0  -> atribuido: programa = basename do caminho.
    - pid == 0 -> nao-atribuido: mostra o endpoint remoto.
    Linhas sem trafego (0/0) sao ignoradas. Dedup por (rotulo, pid)
    mantendo a ultima refresh; ordena por total (enviado+recebido) desc.
    """
    by_key: dict[tuple[str, int], ProcBandwidth] = {}
    for line in text.splitlines():
        if "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        name_field = parts[0].strip()
        sent_s, recv_s = parts[-2].strip(), parts[-1].strip()
        bits = name_field.rsplit("/", 2)
        if len(bits) != 3:
            continue
        head, pid_s, _uid_s = bits
        try:
            pid = int(pid_s)
            # LC_ALL=C ja' forca ponto, mas tolera virgula por seguranca
            sent = float(sent_s.replace(",", "."))
            recv = float(recv_s.replace(",", "."))
        except ValueError:
            continue
        if sent == 0.0 and recv == 0.0:
            continue  # sem trafego no periodo (ruido)
        if pid > 0:
            program = head.rsplit("/", 1)[-1] or head
            attributed = True
        else:
            program = _unattributed_label(head)
            attributed = False
        by_key[(program, pid)] = ProcBandwidth(
            program, pid, sent, recv, attributed
        )
    return sorted(
        by_key.values(),
        key=lambda r: r.sent_kbps + r.recv_kbps,
        reverse=True,
    )


def bandwidth_snapshot_blocking(
    samples: int = 4, delay: int = 1
) -> BandwidthResult:
    """Mede banda por processo por ~samples*delay segundos (bloqueante).

    Rode em worker thread. Read-only (nethogs so' observa o trafego).
    """
    res = BandwidthResult()
    if not nethogs_installed():
        res.error = (
            "nethogs não instalado. Instale pelo Vigia Instalador "
            "(categoria Monitoramento) pra medir banda por processo."
        )
        return res

    cmd = [
        "pkexec", "env", "LC_ALL=C",
        "nethogs", "-t", "-c", str(samples), "-d", str(delay),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=samples * delay + 60
        )
    except subprocess.TimeoutExpired:
        res.error = "Medição excedeu o tempo limite."
        return res
    except (FileNotFoundError, OSError):
        res.error = "pkexec ou nethogs não encontrado."
        return res

    if proc.returncode in (126, 127):
        res.error = "Autenticação cancelada."
        return res

    rows = parse_nethogs_trace(proc.stdout)
    if not rows:
        res.error = (
            "Sem tráfego por processo no período. Pode não ter havido "
            "atividade de rede, ou o nethogs não conseguiu capturar."
        )
        return res

    res.rows = rows
    return res
