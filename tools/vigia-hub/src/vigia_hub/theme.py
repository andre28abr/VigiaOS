"""Integracao com o tema do GNOME (Adw.StyleManager).

v0.6.4: REMOVIDA opcao de tema customizado (light/dark forcado). Hub
sempre segue o tema escolhido pelo usuario nas Configuracoes do GNOME.

Helpers:
- follow_system_theme(): garante que Adw esta em ColorScheme.DEFAULT
  (segue sistema)
- is_dark_mode(): True se Adw esta renderizando em dark agora

Mudanca de tema em tempo real e' suportada via signal 'notify::dark'
da Adw.StyleManager (conectar do lado do consumer — ex: window.py
re-renderiza WebKit quando tema muda).
"""

from __future__ import annotations


def follow_system_theme() -> None:
    """Configura Adw pra sempre seguir o tema do GNOME (DEFAULT).

    Idempotente; pode ser chamado em todo do_activate.
    """
    try:
        import gi
        gi.require_version("Adw", "1")
        from gi.repository import Adw
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.DEFAULT
        )
    except (ValueError, ImportError):
        pass


def is_dark_mode() -> bool:
    """True se Adw esta renderizando em dark agora.

    Reflete a preferencia atual do GNOME (Configuracoes > Aparencia).
    """
    try:
        import gi
        gi.require_version("Adw", "1")
        from gi.repository import Adw
        return bool(Adw.StyleManager.get_default().get_dark())
    except (ValueError, ImportError):
        return False


# Mantido por backwards compat (window.py / app.py podem importar).
# normalize_mode aceita qualquer string; sempre retorna "system" agora.
def normalize_mode(_raw: str) -> str:
    return "system"


def apply_theme(_mode: str = "system") -> None:
    """Backwards-compat shim: agora sempre segue sistema."""
    follow_system_theme()


VALID_MODES: tuple[str, ...] = ("system",)
