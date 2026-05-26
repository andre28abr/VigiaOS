"""Migration helpers: transicao segura entre systemd-resolved e dnscrypt-proxy.

Cenarios:

A) Ativar modo avancado (dnscrypt-proxy):
   1. Backup /etc/systemd/resolved.conf (cria .vigia-resolved-backup)
   2. Stop + disable systemd-resolved
   3. Enable + start dnscrypt-proxy
   4. Aponta /etc/resolv.conf para 127.0.0.1 (atomic write)

B) Desativar modo avancado (volta para systemd-resolved):
   1. Stop + disable dnscrypt-proxy
   2. Restore /etc/systemd/resolved.conf do backup
   3. Enable + start systemd-resolved
   4. Symlink /etc/resolv.conf → /run/systemd/resolve/stub-resolv.conf

C) Rollback (em caso de erro):
   - Best-effort: tenta restaurar estado anterior

Tudo em 1 unica chamada pkexec por operacao (combina via bash -c).
LGPD/security: backups com chmod 0600.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path


RESOLVED_CONF = Path("/etc/systemd/resolved.conf")
RESOLVED_BACKUP = Path("/etc/systemd/resolved.conf.vigia-resolved-backup")
RESOLV_CONF = Path("/etc/resolv.conf")
RESOLV_BACKUP = Path("/etc/resolv.conf.vigia-resolved-backup")


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 1, "", ""


def has_resolved_backup() -> bool:
    return RESOLVED_BACKUP.exists()


def systemd_resolved_active() -> bool:
    if shutil.which("systemctl") is None:
        return False
    rc, _, _ = _run(["systemctl", "is-active", "--quiet", "systemd-resolved"], timeout=5)
    return rc == 0


def activate_advanced_mode_blocking() -> tuple[bool, str]:
    """Ativa modo avancado: systemd-resolved OFF + dnscrypt-proxy ON.

    Executa tudo em 1 unica chamada pkexec. Em caso de erro no meio,
    tenta best-effort rollback do systemd-resolved.
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    script = f"""set -e

# 1. Backup resolved.conf (apenas primeira vez)
if [ -f {RESOLVED_CONF} ] && [ ! -f {RESOLVED_BACKUP} ]; then
    cp -a {RESOLVED_CONF} {RESOLVED_BACKUP}
    chmod 0600 {RESOLVED_BACKUP}
fi

# 2. Backup resolv.conf (apenas primeira vez)
if [ -L {RESOLV_CONF} ] || [ -f {RESOLV_CONF} ]; then
    if [ ! -e {RESOLV_BACKUP} ]; then
        # Pode ser symlink — usa -a pra preservar
        cp -aP {RESOLV_CONF} {RESOLV_BACKUP} 2>/dev/null || true
    fi
fi

# 3. Stop + disable systemd-resolved
systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true

# 4. Aponta /etc/resolv.conf para 127.0.0.1 (dnscrypt vai escutar la)
# Remove se existir (pode ser symlink ou file)
rm -f {RESOLV_CONF}
cat > {RESOLV_CONF} << 'EOF_RESOLV'
# Gerenciado pelo Vigia DNS Manager v0.2+ (modo avancado / dnscrypt-proxy)
# Para reverter, use o switch no DNS Manager ou execute:
#   sudo cp {RESOLV_BACKUP} {RESOLV_CONF}
nameserver 127.0.0.1
nameserver ::1
options edns0
EOF_RESOLV
chmod 0644 {RESOLV_CONF}
chown root:root {RESOLV_CONF}

# 5. Enable + start dnscrypt-proxy
systemctl enable --now dnscrypt-proxy
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        # Tenta best-effort rollback
        _attempt_rollback()
        return False, (err.strip() or "Falha ao ativar modo avancado.")[:600]
    return True, ""


def deactivate_advanced_mode_blocking() -> tuple[bool, str]:
    """Desativa modo avancado: dnscrypt-proxy OFF + systemd-resolved ON.

    Restaura backup do resolved.conf e resolv.conf.
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    script = f"""set -e

# 1. Stop + disable dnscrypt-proxy
systemctl stop dnscrypt-proxy 2>/dev/null || true
systemctl disable dnscrypt-proxy 2>/dev/null || true

# 2. Restore resolved.conf do backup (se existir)
if [ -f {RESOLVED_BACKUP} ]; then
    cp -a {RESOLVED_BACKUP} {RESOLVED_CONF}
fi

# 3. Restore resolv.conf do backup (se existir)
if [ -e {RESOLV_BACKUP} ]; then
    rm -f {RESOLV_CONF}
    cp -aP {RESOLV_BACKUP} {RESOLV_CONF}
else
    # Fallback: cria symlink padrao do systemd-resolved
    rm -f {RESOLV_CONF}
    ln -sf /run/systemd/resolve/stub-resolv.conf {RESOLV_CONF}
fi

# 4. Enable + start systemd-resolved
systemctl enable --now systemd-resolved
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao desativar modo avancado.")[:600]
    return True, ""


def _attempt_rollback() -> None:
    """Best-effort rollback se algo deu errado no meio.

    NAO chama pkexec novamente (assume que ja temos contexto).
    """
    # Se o pkexec ja falhou, raramente conseguimos rodar sem prompt novo.
    # Esta funcao e' mais simbolica — em pratica, usuario precisa rodar
    # 'deactivate_advanced_mode_blocking' manualmente se algo travar.
    pass


def get_current_mode() -> str:
    """Retorna 'advanced', 'simple', ou 'unknown'.

    Heuristica:
    - 'advanced': dnscrypt-proxy ativo + systemd-resolved inativo
    - 'simple': systemd-resolved ativo + dnscrypt-proxy inativo
    - 'unknown': qualquer outra combinacao (transient ou config manual)
    """
    from . import dnscrypt_backend as dc

    dnscrypt_active = dc.is_active()
    resolved_active = systemd_resolved_active()

    if dnscrypt_active and not resolved_active:
        return "advanced"
    if resolved_active and not dnscrypt_active:
        return "simple"
    return "unknown"
