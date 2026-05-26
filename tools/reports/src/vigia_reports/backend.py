"""Coletores de dados para os relatorios.

Estrategia:
- Parsers puros (`_parse_*`) trabalham sobre dados ja coletados (list[dict] do
  journal JSON, ou texto bruto). Nao chamam subprocess.
- Coletores nao-elevados chamam journalctl/last/lastb diretamente, um por vez.
- Coletor elevado (`collect_all_elevated`) consolida TODOS os comandos numa
  unica chamada `pkexec bash -c '<script>'`, dividindo a saida por marcadores.
  Isso reduz de N dialogs polkit para 1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


# LGPD CRITICAL: reports tem PII (IPs, usernames, comandos sudo, lastb).
# NAO usar ~/Documents (sync cloud Dropbox/OneDrive/iCloud por default).
# Usar XDG_DATA_HOME (~/.local/share/) que e' padrao Linux para dados
# de app, fora de pastas sync por default.
REPORTS_DIR = Path.home() / ".local" / "share" / "vigia-reports"

# Path legacy — usado apenas para migracao automatica
_LEGACY_REPORTS_DIR = Path.home() / "Documents" / "VigiaReports"


@dataclass
class Period:
    since: datetime
    until: datetime

    @property
    def label(self) -> str:
        delta = self.until - self.since
        days = max(1, int(delta.total_seconds() / 86400))
        if days == 1:
            return "ultimas 24 horas"
        return f"ultimos {days} dias"

    def journalctl_since(self) -> str:
        return self.since.strftime("%Y-%m-%d %H:%M:%S")

    def journalctl_until(self) -> str:
        return self.until.strftime("%Y-%m-%d %H:%M:%S")


def make_period(days: int) -> Period:
    until = datetime.now()
    since = until - timedelta(days=days)
    return Period(since=since, until=until)


def ensure_reports_dir() -> Path:
    """Garante ~/.local/share/vigia-reports/ com mode 0700.

    LGPD: applies chmod imediatamente (defense-in-depth — outras chamadas
    de mkdir podem nao aplicar). Migra de ~/Documents/VigiaReports/ se
    existir.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(REPORTS_DIR, 0o700)
    except OSError:
        pass

    # Migracao one-shot: move arquivos de ~/Documents/VigiaReports/
    # se existir. Isto so roda uma vez (apos move, _LEGACY nao existe).
    if _LEGACY_REPORTS_DIR.is_dir():
        try:
            for f in _LEGACY_REPORTS_DIR.iterdir():
                if f.is_file():
                    target = REPORTS_DIR / f.name
                    if not target.exists():
                        try:
                            f.rename(target)
                            os.chmod(target, 0o600)
                        except OSError:
                            pass
            # Remove dir legacy se vazio
            try:
                _LEGACY_REPORTS_DIR.rmdir()
            except OSError:
                pass
        except OSError:
            pass

    return REPORTS_DIR


# ============================================================
# Helpers basicos
# ============================================================


def _run(cmd: list[str], timeout: int = 30) -> str:
    """Roda comando e retorna stdout. String vazia se falhar."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _parse_json_lines(text: str) -> list[dict]:
    """Cada linha do texto e' um JSON; ignora linhas vazias/invalidas."""
    out: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _parse_journal_ts(raw: str) -> str:
    """journalctl JSON usa epoch em microsegundos. Converte para ISO."""
    if not raw:
        return ""
    try:
        ts = int(raw) / 1_000_000
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return raw


def _extract_user_ip(msg: str, prefix: str) -> tuple[str, str]:
    """De 'Accepted password for andre from 192.0.2.42 port 22 ssh2', extrai (andre, IP)."""
    m = re.search(
        rf"{prefix}\s+(?:password|publickey)?\s*for\s+(?:invalid user )?(\S+)\s+from\s+(\S+)",
        msg,
    )
    if m:
        return m.group(1), m.group(2)
    return "?", "?"


# ============================================================
# Parsers puros (trabalham sobre raw data, sem subprocess)
# ============================================================


def _parse_ssh_journal(raw: list[dict]) -> list[dict]:
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = _parse_journal_ts(e.get("__REALTIME_TIMESTAMP", ""))
        if "Accepted" in msg:
            user, ip = _extract_user_ip(msg, "Accepted")
            events.append({"timestamp": ts, "type": "ssh_accept", "user": user, "ip": ip, "raw": msg})
        elif "Failed password" in msg:
            user, ip = _extract_user_ip(msg, "Failed password")
            events.append({"timestamp": ts, "type": "ssh_fail", "user": user, "ip": ip, "raw": msg})
    return events


def _parse_sudo_journal(raw: list[dict]) -> list[dict]:
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = _parse_journal_ts(e.get("__REALTIME_TIMESTAMP", ""))
        m = re.match(
            r"\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(\S+)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.+?)\s*$",
            msg,
        )
        if m:
            events.append({
                "timestamp": ts,
                "type": "sudo",
                "user": m.group(1),
                "tty": m.group(2),
                "pwd": m.group(3),
                "target_user": m.group(4),
                "command": m.group(5),
                "raw": msg,
            })
    return events


def _parse_fail2ban_journal(raw: list[dict]) -> list[dict]:
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = _parse_journal_ts(e.get("__REALTIME_TIMESTAMP", ""))
        m = re.search(r"\[(\S+)\]\s+Ban\s+(\S+)", msg)
        if m:
            events.append({"timestamp": ts, "type": "ban", "jail": m.group(1), "ip": m.group(2), "raw": msg})
            continue
        m = re.search(r"\[(\S+)\]\s+Unban\s+(\S+)", msg)
        if m:
            events.append({"timestamp": ts, "type": "unban", "jail": m.group(1), "ip": m.group(2), "raw": msg})
    return events


def _parse_pkexec_journal(raw: list[dict]) -> list[dict]:
    """pkexec do Fedora loga assim (em uma linha):

      andre: Executing command [USER=root] [TTY=unknown] [CWD=/home/andre]
      [COMMAND=/usr/sbin/setenforce 1]

    A v0.1 pegava o primeiro [...] (USER=root). Agora extrai o COMMAND=.
    """
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = _parse_journal_ts(e.get("__REALTIME_TIMESTAMP", ""))
        if "Executing command" not in msg:
            continue

        # Usuario antes do ":"
        user_match = re.match(r"\s*(\S+?):\s*Executing command", msg)
        user = user_match.group(1) if user_match else "?"

        # Pega [COMMAND=...] (que e' o ultimo bracket)
        cmd_match = re.search(r"\[COMMAND=(.+?)\](?!.*\[COMMAND=)", msg)
        command = cmd_match.group(1) if cmd_match else ""

        # Pega [USER=...] como target_user
        target_match = re.search(r"\[USER=(\S+?)\]", msg)
        target_user = target_match.group(1) if target_match else "?"

        events.append({
            "timestamp": ts,
            "type": "pkexec",
            "user": user,
            "target_user": target_user,
            "command": command or msg,
            "raw": msg,
        })
    return events


def _parse_last_text(text: str) -> list[dict]:
    """`last -F` output → list[dict]."""
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("wtmp begins") or line.startswith("btmp begins"):
            continue
        parts = re.split(r"\s{2,}", line)
        if len(parts) < 3:
            parts = line.split(None, 4)
        if len(parts) >= 4:
            events.append({
                "user": parts[0],
                "tty": parts[1] if len(parts) > 1 else "",
                "from": parts[2] if len(parts) > 2 else "",
                "when": parts[3] if len(parts) > 3 else "",
                "raw": line,
            })
    return events


# ============================================================
# Coletores nao-elevados (1 subprocess por chamada, sem pkexec)
# ============================================================


def _journalctl_user(args: list[str], period: Period, timeout: int = 60) -> list[dict]:
    cmd = [
        "journalctl",
        "--since", period.journalctl_since(),
        "--until", period.journalctl_until(),
        "--output", "json",
        "--no-pager",
    ] + args
    return _parse_json_lines(_run(cmd, timeout=timeout))


def collect_ssh_events_user(period: Period) -> list[dict]:
    return _parse_ssh_journal(_journalctl_user(["_COMM=sshd"], period))


def collect_sudo_events_user(period: Period) -> list[dict]:
    return _parse_sudo_journal(_journalctl_user(["_COMM=sudo"], period))


def collect_fail2ban_events_user(period: Period) -> list[dict]:
    return _parse_fail2ban_journal(_journalctl_user(["SYSLOG_IDENTIFIER=fail2ban-server"], period))


def collect_pkexec_events_user(period: Period) -> list[dict]:
    return _parse_pkexec_journal(_journalctl_user(["_COMM=pkexec"], period))


def collect_last_user() -> list[dict]:
    return _parse_last_text(_run(["last", "-F", "-n", "50"], timeout=10))


# ============================================================
# Coletor elevado consolidado (UM pkexec → todos os dados)
# ============================================================


def collect_all_elevated(period: Period) -> dict[str, list[dict]] | None:
    """Roda UM `pkexec bash -c '<script>'` que executa todos os comandos
    necessarios, separados por marcadores. Retorna dict com as keys
    parseadas, ou None se autenticacao foi cancelada.
    """
    since = period.journalctl_since()
    until = period.journalctl_until()
    # UUID por execucao garante que o separador nao colide com conteudo
    # natural dos logs (improvavel mas plausivel com copy/paste de logs).
    sep = f"===VIGIA-{uuid.uuid4().hex}==="

    # `set +e` para nao parar no primeiro comando que falhar.
    # `2>/dev/null` em last/lastb porque podem nao ter arquivo.
    script = f"""set +e
journalctl --since "{since}" --until "{until}" --output json --no-pager _COMM=sshd
printf '\\n{sep}\\n'
journalctl --since "{since}" --until "{until}" --output json --no-pager _COMM=sudo
printf '\\n{sep}\\n'
journalctl --since "{since}" --until "{until}" --output json --no-pager SYSLOG_IDENTIFIER=fail2ban-server
printf '\\n{sep}\\n'
journalctl --since "{since}" --until "{until}" --output json --no-pager _COMM=pkexec
printf '\\n{sep}\\n'
last -F -n 50 2>/dev/null
printf '\\n{sep}\\n'
lastb -F -n 100 2>/dev/null
"""
    try:
        result = subprocess.run(
            ["pkexec", "bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    # pkexec retorna 126 quando user cancela polkit
    if result.returncode in (126, 127):
        return None

    sections = result.stdout.split(sep)
    if len(sections) < 6:
        # Algo deu errado — devolve None para o caller fazer fallback
        return None

    return {
        "ssh": _parse_ssh_journal(_parse_json_lines(sections[0])),
        "sudo": _parse_sudo_journal(_parse_json_lines(sections[1])),
        "fail2ban": _parse_fail2ban_journal(_parse_json_lines(sections[2])),
        "pkexec": _parse_pkexec_journal(_parse_json_lines(sections[3])),
        "last": _parse_last_text(sections[4]),
        "lastb": _parse_last_text(sections[5]),
    }


# ============================================================
# Agregadores por template
# ============================================================


def _gather(period: Period, elevated: bool) -> dict:
    """Coleta tudo (1 pkexec dialog se elevated, N subprocess se nao).

    Retorna dict com 6 keys: ssh, sudo, fail2ban, pkexec, last, lastb.
    """
    if elevated:
        batch = collect_all_elevated(period)
        if batch is not None:
            return batch
        # Fallback para non-elevated se pkexec falhar / usuario cancelar
    return {
        "ssh": collect_ssh_events_user(period),
        "sudo": collect_sudo_events_user(period),
        "fail2ban": collect_fail2ban_events_user(period),
        "pkexec": collect_pkexec_events_user(period),
        "last": collect_last_user(),
        "lastb": [],  # lastb sem root nao retorna dados confiaveis
    }


def collect_for_activity_overview(period: Period, elevated: bool = False) -> dict:
    """Dados para template activity_overview."""
    raw = _gather(period, elevated)

    ssh_success = [e for e in raw["ssh"] if e["type"] == "ssh_accept"]
    ssh_failed = [e for e in raw["ssh"] if e["type"] == "ssh_fail"]
    bans_only = [e for e in raw["fail2ban"] if e["type"] == "ban"]

    ip_counts: dict[str, int] = {}
    for b in bans_only:
        ip_counts[b.get("ip", "?")] = ip_counts.get(b.get("ip", "?"), 0) + 1
    top_banned = sorted(ip_counts.items(), key=lambda kv: -kv[1])[:10]

    sudo_user_counts: dict[str, int] = {}
    for s in raw["sudo"]:
        sudo_user_counts[s.get("user", "?")] = sudo_user_counts.get(s.get("user", "?"), 0) + 1
    top_sudo_users = sorted(sudo_user_counts.items(), key=lambda kv: -kv[1])[:10]

    return {
        "period": period,
        "elevated_mode": elevated,
        "kpis": {
            "ssh_success": len(ssh_success),
            "ssh_failed": len(ssh_failed),
            "sudo_invocations": len(raw["sudo"]),
            "pkexec_invocations": len(raw["pkexec"]),
            "bans": len(bans_only),
            "logins": len(raw["last"]),
        },
        "ssh_success": ssh_success[:50],
        "ssh_failed": ssh_failed[:50],
        "sudo": raw["sudo"][:50],
        "bans": bans_only[:50],
        "top_banned_ips": top_banned,
        "top_sudo_users": top_sudo_users,
        "pkexec": raw["pkexec"][:50],
        "logins": raw["last"][:30],
    }


def collect_for_auth_events(period: Period, elevated: bool = False) -> dict:
    """Dados para template auth_events."""
    raw = _gather(period, elevated)
    return {
        "period": period,
        "elevated_mode": elevated,
        "ssh_success": [e for e in raw["ssh"] if e["type"] == "ssh_accept"],
        "ssh_failed": [e for e in raw["ssh"] if e["type"] == "ssh_fail"],
        "sudo": raw["sudo"],
        "pkexec": raw["pkexec"],
        "logins": raw["last"],
        "failed_logins": raw["lastb"],
    }
