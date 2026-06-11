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


# ============================================================
# Tema "Terminal" (hacker) — opcional, via Gtk.CssProvider
# ============================================================

UI_THEMES: tuple[str, ...] = ("padrao", "terminal")

# Paleta extraída do mockup: fundo quase-preto, verde-neon, monospace. Recolore
# o libadwaita pelos *named colors* (o framework propaga pra árvore inteira) +
# força dark + fonte mono. Reversível: remover o provider volta ao adwaita.
TERMINAL_CSS = """
@define-color window_bg_color    #0B0F10;
@define-color window_fg_color    #CFF7DA;
@define-color view_bg_color      #0E1416;
@define-color view_fg_color      #CFF7DA;
@define-color headerbar_bg_color #0A0E0F;
@define-color headerbar_fg_color #39E75F;
@define-color sidebar_bg_color   #0A0E0F;
@define-color sidebar_fg_color   #CFF7DA;
@define-color card_bg_color      #111A1C;
@define-color popover_bg_color   #0E1416;
@define-color dialog_bg_color    #0E1416;
@define-color accent_bg_color    #1E8A4C;
@define-color accent_color       #39E75F;
@define-color accent_fg_color    #04130A;
@define-color destructive_color  #FF5C7A;
@define-color success_color      #39E75F;
@define-color error_color        #FF5C7A;
@define-color warning_color      #F2C744;

/* monospace em tudo — é o ponto do tema */
* {
  font-family: "JetBrains Mono", "Cascadia Code", "Fira Code",
               "DejaVu Sans Mono", monospace;
}

/* títulos/headings e bolinhas de status em verde-neon */
.title-1, .title-2, .title-3, .title-4, .heading, .caption-heading {
  color: #39E75F;
}
label.success { color: #39E75F; }
label.error   { color: #FF5C7A; }
"""

_terminal_provider = None  # Gtk.CssProvider (lazy)


def _get_terminal_provider():
    """Cria (uma vez) o CssProvider do tema terminal."""
    global _terminal_provider
    if _terminal_provider is None:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        p = Gtk.CssProvider()
        try:
            p.load_from_string(TERMINAL_CSS)          # GTK 4.12+
        except AttributeError:
            p.load_from_data(TERMINAL_CSS.encode("utf-8"))  # fallback
        _terminal_provider = p
    return _terminal_provider


# Cores de marca dos produtos no rail (ícones simbólicos tingidos, estilo flat).
_RAIL_CSS = """
.vigia-rail-hub  { color: #2ec27e; }
.vigia-rail-red  { color: #ef4444; }
.vigia-rail-blue { color: #3b82f6; }
"""

_base_provider = None


def apply_base_css() -> None:
    """Aplica (1×) o CSS-base do VigiaOS: cores de marca dos ícones do rail
    (Hub verde, Red vermelho, Blue azul). Independe do tema. Idempotente."""
    global _base_provider
    if _base_provider is not None:
        return
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gdk, Gtk
    except (ValueError, ImportError):
        return
    display = Gdk.Display.get_default()
    if display is None:
        return
    p = Gtk.CssProvider()
    try:
        p.load_from_string(_RAIL_CSS)                  # GTK 4.12+
    except AttributeError:
        p.load_from_data(_RAIL_CSS.encode("utf-8"))    # fallback
    Gtk.StyleContext.add_provider_for_display(
        display, p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    _base_provider = p


def apply_ui_theme(name: str) -> None:
    """Aplica o tema visual ao vivo (reversível):

    - "padrao":   adwaita seguindo o tema do GNOME (remove o provider terminal).
    - "terminal": hacker — dark forçado + verde-neon + monospace.
    """
    name = name if name in UI_THEMES else "padrao"
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gdk, Gtk
    except (ValueError, ImportError):
        return

    display = Gdk.Display.get_default()
    sm = Adw.StyleManager.get_default()
    prio = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION

    if name == "terminal":
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, _get_terminal_provider(), prio)
    else:
        if display is not None and _terminal_provider is not None:
            Gtk.StyleContext.remove_provider_for_display(
                display, _terminal_provider)
        sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
