"""Setup helpers — v0.3.0 (dnscrypt-only).

Antes da v0.3 esse arquivo era o "switch de modo" entre systemd-resolved
e dnscrypt-proxy. A v0.3 simplificou: dnscrypt-proxy e' o unico backend
suportado. Esse arquivo agora cobre apenas:

  1. `dnscrypt_active_ready()` — dnscrypt-proxy esta rodando E o
     sistema esta apontando pra ele (/etc/resolv.conf -> 127.0.0.1)?

  2. `ensure_dnscrypt_active_blocking()` — primeira ativacao apos
     install. Para systemd-resolved se estiver ativo, sobe dnscrypt-proxy,
     aponta resolv.conf. Faz backup do estado anterior pra rollback.

  3. `restore_systemd_resolved_blocking()` — caminho de "uninstall":
     desativa dnscrypt-proxy, restaura systemd-resolved + resolv.conf.
     Pra quem quer parar de usar o DNS Manager.

LGPD: backups com chmod 0600 (regra do projeto).
"""

from __future__ import annotations

import shutil
from pathlib import Path


RESOLVED_CONF = Path("/etc/systemd/resolved.conf")
RESOLVED_BACKUP = Path("/etc/systemd/resolved.conf.vigia-resolved-backup")
RESOLV_CONF = Path("/etc/resolv.conf")
RESOLV_BACKUP = Path("/etc/resolv.conf.vigia-resolved-backup")


# Subprocesso centralizado em vigia_common.proc.run (nunca levanta;
# timeout/binário ausente -> (1, "", "")). Aliased p/ não mexer nos callers.
from vigia_common.proc import run as _run


def has_resolved_backup() -> bool:
    """True se ja temos um backup do systemd-resolved (i.e. ja fizemos setup)."""
    return RESOLVED_BACKUP.exists()


def systemd_resolved_active() -> bool:
    """systemd-resolved esta running?"""
    if shutil.which("systemctl") is None:
        return False
    rc, _, _ = _run(
        ["systemctl", "is-active", "--quiet", "systemd-resolved"], timeout=5,
    )
    return rc == 0


def dnscrypt_active_ready() -> bool:
    """dnscrypt-proxy esta rodando E o sistema esta usando ele?

    Checks:
    1. systemctl is-active dnscrypt-proxy
    2. /etc/resolv.conf aponta pra 127.0.0.1 ou ::1

    Usado pelo onboarding pra decidir se mostra dialog 'Ativar agora'.
    """
    from . import dnscrypt_backend as dc

    if not dc.is_active():
        return False

    # Confere se resolv.conf aponta pra 127.0.0.1
    try:
        if RESOLV_CONF.is_symlink():
            target = str(RESOLV_CONF.resolve())
            # Pode ser stub-resolv.conf (que nao usa dnscrypt) — entao false
            if "systemd" in target:
                return False
        content = RESOLV_CONF.read_text(errors="replace")
        return "127.0.0.1" in content or "::1" in content
    except OSError:
        return False


def ensure_dnscrypt_active_blocking() -> tuple[bool, str]:
    """Ativa dnscrypt-proxy como backend DNS do sistema.

    Idempotente: se ja esta ativo, retorna ok sem fazer nada.

    Combina num so pkexec:
      1. Backup de /etc/systemd/resolved.conf (se existir e nao tiver backup)
      2. Backup de /etc/resolv.conf
      3. Stop + disable systemd-resolved (libera 127.0.0.53)
      4. Reescreve /etc/resolv.conf → nameserver 127.0.0.1
      5. Enable + start dnscrypt-proxy

    Backup files usam chmod 0600 (LGPD).
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    # Verifica se ja esta ativo (idempotencia)
    if dnscrypt_active_ready():
        return True, ""

    script = f"""set -e

# 1. Backup de resolved.conf (so primeira vez)
if [ -f {RESOLVED_CONF} ] && [ ! -f {RESOLVED_BACKUP} ]; then
    cp -a {RESOLVED_CONF} {RESOLVED_BACKUP}
    chmod 0600 {RESOLVED_BACKUP}
fi

# 2. Backup de resolv.conf (so primeira vez)
if [ -L {RESOLV_CONF} ] || [ -f {RESOLV_CONF} ]; then
    if [ ! -e {RESOLV_BACKUP} ]; then
        cp -aP {RESOLV_CONF} {RESOLV_BACKUP} 2>/dev/null || true
    fi
fi

# 3. Stop + disable systemd-resolved (libera porta 53)
systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true

# v0.4.1: garante /var/cache/dnscrypt-proxy/ existe (elimina warning
# 'Couldn't write cache file' no journal). Detecta user/group do unit
# file. Se vazio, default root.
DCS_USER=$(systemctl show dnscrypt-proxy -p User --value 2>/dev/null)
DCS_GROUP=$(systemctl show dnscrypt-proxy -p Group --value 2>/dev/null)
mkdir -p /var/cache/dnscrypt-proxy
if [ -n "$DCS_USER" ] && id "$DCS_USER" >/dev/null 2>&1; then
    chown "${{DCS_USER}}:${{DCS_GROUP:-$DCS_USER}}" /var/cache/dnscrypt-proxy 2>/dev/null || true
fi
chmod 0750 /var/cache/dnscrypt-proxy

# 4. Aponta /etc/resolv.conf pra 127.0.0.1 (dnscrypt-proxy)
rm -f {RESOLV_CONF}
cat > {RESOLV_CONF} << 'EOF_RESOLV'
# Gerenciado pelo Vigia DNS Manager v0.3+ (dnscrypt-proxy)
# Pra reverter, use 'Restaurar systemd-resolved padrao' no DNS Manager
# ou execute:
#   sudo cp {RESOLV_BACKUP} {RESOLV_CONF}
#   sudo systemctl enable --now systemd-resolved
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
        return False, "Autenticação cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao ativar dnscrypt-proxy.")[:600]
    return True, ""


def restore_systemd_resolved_blocking() -> tuple[bool, str]:
    """Caminho de uninstall: desativa dnscrypt-proxy, restaura systemd-resolved.

    Pra quem quer parar de usar o DNS Manager e voltar ao default Fedora.
    Nao desinstala o pacote dnscrypt-proxy (user pode preferir manter).

    Restaura:
    - /etc/systemd/resolved.conf (do backup)
    - /etc/resolv.conf (symlink pra stub-resolv.conf)
    - Para dnscrypt-proxy, sobe systemd-resolved
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    script = f"""set -e

# 1. Stop dnscrypt-proxy
systemctl stop dnscrypt-proxy 2>/dev/null || true
systemctl disable dnscrypt-proxy 2>/dev/null || true

# 2. Restore resolved.conf (se tiver backup)
if [ -f {RESOLVED_BACKUP} ]; then
    cp -a {RESOLVED_BACKUP} {RESOLVED_CONF}
fi

# 3. Restore resolv.conf (se tiver backup) OU recria symlink padrao
if [ -e {RESOLV_BACKUP} ]; then
    rm -f {RESOLV_CONF}
    cp -aP {RESOLV_BACKUP} {RESOLV_CONF}
else
    rm -f {RESOLV_CONF}
    ln -sf /run/systemd/resolve/stub-resolv.conf {RESOLV_CONF}
fi

# 4. Start systemd-resolved
systemctl enable --now systemd-resolved
"""
    rc, _, err = _run(["pkexec", "bash", "-c", script], timeout=30)
    if rc in (126, 127):
        return False, "Autenticação cancelada."
    if rc != 0:
        return False, (err.strip() or "Falha ao restaurar systemd-resolved.")[:600]
    return True, ""
