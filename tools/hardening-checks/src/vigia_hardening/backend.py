"""Backend: roda Lynis e parseia o report.

Lynis grava resultado em /var/log/lynis-report.dat (formato chave=valor).
Algumas chaves aparecem multiplas vezes (warning[], suggestion[]) — sao listas.

A audit completa precisa de root (le /etc/shadow, sysctl, etc.) — chamamos
via `pkexec` para abrir dialog polkit nativo.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

REPORT_PATH = Path("/var/log/lynis-report.dat")
LOG_PATH = Path("/var/log/lynis.log")


# Categorias de testes Lynis (prefixo do test-id), traduzidas pt-BR.
CATEGORY_LABELS: dict[str, str] = {
    "AUTH": "Autenticacao",
    "BANN": "Banners de login",
    "BOOT": "Boot e loader",
    "CONT": "Containers",
    "CRYP": "Criptografia",
    "CUST": "Custom (auditor)",
    "DBS":  "Bancos de dados",
    "DEPR": "Itens obsoletos",
    "FILE": "Permissoes de arquivos",
    "FINT": "Integridade de arquivos",
    "FIRE": "Firewall",
    "HRDN": "Hardening geral",
    "HTTP": "Servidores HTTP",
    "INSE": "Insecure services",
    "KRNL": "Kernel e sysctl",
    "LDAP": "LDAP",
    "LOGG": "Logging e syslog",
    "MACF": "MAC (SELinux/AppArmor)",
    "MAIL": "Servidores de email",
    "MALW": "Malware scanner",
    "NAME": "Resolucao DNS",
    "NETW": "Rede",
    "NFS":  "NFS",
    "PHP":  "PHP",
    "PHYS": "Seguranca fisica",
    "PKGS": "Pacotes instalados",
    "PRNT": "Impressao",
    "PROC": "Processos",
    "RPCS": "RPC services",
    "SCHD": "Tarefas agendadas (cron)",
    "SHLL": "Shells",
    "SNMP": "SNMP",
    "SQD":  "Squid proxy",
    "SSH":  "Servidor SSH",
    "STRG": "Storage / discos",
    "TIME": "Tempo e NTP",
    "TOOL": "Tools auxiliares",
    "USB":  "Dispositivos USB",
    "VRTL": "Virtualizacao",
    "WEBS": "Servidores web",
}


def category_label(category: str) -> str:
    """Retorna nome amigavel da categoria. Fallback: o codigo cru."""
    return CATEGORY_LABELS.get(category.upper(), category)


@dataclass
class Finding:
    test_id: str       # ex: "KRNL-5820"
    category: str      # ex: "KRNL"
    message: str
    details: str = ""

    @property
    def category_label(self) -> str:
        return category_label(self.category)


@dataclass
class LynisReport:
    hardening_index: int | None = None
    tests_executed: int = 0
    tests_skipped: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    warnings: list[Finding] = field(default_factory=list)
    suggestions: list[Finding] = field(default_factory=list)
    controls_passed: list[str] = field(default_factory=list)
    controls_failed: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)
    auditor: str = ""
    # finish=true significa que Lynis completou o run sem abortar.
    finish: bool = False

    def has_data(self) -> bool:
        return self.tests_executed > 0 or self.hardening_index is not None

    def categories_summary(self) -> dict[str, dict[str, int]]:
        """Retorna {category: {warnings: N, suggestions: M}}."""
        summary: dict[str, dict[str, int]] = {}
        for f in self.warnings:
            summary.setdefault(f.category, {"warnings": 0, "suggestions": 0})
            summary[f.category]["warnings"] += 1
        for f in self.suggestions:
            summary.setdefault(f.category, {"warnings": 0, "suggestions": 0})
            summary[f.category]["suggestions"] += 1
        return summary


def lynis_installed() -> bool:
    return shutil.which("lynis") is not None


def report_exists() -> bool:
    return REPORT_PATH.is_file()


def report_age_minutes() -> int | None:
    if not REPORT_PATH.is_file():
        return None
    mtime = REPORT_PATH.stat().st_mtime
    return int((time.time() - mtime) / 60)


def _parse_datetime(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _parse_finding(value: str) -> Finding:
    """Parseia 'KRNL-5820|message|-|-' em Finding."""
    parts = value.split("|")
    test_id = parts[0].strip() if parts else ""
    message = parts[1].strip() if len(parts) > 1 else ""
    details = "|".join(p.strip() for p in parts[2:] if p.strip() not in ("", "-")) if len(parts) > 2 else ""
    category = test_id.split("-")[0] if "-" in test_id else "OTHER"
    return Finding(test_id=test_id, category=category, message=message, details=details)


def parse_report(path: Path = REPORT_PATH) -> LynisReport:
    """Le e parseia /var/log/lynis-report.dat."""
    rep = LynisReport()
    if not path.is_file():
        return rep
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return rep

    for raw in text.splitlines():
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            continue
        key, _, value = raw.partition("=")
        key = key.strip()
        value = value.strip()
        if not value:
            continue

        if key == "hardening_index":
            try:
                rep.hardening_index = int(value)
            except ValueError:
                pass
        elif key == "tests_executed":
            # Lynis grava como lista de test IDs separados por '|' (com
            # '|' no final). Ex: "HRDN-7231|HRDN-7230|...|CORE-1000|".
            # Contamos os ids nao-vazios.
            rep.tests_executed = len([t for t in value.split("|") if t.strip()])
        elif key == "tests_skipped":
            rep.tests_skipped = len([t for t in value.split("|") if t.strip()])
        elif key == "finish":
            rep.finish = value.strip().lower() == "true"
        elif key == "exception_event[]":
            rep.exceptions.append(value)
        elif key == "report_datetime_start":
            rep.started_at = _parse_datetime(value)
        elif key == "report_datetime_end":
            rep.finished_at = _parse_datetime(value)
        elif key == "auditor":
            rep.auditor = value
        elif key == "warning[]":
            rep.warnings.append(_parse_finding(value))
        elif key == "suggestion[]":
            rep.suggestions.append(_parse_finding(value))
        elif key == "plugin_enabled[]":
            rep.plugins.append(value)
        elif key in ("control[]",):
            if ":" in value:
                ctrl_id, _, status = value.partition(":")
                if status.upper() in ("OK", "PASS"):
                    rep.controls_passed.append(ctrl_id.strip())
                else:
                    rep.controls_failed.append(ctrl_id.strip())
            else:
                rep.controls_passed.append(value)

    return rep


def run_audit_blocking() -> tuple[bool, str]:
    """Roda 'lynis audit system' via pkexec. BLOQUEANTE — chame em thread.
    Retorna (success, error_message).
    """
    if not lynis_installed():
        return False, (
            "Lynis nao esta instalado.\n\n"
            "Em Fedora Silverblue:\n"
            "rpm-ostree install lynis\n"
            "systemctl reboot"
        )

    # Bug fix critico: Lynis roda como root via pkexec e gera
    # /var/log/lynis-report.dat dono root:root. Sem `chown`/`chmod`, o Hub
    # (rodando como user) nao consegue ler o report — o parser retorna vazio
    # (UI mostra "Nao avaliado" E a notificacao de fim de audit nao dispara,
    # porque report.has_data() fica False).
    #
    # SECURITY: o username vai como ARGUMENTO POSICIONAL do bash ($1), nao
    # interpolado em f-string nem via env var. Atacante setando
    # USER='root && rm -rf /' nao injeta comando (o script trata "$1" como
    # dado, nao como codigo). Validacao extra: regex POSIX-conforme.
    raw_user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    if re.match(r"^[a-z_][a-z0-9_-]{0,31}\$?$", raw_user):
        # POSIX-compliant username
        validated_user = raw_user
    else:
        validated_user = ""  # sem chown — fallback chmod 644
    # IMPORTANTE: o pkexec HIGIENIZA o ambiente — so repassa env vars
    # declaradas num polkit action (allow_env), que nao temos. Por isso o
    # username NAO pode ir via env=... (chegaria VAZIO no processo root,
    # pulando o chown e deixando o report root:root ilegivel pro Hub).
    # argv, ao contrario, e' SEMPRE repassado pelo pkexec.
    script = """set +e
target_user="$1"
lynis audit system --quiet --no-colors
rc=$?
if [ -n "$target_user" ]; then
    # LGPD: chown pro user + 640 — so root e o dono leem (nao world-readable).
    chown "root:$target_user" /var/log/lynis-report.dat 2>/dev/null || true
    chown "root:$target_user" /var/log/lynis.log 2>/dev/null || true
    chmod 640 /var/log/lynis-report.dat 2>/dev/null || true
    chmod 640 /var/log/lynis.log 2>/dev/null || true
else
    # Fallback (username invalido/ausente): 644 garante a leitura pelo Hub.
    chmod 644 /var/log/lynis-report.dat 2>/dev/null || true
    chmod 644 /var/log/lynis.log 2>/dev/null || true
fi
exit $rc
"""
    try:
        # bash -c SCRIPT NOME ARG1 → dentro do script $0=NOME, $1=ARG1.
        # validated_user chega como "$1" (sobrevive a' higienizacao do pkexec).
        result = subprocess.run(
            ["pkexec", "bash", "-c", script, "vigia-hardening", validated_user],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Lynis demorou mais de 10 minutos. Audit cancelado."
    except FileNotFoundError:
        return False, "pkexec nao encontrado. Instale o pacote polkit."

    if result.returncode in (126, 127):
        return False, "Autenticacao cancelada."
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if stderr:
            return False, f"Lynis falhou (codigo {result.returncode}):\n\n{stderr[:600]}"
        return False, f"Lynis retornou codigo {result.returncode}."

    return True, ""


def format_age(minutes: int | None) -> str:
    """Formata 'ha X min' / 'ha X horas' / 'ha X dias'."""
    if minutes is None:
        return "Nunca executado"
    if minutes < 1:
        return "agora mesmo"
    if minutes < 60:
        return f"ha {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"ha {hours}h"
    days = hours // 24
    return f"ha {days} dia{'s' if days > 1 else ''}"
