"""Backend rpm-ostree — wrapper das operacoes de deployment.

Operacoes (read sem root, write com pkexec):
- rpmostree_available() -> bool
- get_deployments() -> list[Deployment]    [sem root]
- rollback_blocking() -> (ok, err)         [pkexec]
- pin_blocking(index) -> (ok, err)         [pkexec]
- unpin_blocking(index) -> (ok, err)       [pkexec]
- cleanup_all_blocking() -> (ok, err)      [pkexec -prm em 1 call]
- get_boot_usage() -> BootUsage            [sem root, df /boot]
- pkg_diff_blocking(commit_a, commit_b) -> str [sem root]
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Deployment:
    """Um deployment rpm-ostree."""
    index: int                       # 0 = atual, 1 = anterior, etc.
    checksum: str                    # SHA-256 base commit
    base_commit: str                 # short (8 chars) — display
    timestamp: int                   # epoch
    timestamp_str: str               # ISO-ish display
    osname: str                      # ex: 'fedora'
    origin: str                      # ex: 'silverblue/x86_64/41'
    version: str                     # ex: '41.20260520.0'
    booted: bool                     # this is currently booted
    pinned: bool                     # protegido contra cleanup
    staged: bool                     # pending — vai virar booted no proximo boot
    layered_packages: list[str] = field(default_factory=list)
    removed_base_packages: list[str] = field(default_factory=list)
    unlocked: str = "none"           # lock state


@dataclass
class BootUsage:
    """Uso de espaco do /boot."""
    total_mb: int = 0
    used_mb: int = 0
    avail_mb: int = 0
    percent_used: int = 0
    available: bool = False          # /boot eh montado separado?


# ============================================================
# Sanity
# ============================================================


def rpmostree_available() -> bool:
    return shutil.which("rpm-ostree") is not None


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


# ============================================================
# Status (read sem root)
# ============================================================


def get_deployments() -> list[Deployment]:
    """Le `rpm-ostree status --json` e parseia."""
    if not rpmostree_available():
        return []

    rc, out, _ = _run(["rpm-ostree", "status", "--json"], timeout=10)
    if rc != 0 or not out:
        return []

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []
    # HARDENING: JSON pode ser valido mas ter formato inesperado
    # (ex: lista no topo, ou deployments nao-lista). Nunca crashar.
    if not isinstance(data, dict):
        return []

    deployments_raw = data.get("deployments", [])
    if not isinstance(deployments_raw, list):
        return []
    out_list: list[Deployment] = []

    for i, d in enumerate(deployments_raw):
        if not isinstance(d, dict):
            continue
        try:
            checksum = d.get("checksum", "") or d.get("base-checksum", "")
            d_obj = Deployment(
                index=i,
                checksum=checksum,
                base_commit=checksum[:8] if checksum else "",
                timestamp=int(d.get("timestamp", 0)),
                timestamp_str=_format_ts(d.get("timestamp", 0)),
                osname=d.get("osname", ""),
                origin=d.get("origin", "") or d.get("container-image-reference", ""),
                version=d.get("version", ""),
                booted=bool(d.get("booted", False)),
                pinned=bool(d.get("pinned", False)),
                staged=bool(d.get("staged", False)),
                layered_packages=list(d.get("requested-packages", []) or
                                      d.get("packages", []) or []),
                removed_base_packages=list(d.get("requested-base-removals", []) or []),
                unlocked=d.get("unlocked", "none"),
            )
        except (ValueError, TypeError):
            # Campo com tipo inesperado (ex: timestamp nao-numerico). Pula.
            continue
        out_list.append(d_obj)

    return out_list


def _format_ts(epoch: int) -> str:
    """Epoch -> ISO-like display."""
    if not epoch:
        return ""
    import datetime as _dt
    try:
        dt = _dt.datetime.fromtimestamp(int(epoch))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return ""


# ============================================================
# /boot usage (read sem root)
# ============================================================


def get_boot_usage() -> BootUsage:
    """Verifica uso do /boot via df."""
    usage = BootUsage()
    if not Path("/boot").is_dir():
        return usage

    rc, out, _ = _run(["df", "-m", "/boot"], timeout=5)
    if rc != 0 or not out:
        return usage

    # df -m output:
    # Filesystem     1M-blocks  Used Available Use% Mounted on
    # /dev/nvme0n1p2       976   245       675  27% /boot
    lines = out.strip().splitlines()
    if len(lines) < 2:
        return usage

    parts = lines[1].split()
    if len(parts) < 6:
        return usage

    try:
        usage.total_mb = int(parts[1])
        usage.used_mb = int(parts[2])
        usage.avail_mb = int(parts[3])
        pct_str = parts[4].rstrip("%")
        usage.percent_used = int(pct_str)
        usage.available = True
    except (ValueError, IndexError):
        return usage

    return usage


# ============================================================
# Operations (com pkexec)
# ============================================================


def rollback_blocking() -> tuple[bool, str]:
    """`pkexec rpm-ostree rollback`. Volta pro deployment anterior."""
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."
    if not rpmostree_available():
        return False, "rpm-ostree nao disponivel."

    rc, _, err = _run(["pkexec", "rpm-ostree", "rollback"], timeout=60)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha no rollback.")[:500]
    return True, ""


def pin_blocking(index: int) -> tuple[bool, str]:
    """`pkexec ostree admin pin <index>`. Protege deployment do cleanup."""
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."
    if index < 0:
        return False, "Indice invalido."

    rc, _, err = _run(
        ["pkexec", "ostree", "admin", "pin", str(index)],
        timeout=30,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao pinnar.")[:500]
    return True, ""


def unpin_blocking(index: int) -> tuple[bool, str]:
    """`pkexec ostree admin pin --unpin <index>`."""
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."
    if index < 0:
        return False, "Indice invalido."

    rc, _, err = _run(
        ["pkexec", "ostree", "admin", "pin", "--unpin", str(index)],
        timeout=30,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao despinnar.")[:500]
    return True, ""


def cleanup_all_blocking() -> tuple[bool, str]:
    """`pkexec rpm-ostree cleanup -p -r -m` num so call.

    Limpa:
    -p (pending): deployment staged que ainda nao bootou
    -r (rollback): deployment do boot anterior
    -m (cached metadata): refspecs em cache
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    rc, out, err = _run(
        ["pkexec", "rpm-ostree", "cleanup", "-p", "-r", "-m"],
        timeout=120,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or out.strip() or "Falha no cleanup.")[:500]
    return True, ""


# ============================================================
# Pkg diff (sem root)
# ============================================================


def pkg_diff_blocking(commit_a: str, commit_b: str) -> str:
    """`rpm-ostree db diff <a> <b>`. Sem root.

    Retorna output bruto (ou erro como string vazia).
    """
    if not rpmostree_available():
        return ""
    if not commit_a or not commit_b:
        return ""

    rc, out, _ = _run(
        ["rpm-ostree", "db", "diff", commit_a, commit_b],
        timeout=20,
    )
    if rc != 0:
        return ""
    return out.strip()


# ============================================================
# Helpers
# ============================================================


def is_safe_to_delete(d: Deployment) -> bool:
    """Pode ser limpo? (nao booted + nao pinned)"""
    return not d.booted and not d.pinned
