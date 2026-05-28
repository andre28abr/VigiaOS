"""Autenticacao via pkexec pro lock do Hub (v0.5.9 — refatorado).

Abordagem antiga (v0.5.5-0.5.8) usava a lib Python Polkit direto:
- Polkit.Authority.get_sync() + check_authorization_sync()
- Instalava .policy file customizado em /etc/polkit-1/actions/
- check_authorization rodando em threading.Thread

PROBLEMAS DESCOBERTOS:
1. Polkit lib do PyGObject NAO e' thread-safe (deadlock D-Bus)
2. .policy custom precisa de pkexec pra instalar (UX ruim)
3. wait_for_polkit_recognition era frágil (timeout 5s nem sempre basta)

NOVA ABORDAGEM (v0.5.9):
- Usa `pkexec /usr/bin/true` (subprocess) — sem lib Polkit Python
- pkexec internamente chama o agente Polkit do sistema (nativo do GNOME)
- O agente mostra o dialog de senha
- Exit 0 = autenticado, exit 126 = cancelado, outros = erro
- Pra GTK app rodando: usa Gio.Subprocess (async no GMainLoop, sem threads)
- Pra startup do app (antes do main loop): subprocess.run sync (OK)
- ZERO necessidade de .policy custom — usa action default 'exec' que ja
  existe em qualquer sistema Polkit

VANTAGENS:
- Sem .policy pra instalar (UX +)
- Sem threads (sem deadlock D-Bus)
- Sem race condition de polkit recognition
- Codigo muito mais simples e robusto
"""

from __future__ import annotations

import subprocess
from typing import Callable


# Comando que dispara o prompt do Polkit. /usr/bin/true e' o no-op padrao.
# Polkit action invocada e' a default 'org.freedesktop.policykit.exec'.
PKEXEC_CMD = ["pkexec", "/usr/bin/true"]


# ============================================================
# Sync API — usado APENAS no startup do app (antes do GTK loop)
# ============================================================


def check_auth() -> tuple[bool, str]:
    """Versao sync — usar APENAS no do_activate inicial do app.

    Dentro de handlers do GTK (depois que main loop ta rodando),
    use check_auth_async(callback) pra nao bloquear UI.

    Retorna (autorizado, error_msg).
    """
    try:
        result = subprocess.run(
            PKEXEC_CMD,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min pro user digitar senha
        )
    except subprocess.TimeoutExpired:
        return (False, "Timeout aguardando senha (5 minutos).")
    except (OSError, FileNotFoundError) as e:
        return (False, f"pkexec nao encontrado: {e}")

    if result.returncode == 0:
        return (True, "")
    return (False, _format_pkexec_error(result.returncode, result.stderr))


def _format_pkexec_error(rc: int, stderr: str) -> str:
    """Mensagem amigavel baseada no exit code do pkexec."""
    stderr = stderr.strip()
    if rc == 126:
        return "Autenticacao cancelada ou senha incorreta."
    if rc == 127:
        return "pkexec nao encontrado no sistema."
    if stderr:
        return stderr
    return f"pkexec retornou codigo {rc}."


# ============================================================
# Async API — usado dentro do GTK main loop (handlers)
# ============================================================


def check_auth_async(callback: Callable[[bool, str], None]) -> None:
    """Versao async — usar em handlers do GTK pra nao bloquear UI.

    callback e' chamado com (autorizado: bool, error_msg: str)
    quando o pkexec termina. Roda no GMainLoop via Gio.Subprocess
    (sem threads, sem deadlock).
    """
    try:
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
    except (ValueError, ImportError) as e:
        callback(False, f"Gio nao disponivel: {e}")
        return

    try:
        proc = Gio.Subprocess.new(
            PKEXEC_CMD,
            Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_PIPE,
        )
    except GLib.Error as e:
        callback(False, f"Falha ao iniciar pkexec: {e.message}")
        return

    def on_complete(p, async_result, _user_data):
        # Le stderr pra mensagem de erro caso falhe
        try:
            success, _stdout, stderr_bytes = p.communicate_utf8_finish(async_result)
        except GLib.Error as e:
            callback(False, f"Erro pkexec: {e.message}")
            return

        if p.get_if_exited():
            rc = p.get_exit_status()
            if rc == 0:
                callback(True, "")
                return
            stderr = stderr_bytes or ""
            callback(False, _format_pkexec_error(rc, stderr))
            return

        # Killed por signal (incomum pra pkexec)
        callback(False, "pkexec terminou anormalmente.")

    proc.communicate_utf8_async(None, None, on_complete, None)


# ============================================================
# Util — checa se pkexec esta disponivel
# ============================================================


def pkexec_available() -> bool:
    """True se pkexec esta no PATH."""
    import shutil
    return shutil.which("pkexec") is not None
