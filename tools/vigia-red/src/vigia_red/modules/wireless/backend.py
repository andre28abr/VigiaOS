"""Backend do Vigia Wireless — auditoria da senha da SUA rede Wi-Fi.

Objetivo DEFENSIVO/educacional: descobrir se a senha do SEU ponto de acesso é
fraca o suficiente para cair num ataque de dicionário. A pergunta que ele
responde é "a senha do meu Wi-Fi aguenta um atacante?", não "como entrar no
Wi-Fi dos outros" — acesso não autorizado a rede alheia é crime (Lei 12.737/2012).

O fluxo de auditoria tem dois passos:

1. **Capturar o handshake** da sua rede (um aperto de mão de 4 vias que acontece
   quando um dispositivo conecta). Isso exige placa em modo monitor e root; é
   feito fora do app, com `airodump-ng`, e este backend só MONTA os comandos e o
   manual explica o passo a passo. Nada de rede alheia.
2. **Testar o handshake** contra uma wordlist com `aircrack-ng`: se a senha
   estiver na lista, ela é fraca. Esse é o passo que o app roda (só precisa do
   arquivo `.cap` e de uma wordlist — não toca em nenhuma rede).

Partes PURAS (testáveis sem aircrack-ng, sem GTK):
- `list_wifi_interfaces` — lê `/sys/class/net` (informativo).
- `validate_bssid` / `validate_interface` / `validate_channel` / `validate_capture`.
- `build_airodump_cmd` / `build_aireplay_deauth_cmd` — montam o passo de captura.
- `build_aircrack_cmd` — monta o teste do handshake.
- `parse_aircrack_output` — saída → (achou?, senha).

Parte que toca o sistema:
- `run_audit(...)` — roda o aircrack-ng (cancelável) sobre um `.cap` + relatório 0600.
"""

from __future__ import annotations

import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

from ...runner import ScanProcess

DATA_DIR = Path.home() / ".local" / "share" / "vigia-wireless"
REPORTS_DIR = DATA_DIR

_CAPTURE_EXTS = (".cap", ".pcap", ".pcapng")


# ============================================================
# Disponibilidade
# ============================================================


def aircrack_available() -> bool:
    return shutil.which("aircrack-ng") is not None


def airodump_available() -> bool:
    return shutil.which("airodump-ng") is not None


def list_wifi_interfaces() -> list[str]:
    """Interfaces de rede sem fio (lê /sys/class/net/<if>/wireless). Nunca levanta."""
    out: list[str] = []
    base = Path("/sys/class/net")
    try:
        for iface in sorted(base.iterdir()):
            if (iface / "wireless").exists() or (iface / "phy80211").exists():
                out.append(iface.name)
    except OSError:
        pass
    return out


# ============================================================
# Validação (puro)
# ============================================================

_BSSID_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_IFACE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")


def validate_bssid(bssid: str) -> bool:
    return bool(_BSSID_RE.match((bssid or "").strip()))


def validate_interface(iface: str) -> bool:
    return bool(_IFACE_RE.match((iface or "").strip()))


def validate_channel(channel: str) -> bool:
    ch = (channel or "").strip()
    if not ch.isdigit():
        return False
    return 1 <= int(ch) <= 196


def validate_capture(path: str) -> bool:
    p = (path or "").strip()
    if not p:
        return False
    try:
        pp = Path(p).expanduser()
        return pp.is_file() and pp.suffix.lower() in _CAPTURE_EXTS
    except OSError:
        return False


# ============================================================
# Montadores do passo de CAPTURA (puro) — documentados no manual;
# rodam fora do app (exigem modo monitor + root).
# ============================================================


def build_airodump_cmd(iface: str, bssid: str, channel: str,
                       out_prefix: str) -> list[str]:
    """argv do airodump-ng para capturar o handshake da SUA rede.

    `--bssid` e `--channel` travam a captura no SEU ponto de acesso (não varre o
    espectro inteiro). `-w` grava o `.cap`.
    """
    return ["airodump-ng", "--bssid", bssid, "--channel", channel,
            "-w", out_prefix, iface]


def build_aireplay_deauth_cmd(iface: str, bssid: str, count: str = "3") -> list[str]:
    """argv do aireplay-ng para forçar um cliente da SUA rede a reconectar
    (gera o handshake mais rápido). Use SÓ na sua rede — derruba conexões."""
    return ["aireplay-ng", "--deauth", count, "-a", bssid, iface]


# ============================================================
# Montador do TESTE (puro) — o passo que o app roda
# ============================================================


def build_aircrack_cmd(capture: str, wordlist: str,
                       bssid: str = "") -> list[str]:
    """argv do aircrack-ng: testa o handshake do `.cap` contra a wordlist."""
    cmd = ["aircrack-ng", "-w", wordlist]
    if bssid:
        cmd += ["-b", bssid]
    cmd.append(capture)
    return cmd


# ============================================================
# Parser (puro) — nunca levanta
# ============================================================

_KEY_RE = re.compile(r"KEY FOUND!\s*\[\s*(.*?)\s*\]")


def parse_aircrack_output(text: str) -> tuple[bool, str]:
    """(achou_a_senha, senha). `('', False)` quando não achou."""
    m = _KEY_RE.search(text or "")
    if m:
        return True, m.group(1)
    return False, ""


def capture_has_handshake(text: str) -> bool:
    """Heurística: a saída do aircrack indica que havia handshake no `.cap`?"""
    low = (text or "").lower()
    if "no valid wpa handshakes found" in low:
        return False
    if "got no data packets" in low or "no networks found" in low:
        return False
    return True


# ============================================================
# Resultado
# ============================================================


@dataclass
class AuditResult:
    capture: str
    bssid: str = ""
    wordlist: str = ""
    found: bool = False
    password: str = ""
    started_at: str = ""
    elapsed_sec: float = 0.0
    error: str = ""
    ran: bool = False
    raw: str = ""


# ============================================================
# Execução (toca o sistema) — só o teste do handshake
# ============================================================


def run_audit(
    capture: str,
    wordlist: str,
    *,
    bssid: str = "",
    timeout: int = 1800,
    handle: ScanProcess | None = None,
) -> AuditResult:
    """Testa o handshake do `.cap` contra a wordlist. Nunca levanta."""
    res = AuditResult(
        capture=capture, bssid=bssid.strip(), wordlist=wordlist,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    if not validate_capture(capture):
        res.error = ("Arquivo de captura inválido. Aponte um .cap/.pcap com o "
                     "handshake da sua rede.")
        return res
    if not (wordlist or "").strip() or not Path(wordlist).expanduser().is_file():
        res.error = "Wordlist inválida ou ilegível."
        return res
    if bssid and not validate_bssid(bssid):
        res.error = "BSSID inválido (formato AA:BB:CC:DD:EE:FF)."
        return res
    if not aircrack_available():
        res.error = "aircrack-ng não está instalado."
        return res

    runner = handle.run if handle is not None else proc.run
    t0 = time.monotonic()
    rc, out, err = runner(
        build_aircrack_cmd(capture, wordlist, bssid), timeout=timeout)
    res.elapsed_sec = round(time.monotonic() - t0, 2)
    res.raw = out

    if not capture_has_handshake(out + "\n" + err):
        res.error = ("A captura não tem um handshake WPA válido. Refaça a "
                     "captura (veja a aba Sobre) esperando um dispositivo "
                     "conectar à sua rede.")
        save_report(res)
        return res

    res.ran = True
    res.found, res.password = parse_aircrack_output(out)

    save_report(res)
    try:
        from vigia_common import events
        sev = "high" if res.found else "ok"
        title = ("Senha do Wi-Fi FRACA (caiu no dicionário)" if res.found
                 else "Senha do Wi-Fi resistiu ao dicionário")
        events.record("wireless", title, category="scan", severity=sev,
                      ref=res.bssid or Path(capture).name,
                      payload={"found": res.found})
    except Exception:  # pylint: disable=broad-except
        pass
    return res


# ============================================================
# Relatórios (JSON 0600 + histórico + export TXT)
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def result_to_dict(r: AuditResult) -> dict:
    return {
        "capture": r.capture,
        "bssid": r.bssid,
        "wordlist": r.wordlist,
        "started_at": r.started_at,
        "elapsed_sec": r.elapsed_sec,
        "error": r.error,
        "found": r.found,
        # A senha em claro NÃO é salva no histórico (minimização/LGPD): o fato
        # de ser fraca já é o achado; a senha aparece só na tela e no export TXT.
    }


def result_to_text(r: AuditResult) -> str:
    lines = [
        f"Vigia Wireless — auditoria de {Path(r.capture).name}",
        f"BSSID: {r.bssid or '(não informado)'} · {r.started_at} · "
        f"{r.elapsed_sec:.0f}s",
        "=" * 56,
    ]
    if r.error:
        lines.append(f"Erro: {r.error}")
        return "\n".join(lines) + "\n"
    if r.found:
        lines.append("RESULTADO: senha FRACA — caiu no dicionário testado.")
        lines.append(f"Senha encontrada: {r.password}")
        lines.append("\nTroque a senha do seu Wi-Fi por uma frase longa e única.")
    else:
        lines.append("RESULTADO: a senha NÃO caiu no dicionário testado.")
        lines.append("Bom sinal — mas não prova que seja inquebrável.")
    return "\n".join(lines) + "\n"


def save_report(result: AuditResult) -> Path | None:
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"wireless-{safe_ts}.json"
    return path if save_json_0600(path, result_to_dict(result)) else None


def _mtime_or_zero(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def list_recent_reports(limit: int = 20) -> list[dict]:
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(REPORTS_DIR.glob("wireless-*.json"),
                   key=_mtime_or_zero, reverse=True)
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
