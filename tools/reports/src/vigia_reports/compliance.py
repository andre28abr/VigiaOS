"""Checagens de postura para o relatório de Conformidade LGPD.

Todas **user-readable** (sem pkexec): `systemctl is-active`, `gsettings get`,
`getenforce`, `lsblk`. Cada checagem vira um dict estruturado:

    {label, state, value, detail, critical}

`state` ∈ {"ok", "warn", "off", "unknown"}. A lógica de interpretação fica em
funções puras (`_state_*`) testáveis sem subprocess; `run_compliance_checks()`
só cola subprocess + interpretação.
"""

from __future__ import annotations

import shutil

from vigia_common import proc


def _run(cmd: list[str], timeout: int = 10) -> str:
    """stdout (strip), independente do returncode. '' em erro/binário ausente.

    `systemctl is-active` sai !=0 quando inativo mas imprime 'inactive' no
    stdout — por isso ignoramos o returncode (pegamos sempre o stdout).
    """
    return proc.run(cmd, timeout)[1].strip()


# ============================================================
# Interpretadores puros (testáveis sem subprocess)
# ============================================================


def _state_service(out: str, active_is_good: bool) -> str:
    if not out:
        return "unknown"
    active = out == "active"
    if active_is_good:
        return "ok" if active else "off"
    # serviço cuja presença AUMENTA a superfície (ex: sshd): ativo = atenção
    return "warn" if active else "ok"


def _state_selinux(out: str) -> str:
    o = out.strip().lower()
    if o == "enforcing":
        return "ok"
    if o == "permissive":
        return "warn"
    if o == "disabled":
        return "off"
    return "unknown"


def _state_gsettings(out: str, good: str) -> str:
    if out not in ("true", "false"):
        return "unknown"
    return "ok" if out == good else "warn"


def _state_disk(out: str) -> str:
    if not out:
        return "unknown"
    return "ok" if "crypt" in out else "warn"


# ============================================================
# Score / status / resumo (puros)
# ============================================================


def compliance_score(checks: list[dict]) -> dict:
    """Conta conformidade ignorando itens 'unknown' (não aplicáveis)."""
    applicable = [c for c in checks if c.get("state") != "unknown"]
    total = len(applicable)
    ok = sum(1 for c in applicable if c["state"] == "ok")
    pct = round(ok / total * 100) if total else 0
    return {"ok": ok, "total": total, "pct": pct, "unknown": len(checks) - total}


def compliance_status(checks: list[dict]) -> dict:
    crit_fail = any(c.get("state") in ("warn", "off") and c.get("critical") for c in checks)
    any_fail = any(c.get("state") in ("warn", "off") for c in checks)
    if crit_fail:
        return {"level": "danger", "label": "Pendências críticas"}
    if any_fail:
        return {"level": "warn", "label": "Atenção"}
    return {"level": "ok", "label": "Em conformidade"}


def compliance_summary(checks: list[dict]) -> str:
    score = compliance_score(checks)
    fails = [c["label"] for c in checks if c.get("state") in ("warn", "off")]
    parts = [
        f"{score['ok']} de {score['total']} itens de postura em conformidade "
        f"({score['pct']}%). "
    ]
    if not fails:
        parts.append("Todas as medidas técnicas verificadas estão ativas.")
    else:
        sample = ", ".join(fails[:3])
        parts.append(f"Pendências: {sample}{'…' if len(fails) > 3 else ''}.")
    return "".join(parts)


# ============================================================
# Wrappers subprocess + execução
# ============================================================

_SERVICE_VALUE = {"active": "ativo", "inactive": "desligado", "failed": "falhou"}


def _check_service(unit: str, label: str, detail: str, *, active_is_good: bool,
                   critical: bool = False) -> dict:
    out = _run(["systemctl", "is-active", unit]) if shutil.which("systemctl") else ""
    return {
        "label": label,
        "state": _state_service(out, active_is_good),
        "value": _SERVICE_VALUE.get(out, out or "desconhecido"),
        "detail": detail,
        "critical": critical,
    }


def _check_selinux(label: str, detail: str) -> dict:
    out = _run(["getenforce"]) if shutil.which("getenforce") else ""
    return {
        "label": label,
        "state": _state_selinux(out),
        "value": out or "desconhecido",
        "detail": detail,
        "critical": False,
    }


def _check_gsettings(schema: str, key: str, label: str, detail: str, *, good: str) -> dict:
    out = _run(["gsettings", "get", schema, key]) if shutil.which("gsettings") else ""
    return {
        "label": label,
        "state": _state_gsettings(out, good),
        "value": {"true": "ligado", "false": "desligado"}.get(out, out or "desconhecido"),
        "detail": detail,
        "critical": False,
    }


def _check_disk(label: str, detail: str) -> dict:
    out = _run(["lsblk", "-o", "TYPE"]) if shutil.which("lsblk") else ""
    state = _state_disk(out)
    return {
        "label": label,
        "state": state,
        "value": {"ok": "cifrado (LUKS)", "warn": "não cifrado", "unknown": "desconhecido"}[state],
        "detail": detail,
        "critical": True,
    }


def run_compliance_checks() -> list[dict]:
    """Roda todas as checagens de postura e devolve a lista de itens."""
    return [
        _check_service(
            "firewalld", "Firewall (firewalld)",
            "Bloqueia conexões de entrada não autorizadas — base da segurança de rede (LGPD art. 46).",
            active_is_good=True, critical=True,
        ),
        _check_disk(
            "Disco criptografado (LUKS)",
            "Dados em repouso cifrados: se o equipamento for furtado, os dados ficam ilegíveis (LGPD art. 46).",
        ),
        _check_selinux(
            "SELinux (modo)",
            "Confinamento obrigatório de processos — limita o estrago de um aplicativo comprometido.",
        ),
        _check_service(
            "sshd", "Servidor SSH (entrada)",
            "Acesso remoto por terminal. Mantê-lo desligado reduz a superfície de ataque.",
            active_is_good=False,
        ),
        _check_service(
            "dnscrypt-proxy", "DNS encriptado",
            "Consultas DNS cifradas (DoH/DoT) — o provedor de internet não vê os sites visitados.",
            active_is_good=True,
        ),
        _check_service(
            "fail2ban", "Proteção contra força bruta (fail2ban)",
            "Bane temporariamente IPs que tentam adivinhar a senha repetidamente.",
            active_is_good=True,
        ),
        _check_gsettings(
            "org.gnome.desktop.privacy", "report-technical-problems",
            "Telemetria do GNOME desligada",
            "O sistema não envia relatórios técnicos automáticos para terceiros.",
            good="false",
        ),
        _check_gsettings(
            "org.gnome.system.location", "enabled",
            "Serviços de localização desligados",
            "Aplicativos não acessam a geolocalização da máquina.",
            good="false",
        ),
        _check_gsettings(
            "org.gnome.desktop.screensaver", "lock-enabled",
            "Bloqueio de tela automático",
            "A tela bloqueia sozinha — barreira contra acesso físico não autorizado.",
            good="true",
        ),
    ]
