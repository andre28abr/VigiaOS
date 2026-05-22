"""Parser para output do `ss` (socket statistics).

Estrategia: roda `ss -tunap` (TCP+UDP, sem DNS resolution para velocidade,
all states, com process info). Sem root, process info aparece vazia para
sockets de outros usuarios; com sudo aparece para todos.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class NetConnection:
    proto: str       # 'tcp', 'udp', 'tcp6', 'udp6'
    state: str       # 'ESTAB', 'LISTEN', 'TIME-WAIT', 'UNCONN', etc.
    local_addr: str  # ex: '192.168.1.5:43210'
    peer_addr: str   # ex: '142.250.78.46:443' ou '0.0.0.0:*'
    process: str     # nome do binario (ex: 'firefox') ou '?'
    pid: str         # PID ou '?'
    raw: str         # linha original do ss

    @property
    def is_listening(self) -> bool:
        return self.state == "LISTEN" or self.peer_addr.endswith(":*")

    @property
    def is_established(self) -> bool:
        return self.state == "ESTAB"


def list_connections(elevated: bool = False) -> list[NetConnection]:
    """Roda `ss -tunap` e devolve lista de conexoes.

    elevated=True roda via pkexec (mostra process info de TODOS os sockets,
    incluindo system services). Dispara dialogo polkit pedindo senha admin
    a cada chamada — chame com parsimonia.
    """
    if shutil.which("ss") is None:
        return []
    if elevated:
        if shutil.which("pkexec") is None:
            return []
        cmd = ["pkexec", "ss", "-tunap"]
        timeout = 60  # mais espaco para o dialogo polkit
    else:
        cmd = ["ss", "-tunap"]
        timeout = 10
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []

    return _parse_ss_output(result.stdout)


def _parse_ss_output(output: str) -> list[NetConnection]:
    """Parser do `ss -tunap`.

    Formato (colunas separadas por whitespace, com process info no final):
        Netid State    Recv-Q Send-Q Local Address:Port    Peer Address:Port  Process
        udp   UNCONN   0      0      127.0.0.54:53         0.0.0.0:*          users:(("systemd-resolve",pid=804,...))
        tcp   ESTAB    0      0      192.168.1.5:43210     142.250.78.46:443
    """
    conns: list[NetConnection] = []
    process_re = re.compile(r'\("([^"]+)",pid=(\d+)')

    for line in output.splitlines():
        line = line.rstrip()
        if not line or line.startswith("Netid"):
            continue
        # Limita splits para preservar process info (que tem virgulas/parens)
        parts = line.split(None, 6)
        if len(parts) < 6:
            continue
        netid, state, _recv, _send, local, peer = parts[:6]
        process_info = parts[6] if len(parts) > 6 else ""

        m = process_re.search(process_info)
        if m:
            process_name, pid = m.group(1), m.group(2)
        else:
            process_name, pid = "?", "?"

        conns.append(NetConnection(
            proto=netid,
            state=state,
            local_addr=local,
            peer_addr=peer,
            process=process_name,
            pid=pid,
            raw=line,
        ))
    return conns


# ============================================================================
# Convenience filters
# ============================================================================

def list_listening(elevated: bool = False) -> list[NetConnection]:
    """So sockets em LISTEN ou UNCONN com peer wildcard (servidores ativos)."""
    return [c for c in list_connections(elevated=elevated) if c.is_listening]


def list_established(elevated: bool = False) -> list[NetConnection]:
    """So conexoes ESTAB (TCP estabelecidas)."""
    return [c for c in list_connections(elevated=elevated) if c.is_established]


def is_ss_available() -> bool:
    return shutil.which("ss") is not None
