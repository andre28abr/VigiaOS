"""Autenticacao via Polkit pro lock do Hub.

Conceito:
- Polkit ('PolicyKit') e' o framework do Linux pra autorizacao baseada
  em senha do user/admin
- Define 'actions' em XML em /usr/share/polkit-1/actions/ ou
  /etc/polkit-1/actions/
- App chama check_authorization(action_id) que mostra dialog de senha
  se nao autorizado ainda na sessao

Vantagem vs. senha customizada:
- ZERO armazenamento de credencial (LGPD friendly)
- Reusa senha admin do sistema (PAM) — user nao memoriza outra senha
- Native, robusta, com auditoria via journal

Fluxo:
1. Hub starts -> if settings.password_lock and not authorized yet:
   - check_auth() -> Polkit prompt aparece
   - User digita senha sudo
   - Authorized -> Hub abre normal
   - Cancelado/errou -> Hub fecha (app.quit())

2. Action ID: br.com.vigia.Hub.unlock

3. .policy file e' instalado em /etc/polkit-1/actions/ via pkexec na
   primeira vez que o user liga o switch. Em pacotes RPM/COPR isso
   vai automatico pra /usr/share/polkit-1/actions/.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


# ============================================================
# Constantes
# ============================================================

ACTION_ID = "br.com.vigia.Hub.unlock"

# Paths possiveis onde o .policy pode estar (ordem de prioridade)
POLICY_DIRS = [
    Path("/usr/share/polkit-1/actions"),   # System RPM (futuro COPR)
    Path("/etc/polkit-1/actions"),         # Local override (dev/pip install)
]

POLICY_FILENAME = "br.com.vigia.Hub.policy"

# Path onde a gente INSTALA (writeable mediante pkexec)
INSTALL_TARGET = Path("/etc/polkit-1/actions") / POLICY_FILENAME


# ============================================================
# .policy XML — definicao da action
# ============================================================


def policy_xml() -> str:
    """XML do Polkit action.

    <defaults> com auth_admin -> sempre exige senha admin.
    <allow_active>auth_admin</allow_active> = mesmo session ativa
    precisa autenticar.

    Em GNOME, o prompt mostra a mensagem em <message> traduzida.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>

  <vendor>VigiaOS</vendor>
  <vendor_url>https://github.com/andre28abr/VigiaOS</vendor_url>

  <action id="{ACTION_ID}">
    <description>Abrir o Vigia Hub</description>
    <description xml:lang="pt_BR">Abrir o Vigia Hub</description>
    <message>Autenticacao necessaria para abrir o Vigia Hub</message>
    <message xml:lang="pt_BR">Autenticacao necessaria para abrir o Vigia Hub</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin</allow_active>
    </defaults>
  </action>

</policyconfig>
"""


# ============================================================
# Instalacao do .policy
# ============================================================


def is_policy_installed() -> bool:
    """True se o .policy esta instalado em qualquer um dos paths."""
    for d in POLICY_DIRS:
        if (d / POLICY_FILENAME).is_file():
            return True
    return False


def installed_policy_path() -> Optional[Path]:
    """Retorna o path onde o .policy esta instalado, ou None."""
    for d in POLICY_DIRS:
        p = d / POLICY_FILENAME
        if p.is_file():
            return p
    return None


def install_policy() -> tuple[bool, str]:
    """Instala o .policy em /etc/polkit-1/actions/ via pkexec.

    Estrategia: cria arquivo temp com o XML, depois pkexec install
    pra mover (preserva permissoes/owner root:root). Apos copia,
    espera ate 5s o polkitd reconhecer a action — alguns sistemas
    nao tem inotify watch nos action dirs.
    """
    try:
        # Cria temp file com o XML
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".policy",
            prefix="vigia-hub-",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(policy_xml())
            tmp_path = Path(f.name)
        os.chmod(tmp_path, 0o644)

        # pkexec install -m 0644 -o root -g root SRC DEST
        # 'install' e' GNU coreutils, cuida de mode/owner num so cmd
        cmd = [
            "pkexec",
            "install",
            "-m", "0644",
            "-o", "root",
            "-g", "root",
            "-D",  # cria diretorios pai se nao existem
            str(tmp_path),
            str(INSTALL_TARGET),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        # Limpa temp
        try:
            tmp_path.unlink()
        except OSError:
            pass

        if result.returncode != 0:
            err = result.stderr.strip() or f"pkexec retornou {result.returncode}"
            return (False, err)

        # Espera ate 5s pelo polkitd reconhecer a nova action
        if not wait_for_polkit_recognition(ACTION_ID, timeout=5.0):
            return (
                False,
                "O arquivo foi instalado, mas o servico polkitd nao "
                "reconheceu a action em ate 5 segundos. Tente desligar "
                "e religar o switch (geralmente resolve), ou reinicie "
                "o servico: sudo systemctl restart polkit",
            )

        return (True, "")
    except (OSError, subprocess.SubprocessError) as e:
        return (False, str(e))


def wait_for_polkit_recognition(action_id: str, timeout: float = 5.0) -> bool:
    """Espera o polkitd reconhecer a action recem-instalada.

    Usa `pkaction --action-id <id>` em loop ate retornar exit 0 ou
    timeout. Resolve a race condition entre `install` do .policy e
    o inotify do polkitd.
    """
    if not shutil.which("pkaction"):
        # Sem pkaction nao da pra verificar — assume que vai funcionar
        return True

    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["pkaction", "--action-id", action_id],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        time.sleep(0.2)
    return False


def uninstall_policy() -> tuple[bool, str]:
    """Remove o .policy via pkexec. Nao falha se ja' nao existe."""
    target = INSTALL_TARGET
    if not target.exists():
        return (True, "")  # ja' removido
    try:
        result = subprocess.run(
            ["pkexec", "rm", "-f", str(target)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return (True, "")
        return (False, result.stderr.strip() or f"exit {result.returncode}")
    except (OSError, subprocess.SubprocessError) as e:
        return (False, str(e))


# ============================================================
# Autorizacao
# ============================================================


def check_auth(action_id: str = ACTION_ID) -> tuple[bool, str]:
    """Roda check_authorization do Polkit.

    Retorna (autorizado, error_msg).
    Mostra dialog de senha se o user nao esta autorizado ainda.
    Bloqueia ate user responder.
    """
    try:
        import gi
        gi.require_version("Polkit", "1.0")
        from gi.repository import Polkit
    except (ValueError, ImportError) as e:
        return (False, f"Polkit nao disponivel: {e}")

    try:
        authority = Polkit.Authority.get_sync()
        subject = Polkit.UnixProcess.new_for_owner(
            os.getpid(), 0, os.getuid()
        )
        result = authority.check_authorization_sync(
            subject,
            action_id,
            None,
            Polkit.CheckAuthorizationFlags.ALLOW_USER_INTERACTION,
            None,
        )
        if result.get_is_authorized():
            return (True, "")
        if result.get_is_challenge():
            # User cancelou ou errou senha
            return (False, "Autenticacao cancelada ou senha incorreta.")
        return (False, "Acesso negado pelo Polkit.")
    except Exception as e:  # pylint: disable=broad-except
        return (False, f"Erro Polkit: {e}")


def polkit_available() -> bool:
    """True se a lib Python do Polkit esta disponivel."""
    try:
        import gi
        gi.require_version("Polkit", "1.0")
        from gi.repository import Polkit  # noqa: F401
        return True
    except (ValueError, ImportError):
        return False
