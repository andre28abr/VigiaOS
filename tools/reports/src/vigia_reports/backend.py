"""Coletores de dados para os relatorios.

Usa subprocess para chamar `journalctl`, `last`, `lastb`, `ausearch`.
Modo admin (via pkexec) habilita coleta de dados restritos (audit.log,
journal do sistema).

Todos os coletores retornam list[dict] com chaves estaveis para templates.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


REPORTS_DIR = Path.home() / "Documents" / "VigiaReports"


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
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


# ============================================================
# Helpers
# ============================================================


def _run(cmd: list[str], timeout: int = 30) -> str:
    """Roda comando e retorna stdout. String vazia se falhar."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _journalctl(
    args: list[str],
    period: Period,
    elevated: bool = False,
    timeout: int = 60,
) -> list[dict]:
    """Roda journalctl com --output=json-pretty e parseia."""
    cmd: list[str] = []
    if elevated:
        cmd.append("pkexec")
    cmd.append("journalctl")
    cmd += [
        "--since", period.journalctl_since(),
        "--until", period.journalctl_until(),
        "--output", "json",
        "--no-pager",
    ]
    cmd += args

    out = _run(cmd, timeout=timeout)
    events: list[dict] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


# ============================================================
# Coletores de eventos
# ============================================================


def collect_ssh_events(period: Period, elevated: bool = False) -> list[dict]:
    """Logins SSH (sucesso e falha) via journalctl _COMM=sshd."""
    raw = _journalctl(["_COMM=sshd"], period, elevated=elevated)
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = e.get("__REALTIME_TIMESTAMP", "")
        timestamp = _parse_journal_ts(ts)

        if "Accepted" in msg:
            user, ip = _extract_user_ip(msg, "Accepted")
            events.append({
                "timestamp": timestamp,
                "type": "ssh_accept",
                "user": user,
                "ip": ip,
                "raw": msg,
            })
        elif "Failed password" in msg:
            user, ip = _extract_user_ip(msg, "Failed password")
            events.append({
                "timestamp": timestamp,
                "type": "ssh_fail",
                "user": user,
                "ip": ip,
                "raw": msg,
            })
    return events


def collect_sudo_events(period: Period, elevated: bool = False) -> list[dict]:
    """Invocacoes sudo via journalctl _COMM=sudo."""
    raw = _journalctl(["_COMM=sudo"], period, elevated=elevated)
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = e.get("__REALTIME_TIMESTAMP", "")
        timestamp = _parse_journal_ts(ts)

        # Padrao: "user : TTY=pts/0 ; PWD=/home/user ; USER=root ; COMMAND=/usr/bin/dnf update"
        m = re.match(
            r"\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(\S+)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.+?)\s*$",
            msg,
        )
        if m:
            events.append({
                "timestamp": timestamp,
                "type": "sudo",
                "user": m.group(1),
                "tty": m.group(2),
                "pwd": m.group(3),
                "target_user": m.group(4),
                "command": m.group(5),
                "raw": msg,
            })
    return events


def collect_fail2ban_events(period: Period, elevated: bool = False) -> list[dict]:
    """Bans do fail2ban via journalctl SYSLOG_IDENTIFIER=fail2ban-server."""
    raw = _journalctl(["SYSLOG_IDENTIFIER=fail2ban-server"], period, elevated=elevated)
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = e.get("__REALTIME_TIMESTAMP", "")
        timestamp = _parse_journal_ts(ts)

        # Padrao: "[jail] Ban 192.0.2.42"
        m = re.search(r"\[(\S+)\]\s+Ban\s+(\S+)", msg)
        if m:
            events.append({
                "timestamp": timestamp,
                "type": "ban",
                "jail": m.group(1),
                "ip": m.group(2),
                "raw": msg,
            })
            continue

        m = re.search(r"\[(\S+)\]\s+Unban\s+(\S+)", msg)
        if m:
            events.append({
                "timestamp": timestamp,
                "type": "unban",
                "jail": m.group(1),
                "ip": m.group(2),
                "raw": msg,
            })
    return events


def collect_pkexec_events(period: Period, elevated: bool = False) -> list[dict]:
    """Invocacoes pkexec (privilege escalation grafica) via journalctl."""
    raw = _journalctl(["_COMM=pkexec"], period, elevated=elevated)
    events = []
    for e in raw:
        msg = e.get("MESSAGE", "")
        ts = e.get("__REALTIME_TIMESTAMP", "")
        timestamp = _parse_journal_ts(ts)

        # Pkexec costuma logar: "user: Executing command [...]"
        m = re.match(r"\s*(\S+):\s*Executing command\s+\[(.+?)\]", msg)
        if m:
            events.append({
                "timestamp": timestamp,
                "type": "pkexec",
                "user": m.group(1),
                "command": m.group(2),
                "raw": msg,
            })
    return events


def collect_login_history(elevated: bool = False) -> list[dict]:
    """Historico de logins via 'last -F'. Retorna ate 50 entradas mais recentes."""
    cmd = (["pkexec"] if elevated else []) + ["last", "-F", "-n", "50"]
    out = _run(cmd, timeout=10)
    events = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("wtmp begins"):
            continue
        # Formato: "user pts/0  192.168.1.10  Fri May 23 14:30:00 2026 - still logged in"
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


def collect_failed_logins(elevated: bool = False) -> list[dict]:
    """Tentativas falhadas via 'lastb -F' (precisa root)."""
    cmd = ["pkexec", "lastb", "-F", "-n", "100"] if elevated else ["lastb", "-F", "-n", "100"]
    out = _run(cmd, timeout=10)
    events = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("btmp begins"):
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
            })
    return events


# ============================================================
# Helpers de parsing
# ============================================================


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
    """De 'Accepted password for andre from 192.0.2.42 port 22 ssh2', extrai (andre, 192.0.2.42)."""
    m = re.search(rf"{prefix}\s+(?:password|publickey)?\s*for\s+(\S+)\s+from\s+(\S+)", msg)
    if m:
        return m.group(1), m.group(2)
    # Variantes "Failed password for invalid user X from Y"
    m = re.search(rf"{prefix}\s+(?:password|publickey)?\s*for\s+(?:invalid user )?(\S+)\s+from\s+(\S+)", msg)
    if m:
        return m.group(1), m.group(2)
    return "?", "?"


# ============================================================
# Agregacao por template
# ============================================================


def collect_for_activity_overview(period: Period, elevated: bool = False) -> dict:
    """Coleta dados para o template activity_overview."""
    ssh = collect_ssh_events(period, elevated=elevated)
    sudo = collect_sudo_events(period, elevated=elevated)
    bans = collect_fail2ban_events(period, elevated=elevated)
    pkexec_events = collect_pkexec_events(period, elevated=elevated)
    logins = collect_login_history(elevated=elevated)

    # KPIs
    ssh_success = [e for e in ssh if e["type"] == "ssh_accept"]
    ssh_failed = [e for e in ssh if e["type"] == "ssh_fail"]
    bans_only = [e for e in bans if e["type"] == "ban"]

    # Top IPs banidos (count by ip)
    ip_counts: dict[str, int] = {}
    for b in bans_only:
        ip = b.get("ip", "?")
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    top_banned = sorted(ip_counts.items(), key=lambda kv: -kv[1])[:10]

    # Top users de sudo (count by user)
    sudo_user_counts: dict[str, int] = {}
    for s in sudo:
        u = s.get("user", "?")
        sudo_user_counts[u] = sudo_user_counts.get(u, 0) + 1
    top_sudo_users = sorted(sudo_user_counts.items(), key=lambda kv: -kv[1])[:10]

    return {
        "period": period,
        "elevated_mode": elevated,
        "kpis": {
            "ssh_success": len(ssh_success),
            "ssh_failed": len(ssh_failed),
            "sudo_invocations": len(sudo),
            "pkexec_invocations": len(pkexec_events),
            "bans": len(bans_only),
            "logins": len(logins),
        },
        "ssh_success": ssh_success[:50],
        "ssh_failed": ssh_failed[:50],
        "sudo": sudo[:50],
        "bans": bans_only[:50],
        "top_banned_ips": top_banned,
        "top_sudo_users": top_sudo_users,
        "pkexec": pkexec_events[:50],
        "logins": logins[:30],
    }


def collect_for_auth_events(period: Period, elevated: bool = False) -> dict:
    """Coleta dados focados em autenticacao."""
    ssh = collect_ssh_events(period, elevated=elevated)
    sudo = collect_sudo_events(period, elevated=elevated)
    pkexec_events = collect_pkexec_events(period, elevated=elevated)
    logins = collect_login_history(elevated=elevated)
    failed = collect_failed_logins(elevated=elevated)

    return {
        "period": period,
        "elevated_mode": elevated,
        "ssh_success": [e for e in ssh if e["type"] == "ssh_accept"],
        "ssh_failed": [e for e in ssh if e["type"] == "ssh_fail"],
        "sudo": sudo,
        "pkexec": pkexec_events,
        "logins": logins,
        "failed_logins": failed,
    }
