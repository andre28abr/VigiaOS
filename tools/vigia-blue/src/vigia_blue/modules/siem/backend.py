"""Backend do Vigia SIEM — detecção e triagem de eventos de segurança.

Camada de **detecção** sobre o core do Activity Log (binário Rust `vigia-log`):
coleta o mesmo *bundle* de eventos (audit / journald / fail2ban), mas em vez de
só listar a linha do tempo, aplica **regras de detecção** e gera **alertas**
triados por severidade — cada um com explicação leiga + recomendação.

Diferença pro Activity Log (pra não ser redundante): o Activity Log é o
*navegador* ("veja tudo que aconteceu"); o SIEM é a camada de *detecção*
("o que é suspeito?"). Mesma fonte de dados, propósitos diferentes — é como uma
stack de SOC real separa *agregação de logs* de *SIEM/detecção*.

Divisão (mesmo padrão do Vigia YARA):
- Partes PURAS (testáveis headless, sem `vigia-log` e sem gi):
    * `parse_bundle(dict)`   → (events, correlations)
    * `detect(events, ...)`  → list[Alert]   — o MOTOR de regras
    * `rules_catalog()`      → list[Rule]    — metadados p/ a aba "Regras"
- Parte que toca o sistema:
    * `collect(...)`  → roda `vigia-log --output json-bundle`
    * `analyze(...)`  → collect + detect + relatório JSON 0600

O VigiaBlue NÃO importa o pacote Python do Activity Log — fala direto com o
binário `vigia-log` (o artefato compartilhado), mantendo o produto independente.

Formato do `payload` de cada evento (o `Event` serializado pelo core):
- audit:    {source, audit_id, records:[{record_type, fields:{res, acct, addr,
            exe, permissive, ...}}]}
- journal:  {source, priority, message, unit, comm, pid, uid}
- fail2ban: {source, level, jail, action:{kind}, ip, raw_message}
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from vigia_common import proc
from vigia_common.state import load_json, save_json_0600

# ~/.local/share/vigia-siem/{analysis-*.json}
DATA_DIR = Path.home() / ".local" / "share" / "vigia-siem"
REPORTS_DIR = DATA_DIR

# Binário do core (Activity Log). É o artefato compartilhado — não dependemos do
# pacote Python `vigia_log_gui`, só do binário no PATH.
VIGIA_LOG_BIN = "vigia-log"

# Fontes padrão que NÃO exigem root (audit precisa de privilégio → opcional).
DEFAULT_SOURCES = ["journald", "fail2ban"]

# Escala de severidade do SIEM (mesma do Vigia YARA + "info"). Ordena os alertas.
SEVERITY_RANK = {"info": 0, "baixo": 1, "suspeito": 2, "alto": 3, "critico": 4}

# Limiares das regras (ajustáveis). O bundle já vem limitado pelo --limit do core,
# então a contagem é "dentro da janela coletada".
SSH_BRUTEFORCE_MIN = 5      # nº de falhas da mesma origem p/ virar alerta
SSH_BRUTEFORCE_CRIT = 20    # acima disso, vira "crítico"
FAILED_SUDO_HIGH = 5        # acima disso, falha de sudo vira "alto"

_IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


# ============================================================
# Modelo de dados
# ============================================================


@dataclass
class Event:
    """Um evento coletado do core, já normalizado (espelha o EventWire)."""

    timestamp: str
    source: str               # "audit" | "journal" | "fail2ban"
    severity: str             # core: routine | interesting | suspicious
    narrative: str            # narrativa pt-BR pré-renderizada pelo core
    payload: dict = field(default_factory=dict)


@dataclass
class Alert:
    """Um achado do motor de detecção — o que a UI mostra como alerta amigável."""

    rule_id: str
    title: str                # curto, ex.: "Força-bruta de login — 1.2.3.4"
    description: str          # leigo: o que é + por que importa
    recommendation: str      # leigo: o que fazer
    severity: str             # info | baixo | suspeito | alto | critico
    count: int = 1            # nº de eventos que contribuíram
    when: str = ""            # "primeiro … último" (ou único)
    evidence: list[str] = field(default_factory=list)  # linhas técnicas (amostra)


@dataclass
class Rule:
    """Metadado de uma regra de detecção (alimenta a aba 'Regras' — puro/data)."""

    id: str
    name: str
    category: str             # rótulo curto p/ agrupar (Autenticação, Rede, …)
    severity: str             # severidade típica/máxima (catálogo)
    description: str          # leigo: o que a regra procura
    recommendation: str      # leigo: o que fazer quando dispara
    sources: list[str]        # fontes que a regra usa


@dataclass
class SiemResult:
    alerts: list[Alert] = field(default_factory=list)
    events_count: int = 0
    sources: list[str] = field(default_factory=list)
    elapsed_sec: float = 0.0
    error: str = ""           # erro amigável (core ausente, auth cancelada, …)
    started_at: str = ""      # ISO timestamp


# ============================================================
# Helpers de leitura do payload (puros, defensivos)
# ============================================================


def _payload(ev: Event) -> dict:
    return ev.payload if isinstance(ev.payload, dict) else {}


def _audit_records(ev: Event) -> list[dict]:
    recs = _payload(ev).get("records", [])
    return [r for r in recs if isinstance(r, dict)] if isinstance(recs, list) else []


def _audit_types(ev: Event) -> list[str]:
    return [str(r.get("record_type", "")) for r in _audit_records(ev)]


# Mesma heurística do core (AVC > USER_AUTH > USER_LOGIN > USER_ACCT > ANOM_* > SYSCALL).
_AUDIT_PRIORITY = (
    "AVC", "USER_AUTH", "USER_LOGIN", "USER_ACCT",
    "ANOM_PROMISCUOUS", "ANOM_ABEND", "SYSCALL",
)


def _audit_primary_type(ev: Event) -> str:
    types = _audit_types(ev)
    for t in _AUDIT_PRIORITY:
        if t in types:
            return t
    return types[0] if types else "UNKNOWN"


def _audit_field(ev: Event, key: str) -> str | None:
    """Primeiro valor encontrado p/ a chave em qualquer record (espelha core.field)."""
    for r in _audit_records(ev):
        fields = r.get("fields", {})
        if isinstance(fields, dict) and key in fields:
            return str(fields[key])
    return None


def _is_failure(res: str | None) -> bool:
    """`res` do audit indica falha? (success/1/yes = sucesso; resto preenchido = falha)."""
    if not res:
        return False
    return res.lower() not in ("success", "1", "yes")


def _msg(ev: Event) -> str:
    return str(_payload(ev).get("message", ""))


def _unit(ev: Event) -> str:
    return str(_payload(ev).get("unit") or "")


def _comm(ev: Event) -> str:
    return str(_payload(ev).get("comm") or "")


def _priority(ev: Event) -> str:
    return str(_payload(ev).get("priority", "")).lower()


def _f2b_action(ev: Event) -> str:
    a = _payload(ev).get("action", {})
    if isinstance(a, dict):
        return str(a.get("kind", "")).lower()
    return str(a).lower()


def _f2b_ip(ev: Event) -> str:
    return str(_payload(ev).get("ip") or "")


def _f2b_jail(ev: Event) -> str:
    return str(_payload(ev).get("jail") or "")


def _span(evs: list[Event]) -> str:
    ts = sorted(e.timestamp for e in evs if e.timestamp)
    if not ts:
        return ""
    return ts[0] if ts[0] == ts[-1] else f"{ts[0]} … {ts[-1]}"


def _evidence(evs: list[Event], n: int = 5) -> list[str]:
    out: list[str] = []
    for e in evs[:n]:
        line = e.narrative or _msg(e) or str(_payload(e).get("raw_message", ""))
        if line:
            out.append(line)
    return out


# ============================================================
# Parser do bundle (puro)
# ============================================================


def parse_bundle(data: dict) -> tuple[list[Event], list[dict]]:
    """Converte o JSON do `vigia-log` em (eventos, correlações). Nunca crasha."""
    if not isinstance(data, dict):
        return [], []
    events: list[Event] = []
    raw_events = data.get("events", [])
    if isinstance(raw_events, list):
        for raw in raw_events:
            if not isinstance(raw, dict):
                continue
            payload = raw.get("payload", {})
            events.append(Event(
                timestamp=str(raw.get("timestamp", "")),
                source=str(raw.get("source", "")),
                severity=str(raw.get("severity", "routine")),
                narrative=str(raw.get("narrative", "")),
                payload=payload if isinstance(payload, dict) else {},
            ))
    raw_corrs = data.get("correlations", [])
    corrs = [c for c in raw_corrs if isinstance(c, dict)] if isinstance(raw_corrs, list) else []
    return events, corrs


# ============================================================
# Regras de detecção (puras) — cada uma: (events) -> list[Alert]
# ============================================================


def _r_ssh_bruteforce(events: list[Event]) -> list[Alert]:
    """Muitas falhas de login da mesma origem = ataque de força-bruta."""
    groups: dict[str, list[Event]] = defaultdict(list)
    for ev in events:
        key: str | None = None
        if ev.source == "audit":
            if any(t in ("USER_AUTH", "USER_LOGIN", "LOGIN") for t in _audit_types(ev)):
                if _is_failure(_audit_field(ev, "res")):
                    key = (_audit_field(ev, "addr") or _audit_field(ev, "hostname")
                           or _audit_field(ev, "acct") or "origem desconhecida")
        elif ev.source == "journal":
            low = _msg(ev).lower()
            if ("failed password" in low or "authentication failure" in low
                    or "invalid user" in low or "failed publickey" in low):
                m = _IP_RE.search(_msg(ev))
                key = m.group(1) if m else (_comm(ev) or "origem desconhecida")
        if key is not None:
            groups[key].append(ev)

    alerts: list[Alert] = []
    for key, hits in groups.items():
        if len(hits) < SSH_BRUTEFORCE_MIN:
            continue
        sev = "critico" if len(hits) >= SSH_BRUTEFORCE_CRIT else "alto"
        alerts.append(Alert(
            rule_id="ssh_bruteforce",
            title=f"Força-bruta de login — {key}",
            description=(
                f"Houve {len(hits)} tentativas de login que falharam vindas de "
                f"{key}. Esse padrão costuma ser alguém tentando adivinhar a "
                "senha por repetição (ataque de força-bruta)."
            ),
            recommendation=(
                "Confirme se foi você. Se não, bloqueie a origem (firewall / "
                "fail2ban), prefira chave SSH a senha e considere desativar o "
                "login por senha."
            ),
            severity=sev, count=len(hits), when=_span(hits),
            evidence=_evidence(hits),
        ))
    return alerts


def _r_failed_sudo(events: list[Event]) -> list[Alert]:
    """Tentativas falhas de virar administrador (sudo/su)."""
    hits: list[Event] = []
    for ev in events:
        if ev.source == "audit":
            exe = (_audit_field(ev, "exe") or "").lower()
            is_priv_tool = exe.endswith("/sudo") or exe.endswith("/su") or "sudo" in exe
            has_auth = any(t in ("USER_CMD", "USER_AUTH", "USER_ACCT") for t in _audit_types(ev))
            if is_priv_tool and has_auth and _is_failure(_audit_field(ev, "res")):
                hits.append(ev)
        elif ev.source == "journal":
            comm = _comm(ev).lower()
            low = _msg(ev).lower()
            if comm in ("sudo", "su") and (
                "authentication failure" in low or "incorrect password" in low
                or "not in the sudoers" in low or "auth could not" in low
                or "conversation failed" in low
            ):
                hits.append(ev)
    if not hits:
        return []
    sev = "alto" if len(hits) >= FAILED_SUDO_HIGH else "suspeito"
    return [Alert(
        rule_id="failed_sudo",
        title=f"Falha ao obter privilégio de administrador ({len(hits)}x)",
        description=(
            "Houve tentativas de virar administrador (sudo/su) que falharam — "
            "senha errada ou usuário sem permissão. Pode ser engano, mas também "
            "é típico de quem tenta escalar privilégio."
        ),
        recommendation=(
            "Confirme se foi você. Falhas repetidas de sudo por um usuário que "
            "não deveria ter acesso merecem investigação."
        ),
        severity=sev, count=len(hits), when=_span(hits), evidence=_evidence(hits),
    )]


# tipos de audit e comandos ligados a gestão de contas
_ACCOUNT_TYPES = {
    "ADD_USER", "DEL_USER", "ADD_GROUP", "DEL_GROUP", "USER_MGMT", "GRP_MGMT",
    "ROLE_ASSIGN", "ROLE_REMOVE", "ACCT_LOCK", "ACCT_UNLOCK",
}
_ACCOUNT_COMMS = {
    "useradd", "userdel", "usermod", "groupadd", "groupdel", "gpasswd", "passwd",
}


def _r_account_change(events: list[Event]) -> list[Alert]:
    """Criação/alteração de usuários e grupos (persistência clássica)."""
    hits: list[Event] = []
    for ev in events:
        if ev.source == "audit" and (_ACCOUNT_TYPES & set(_audit_types(ev))):
            hits.append(ev)
        elif ev.source == "journal" and _comm(ev).lower() in _ACCOUNT_COMMS:
            hits.append(ev)
    if not hits:
        return []
    return [Alert(
        rule_id="account_change",
        title=f"Conta de usuário/grupo criada ou alterada ({len(hits)}x)",
        description=(
            "Detectamos criação ou alteração de contas de usuário/grupo. Quando "
            "não é uma mudança planejada, criar conta é uma forma comum de um "
            "invasor manter o acesso (persistência)."
        ),
        recommendation=(
            "Confirme se a mudança foi feita por você ou pela TI. Conta nova "
            "inesperada é um sinal grave — investigue."
        ),
        severity="suspeito", count=len(hits), when=_span(hits), evidence=_evidence(hits),
    )]


def _r_service_failure(events: list[Event]) -> list[Alert]:
    """Serviços do systemd que falharam ou entraram em estado de erro."""
    hits: list[Event] = []
    for ev in events:
        if ev.source == "journal":
            low = _msg(ev).lower()
            bad_prio = _priority(ev) in ("emerg", "alert", "crit", "err")
            looks_failed = (
                "failed to start" in low or "entered failed state" in low
                or "failed with result" in low or "start request repeated too quickly" in low
            )
            if looks_failed or (bad_prio and _unit(ev).endswith(".service")):
                hits.append(ev)
        elif ev.source == "audit":
            if any(t in ("SERVICE_START", "SERVICE_STOP") for t in _audit_types(ev)):
                if (_audit_field(ev, "res") or "").lower() == "failed":
                    hits.append(ev)
    if not hits:
        return []
    units = sorted({_unit(e) for e in hits if _unit(e)})
    sev = "suspeito" if len(hits) >= 10 else "baixo"
    extra = f" Serviços afetados: {', '.join(units[:6])}." if units else ""
    return [Alert(
        rule_id="service_failure",
        title=f"Falha de serviço do sistema ({len(hits)}x)",
        description=(
            "Um ou mais serviços do sistema (systemd) falharam ou entraram em "
            "estado de erro." + extra + " Pode ser problema técnico comum, mas "
            "falhas repetidas também podem indicar sabotagem ou um serviço "
            "sendo derrubado."
        ),
        recommendation=(
            "Veja o log do serviço afetado (`journalctl -u <serviço>`). Se você "
            "não reconhece o serviço ou a falha se repete, investigue."
        ),
        severity=sev, count=len(hits), when=_span(hits), evidence=_evidence(hits),
    )]


def _r_selinux_denial(events: list[Event]) -> list[Alert]:
    """Bloqueios do SELinux (AVC). Enforcing (permissive=0) é mais sério."""
    enforcing: list[Event] = []
    permissive: list[Event] = []
    for ev in events:
        if ev.source == "audit" and "AVC" in _audit_types(ev):
            (enforcing if _audit_field(ev, "permissive") == "0" else permissive).append(ev)
    alerts: list[Alert] = []
    if enforcing:
        alerts.append(Alert(
            rule_id="selinux_denial",
            title=f"SELinux bloqueou uma ação ({len(enforcing)}x)",
            description=(
                "O SELinux (proteção do sistema) bloqueou ações em modo "
                "enforcing — algum programa tentou fazer algo que sua política "
                "não permite. Pode ser configuração legítima faltando, mas "
                "também é o que acontece quando um malware tenta agir."
            ),
            recommendation=(
                "Se você não reconhece o programa bloqueado, investigue. Se for "
                "software legítimo, ajuste a política (não desligue o SELinux)."
            ),
            severity="suspeito", count=len(enforcing), when=_span(enforcing),
            evidence=_evidence(enforcing),
        ))
    if permissive:
        alerts.append(Alert(
            rule_id="selinux_denial",
            title=f"SELinux registrou ação que seria bloqueada ({len(permissive)}x)",
            description=(
                "O SELinux está em modo permissivo aqui: registrou ações que "
                "seriam bloqueadas, mas as deixou passar. Útil para diagnóstico."
            ),
            recommendation=(
                "Reveja se essas ações são esperadas antes de voltar ao modo "
                "enforcing."
            ),
            severity="baixo", count=len(permissive), when=_span(permissive),
            evidence=_evidence(permissive),
        ))
    return alerts


_PKG_COMMS = {"rpm-ostree", "rpm", "dnf", "yum", "packagekitd", "dpkg", "flatpak"}
_PKG_KEYWORDS = ("installed:", "removed:", "upgraded:", "downgraded:",
                 "layering", "uninstalled", "created new deployment")


def _r_package_change(events: list[Event]) -> list[Alert]:
    """Instalação/remoção/atualização de software (auditoria de mudança)."""
    hits: list[Event] = []
    for ev in events:
        if ev.source != "journal":
            continue
        low = _msg(ev).lower()
        if _comm(ev).lower() in _PKG_COMMS or any(k in low for k in _PKG_KEYWORDS):
            hits.append(ev)
    if not hits:
        return []
    return [Alert(
        rule_id="package_change",
        title=f"Software instalado, removido ou atualizado ({len(hits)}x)",
        description=(
            "Houve mudança no software instalado (pacotes via rpm-ostree / dnf / "
            "flatpak). É informativo — serve de trilha de auditoria de mudanças, "
            "mas software instalado sem você saber merece atenção."
        ),
        recommendation=(
            "Confira se a instalação/remoção foi autorizada. Em escritório, "
            "mudanças de software devem ser planejadas."
        ),
        severity="info", count=len(hits), when=_span(hits), evidence=_evidence(hits),
    )]


def _r_fail2ban_ban(events: list[Event]) -> list[Alert]:
    """IPs que o fail2ban bloqueou por comportamento abusivo."""
    hits = [ev for ev in events if ev.source == "fail2ban" and _f2b_action(ev) == "ban"]
    if not hits:
        return []
    ips = sorted({_f2b_ip(e) for e in hits if _f2b_ip(e)})
    jails = sorted({_f2b_jail(e) for e in hits if _f2b_jail(e)})
    where = f" Serviços visados: {', '.join(jails)}." if jails else ""
    ip_list = f" IPs: {', '.join(ips[:8])}." if ips else ""
    return [Alert(
        rule_id="fail2ban_ban",
        title=f"IP bloqueado pelo fail2ban ({len(ips) or len(hits)} origem(ns))",
        description=(
            "O fail2ban bloqueou origens por comportamento abusivo (ex.: muitas "
            "falhas de SSH)." + where + ip_list + " Isso é bom — sua defesa "
            "agiu —, mas também mostra que você está sendo sondado de fora."
        ),
        recommendation=(
            "Sua proteção está funcionando. Muitos bans = varredura constante; "
            "reforce a exposição mínima (só portas necessárias abertas)."
        ),
        severity="suspeito", count=len(hits), when=_span(hits), evidence=_evidence(hits),
    )]


# Catálogo (metadados — alimenta a aba "Regras"). Ordem = como aparecem.
RULES: list[Rule] = [
    Rule("ssh_bruteforce", "Força-bruta de login (SSH)", "Autenticação", "alto",
         "Detecta muitas tentativas de login que falharam vindas da mesma "
         "origem — sinal clássico de quem tenta adivinhar a senha.",
         "Bloqueie a origem, prefira chave SSH a senha e ative o fail2ban.",
         ["audit", "journald"]),
    Rule("failed_sudo", "Falha de elevação (sudo/su)", "Privilégio", "suspeito",
         "Detecta tentativas falhas de virar administrador — senha errada ou "
         "usuário sem permissão.",
         "Confirme se foi você; falhas repetidas merecem investigação.",
         ["audit", "journald"]),
    Rule("account_change", "Conta de usuário criada/alterada", "Contas", "suspeito",
         "Detecta criação/alteração de usuários e grupos — forma comum de um "
         "invasor manter acesso.",
         "Confirme se a mudança foi planejada. Conta nova inesperada é grave.",
         ["audit", "journald"]),
    Rule("service_failure", "Falha de serviço do sistema", "Disponibilidade", "baixo",
         "Detecta serviços (systemd) que falharam ou entraram em estado de erro.",
         "Veja o log do serviço; falhas repetidas podem indicar problema ou "
         "sabotagem.",
         ["journald", "audit"]),
    Rule("selinux_denial", "Bloqueio do SELinux", "Kernel/MAC", "suspeito",
         "Detecta ações bloqueadas pelo SELinux (AVC). Em modo enforcing, algo "
         "tentou fazer o que não devia.",
         "Se não foi configuração legítima, investigue o processo bloqueado.",
         ["audit"]),
    Rule("package_change", "Software instalado ou removido", "Mudança", "info",
         "Registra instalação/remoção/atualização de pacotes (rpm-ostree/dnf/"
         "flatpak) — trilha de auditoria de mudanças.",
         "Confira se a mudança de software foi autorizada.",
         ["journald"]),
    Rule("fail2ban_ban", "IP bloqueado pelo fail2ban", "Rede", "suspeito",
         "Mostra IPs que o fail2ban bloqueou por abuso (ex.: muitas falhas de SSH).",
         "Confirma que sua defesa está ativa; muitos bans = você está sob varredura.",
         ["fail2ban"]),
]

_MATCHERS = {
    "ssh_bruteforce": _r_ssh_bruteforce,
    "failed_sudo": _r_failed_sudo,
    "account_change": _r_account_change,
    "service_failure": _r_service_failure,
    "selinux_denial": _r_selinux_denial,
    "package_change": _r_package_change,
    "fail2ban_ban": _r_fail2ban_ban,
}


def rules_catalog() -> list[Rule]:
    """Metadados das regras de detecção (p/ a aba 'Regras'). Puro."""
    return list(RULES)


# ============================================================
# Correlações do core → alertas (bônus)
# ============================================================

_CORE_SEV = {"suspicious": "suspeito", "interesting": "baixo", "routine": "info"}


def _alert_from_correlation(c: dict) -> Alert:
    sev = _CORE_SEV.get(str(c.get("severity", "")).lower(), "baixo")
    kind = str(c.get("kind", ""))
    ts, end = str(c.get("timestamp", "")), str(c.get("end", ""))
    when = ts if (not end or end == ts) else f"{ts} … {end}"
    n = c.get("contributing_count", 0)
    return Alert(
        rule_id="correlation",
        title=f"Padrão correlacionado: {kind}" if kind else "Padrão correlacionado",
        description=(str(c.get("summary", ""))
                    or "O motor cruzou vários eventos num mesmo padrão suspeito."),
        recommendation=(
            "Padrão detectado cruzando várias fontes — revise os eventos do "
            "período no Activity Log."
        ),
        severity=sev, count=int(n) if isinstance(n, (int, float)) else 0,
        when=when, evidence=[],
    )


# ============================================================
# Motor (puro): aplica todas as regras
# ============================================================


def detect(events: list[Event], correlations: list[dict] | None = None) -> list[Alert]:
    """Aplica todas as regras + correlações do core. Ordena por severidade (desc).

    Uma regra que levante exceção é ignorada (nunca derruba a análise inteira).
    """
    alerts: list[Alert] = []
    for rule in RULES:
        fn = _MATCHERS.get(rule.id)
        if not fn:
            continue
        try:
            alerts.extend(fn(events))
        except Exception:  # noqa: BLE001 — robustez: regra ruim não quebra o resto
            continue
    for c in (correlations or []):
        try:
            alerts.append(_alert_from_correlation(c))
        except Exception:  # noqa: BLE001
            continue
    alerts.sort(key=lambda a: SEVERITY_RANK.get(a.severity, 0), reverse=True)
    return alerts


def severity_counts(alerts: list[Alert]) -> dict[str, int]:
    """Conta alertas por severidade (p/ a linha de resumo da UI)."""
    out: dict[str, int] = defaultdict(int)
    for a in alerts:
        out[a.severity] += 1
    return dict(out)


# ============================================================
# Coleta (toca o sistema via vigia-log) + análise
# ============================================================


def core_available() -> bool:
    return shutil.which(VIGIA_LOG_BIN) is not None


def core_install_hint() -> str:
    return (
        "O motor `vigia-log` (core do Activity Log) não foi encontrado. Ele é "
        "compartilhado com o módulo Activity Log do VigiaHub.\n\n"
        "Compile e instale:\n"
        "  cd tools/activity-log\n"
        "  cargo build --release\n"
        "  sudo install -m 0755 target/release/vigia-log /usr/local/bin/"
    )


def collect(
    sources: list[str] | None = None,
    elevated: bool = False,
    limit: int = 800,
    timeout: int = 90,
) -> tuple[dict | None, str]:
    """Roda `vigia-log --output json-bundle`. Retorna (data, erro_amigável).

    `elevated=True` prefixa `pkexec` (UM diálogo polkit) p/ acessar o audit do
    sistema. argv em LISTA — nunca shell string (convenção de segurança).
    """
    srcs = sources or list(DEFAULT_SOURCES)
    if not core_available():
        return None, core_install_hint()
    if not srcs:
        return None, "Nenhuma fonte selecionada."

    cmd: list[str] = []
    if elevated:
        cmd.append("pkexec")
    cmd += [VIGIA_LOG_BIN, "--output", "json-bundle", "--limit", str(limit)]
    cmd += ["--sources", *srcs]

    rc, out, err = proc.run(cmd, timeout=timeout)
    if rc in (126, 127):
        return None, "Autenticação cancelada (pkexec)."
    if rc != 0 and not out:
        return None, (err.strip() or "Falha ao executar o vigia-log.")[:500]
    try:
        data = json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return None, "Resposta inválida do vigia-log (JSON malformado)."
    if not isinstance(data, dict):
        return None, "Resposta inesperada do vigia-log."
    return data, ""


def analyze(
    sources: list[str] | None = None,
    elevated: bool = False,
    limit: int = 800,
    timeout: int = 90,
) -> SiemResult:
    """Coleta o bundle, roda o motor de detecção e devolve o resultado. Nunca levanta."""
    srcs = sources or list(DEFAULT_SOURCES)
    result = SiemResult(
        sources=list(srcs),
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    t0 = time.monotonic()
    data, err = collect(sources=srcs, elevated=elevated, limit=limit, timeout=timeout)
    if data is None:
        result.error = err
        result.elapsed_sec = round(time.monotonic() - t0, 2)
        return result

    events, corrs = parse_bundle(data)
    result.events_count = len(events)
    bundle_sources = data.get("sources")
    if isinstance(bundle_sources, list) and bundle_sources:
        result.sources = [str(s) for s in bundle_sources]
    result.alerts = detect(events, corrs)
    result.elapsed_sec = round(time.monotonic() - t0, 2)
    return result


# ============================================================
# Relatórios (JSON 0600 + histórico) — padrão Vigia YARA / Antivírus
# ============================================================


def _ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def save_report(result: SiemResult) -> Path | None:
    """Salva o resultado em ~/.local/share/vigia-siem/analysis-<ts>.json (0600)."""
    if not result.started_at:
        return None
    rd = _ensure_reports_dir()
    safe_ts = result.started_at.replace(":", "-").replace(".", "_")
    path = rd / f"analysis-{safe_ts}.json"
    data = {
        "started_at": result.started_at,
        "sources": result.sources,
        "events_count": result.events_count,
        "elapsed_sec": result.elapsed_sec,
        "error": result.error,
        "alerts": [
            {"rule_id": a.rule_id, "title": a.title, "description": a.description,
             "recommendation": a.recommendation, "severity": a.severity,
             "count": a.count, "when": a.when, "evidence": a.evidence}
            for a in result.alerts
        ],
    }
    return path if save_json_0600(path, data) else None


def list_recent_reports(limit: int = 20) -> list[dict]:
    """Análises salvas, mais novas primeiro (descarta corrompidas)."""
    if not REPORTS_DIR.is_dir():
        return []
    files = sorted(
        REPORTS_DIR.glob("analysis-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out: list[dict] = []
    for f in files[:limit]:
        data = load_json(f)
        if isinstance(data, dict):
            data["_file"] = str(f)
            out.append(data)
    return out
