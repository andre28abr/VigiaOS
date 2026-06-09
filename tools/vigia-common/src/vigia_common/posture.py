"""Postura de segurança do sistema — checagens pro painel "Tudo certo?" e pro
status das ferramentas no Hub.

Desenho: **avaliadores puros** (recebem valores, devolvem `Check` — testáveis
sem tocar no sistema) + **coletores finos** (rodam subprocess/leem arquivos).
Sem dependência de outras tools do Vigia (camada de baixo nível).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass

OK = "ok"
WARN = "warn"
BAD = "bad"
UNKNOWN = "unknown"

# Pior status vence (pro semáforo geral): ok < unknown < warn < bad
_ORDER = {OK: 0, UNKNOWN: 1, WARN: 2, BAD: 3}


@dataclass(frozen=True)
class Check:
    key: str            # "firewall"
    label: str          # "Firewall"
    status: str         # ok | warn | bad | unknown
    detail: str         # frase curta pro usuário
    fix_tool: str = ""  # id de tool do Hub pra "Resolver" (vazio = sem botão)
    fix_label: str = ""  # rótulo do botão ("Ligar firewall")


# ============================================================
# Avaliadores PUROS (testáveis)
# ============================================================


def eval_firewall(active: bool | None) -> Check:
    if active is None:
        return Check("firewall", "Firewall", UNKNOWN,
                     "Não consegui verificar.", "firewall-gui", "Abrir Firewall")
    if active:
        return Check("firewall", "Firewall", OK, "Ligado e protegendo.")
    return Check("firewall", "Firewall", BAD,
                 "Desligado — seu PC fica mais exposto.",
                 "firewall-gui", "Ligar firewall")


def eval_updates(count: int | None) -> Check:
    if count is None:
        return Check("updates", "Atualizações", UNKNOWN,
                     "Não consegui verificar agora.")
    if count <= 0:
        return Check("updates", "Atualizações", OK, "Sistema em dia.")
    plural = "atualização disponível" if count == 1 else "atualizações disponíveis"
    return Check("updates", "Atualizações", WARN, f"{count} {plural}.",
                 "config", "Ver Atualizações")


def eval_antivirus(installed: bool, db_age_days: float | None) -> Check:
    if not installed:
        return Check("antivirus", "Antivírus", WARN,
                     "ClamAV não está instalado.", "antivirus", "Abrir Antivírus")
    if db_age_days is None:
        return Check("antivirus", "Antivírus", WARN,
                     "Base de vírus não encontrada — atualize.",
                     "antivirus", "Atualizar base")
    if db_age_days <= 7:
        return Check("antivirus", "Antivírus", OK, "Base de vírus atualizada.")
    return Check("antivirus", "Antivírus", WARN,
                 f"Base de vírus com {int(db_age_days)} dias — atualize.",
                 "antivirus", "Atualizar base")


def eval_privacy(hardened: int, total: int) -> Check:
    if total <= 0:
        return Check("privacy", "Privacidade", UNKNOWN,
                     "Não consegui verificar.",
                     "privacy-controls", "Abrir Privacidade")
    if hardened >= total:
        return Check("privacy", "Privacidade", OK,
                     "Ajustes de privacidade ativos.")
    falta = total - hardened
    item = "ajuste recomendado" if falta == 1 else "ajustes recomendados"
    return Check("privacy", "Privacidade", WARN, f"{falta} {item}.",
                 "privacy-controls", "Abrir Privacidade")


def overall_status(checks: list[Check]) -> str:
    """Status geral do semáforo: o pior entre os checks."""
    worst = OK
    for c in checks:
        if _ORDER.get(c.status, 1) > _ORDER.get(worst, 0):
            worst = c.status
    return worst


# ============================================================
# Coletores (subprocess/fs — não testados unitariamente)
# ============================================================


def gather_firewall() -> bool | None:
    """firewalld está ativo? (systemctl is-active firewalld)."""
    if not shutil.which("systemctl"):
        return None
    try:
        r = subprocess.run(["systemctl", "is-active", "firewalld"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except (OSError, subprocess.SubprocessError):
        return None


_CLAMAV_DIR = "/var/lib/clamav"


def gather_antivirus() -> tuple[bool, float | None]:
    """(clamav instalado?, idade da base em dias | None)."""
    installed = (shutil.which("clamscan") is not None
                 or shutil.which("freshclam") is not None)
    newest: float | None = None
    try:
        for name in os.listdir(_CLAMAV_DIR):
            if name.endswith((".cvd", ".cld")):
                m = os.path.getmtime(os.path.join(_CLAMAV_DIR, name))
                newest = m if newest is None else max(newest, m)
    except OSError:
        pass
    age = None if newest is None else max(0.0, (time.time() - newest) / 86400.0)
    return (installed, age)


# Chaves de privacidade do GNOME consideradas "endurecidas" no valor à direita.
_PRIVACY_KEYS = [
    ("org.gnome.desktop.privacy", "report-technical-problems", "false"),
    ("org.gnome.system.location", "enabled", "false"),
    ("org.gnome.desktop.privacy", "send-software-usage-stats", "false"),
    ("org.gnome.desktop.privacy", "remember-recent-files", "false"),
]


def gather_privacy() -> tuple[int, int]:
    """(quantas chaves de privacidade estão endurecidas, total verificável)."""
    if not shutil.which("gsettings"):
        return (0, 0)
    hardened = 0
    total = 0
    for schema, key, want in _PRIVACY_KEYS:
        try:
            r = subprocess.run(["gsettings", "get", schema, key],
                               capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode != 0:
            continue  # schema/chave não existe nesta versão do GNOME
        total += 1
        if r.stdout.strip().lower() == want:
            hardened += 1
    return (hardened, total)


def gather_updates() -> int | None:
    """Nº de atualizações pendentes via `dnf --cacheonly check-update` (rápido,
    sem rede; pode estar levemente desatualizado). None se não der pra checar."""
    if not shutil.which("dnf"):
        return None
    try:
        r = subprocess.run(["dnf", "-q", "--cacheonly", "check-update"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode == 0:
        return 0
    if r.returncode == 100:  # 100 = há atualizações
        count = 0
        for line in r.stdout.splitlines():
            if line and not line[0].isspace() and len(line.split()) >= 3:
                count += 1
        return count
    return None


def run_all() -> list[Check]:
    """Checagens rápidas: atualizações, firewall, antivírus, privacidade."""
    inst, age = gather_antivirus()
    h, t = gather_privacy()
    return [
        eval_updates(gather_updates()),
        eval_firewall(gather_firewall()),
        eval_antivirus(inst, age),
        eval_privacy(h, t),
    ]
