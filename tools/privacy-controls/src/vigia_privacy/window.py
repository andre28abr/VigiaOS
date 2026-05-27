"""Janela principal com painel de toggles agrupados por categoria.

Suporta dois modos:
- Standalone (vigia-privacy via CLI): VigiaPrivacyWindow envolve build_content()
- Embedded (dentro do Vigia Hub): Hub chama build_content() diretamente
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import WRAPPED_PACKAGES
from .about import AboutTab
from .toggles import ALL_TOGGLES
from .toggles.base import Toggle


def _make_pkg_badges_bar() -> Gtk.Widget:
    """Sub-bar com badges dos pacotes 'wrapped' (mostrada abaixo do header).

    Em vez de pack_end no header (que apertava as tabs quando muitas),
    vira uma subheader bar via toolbar.add_top_bar() depois do header.
    """
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    bar.set_margin_start(12)
    bar.set_margin_end(12)
    bar.set_margin_top(4)
    bar.set_margin_bottom(4)

    intro = Gtk.Label(label="Wrapper de:")
    intro.add_css_class("caption")
    intro.add_css_class("dim-label")
    bar.append(intro)

    for pkg in WRAPPED_PACKAGES:
        pill = Gtk.Label(label=pkg)
        pill.add_css_class("monospace")
        pill.add_css_class("caption")
        pill.add_css_class("dim-label")
        bar.append(pill)

    return bar


# ============================================================
# API publica: build_content()
# ============================================================


def build_content() -> Gtk.Widget:
    """Constroi o conteudo principal: ViewStack com 2 abas (Toggles + Sobre).

    Retorna um Adw.ToolbarView pronto para ser:
    - content de uma Adw.ApplicationWindow (modo standalone)
    - embarcado num Gtk.Stack do Vigia Hub (modo embedded)
    """
    # ViewStack: 2 tabs
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_build_page(), "toggles", "Toggles", "preferences-system-symbolic")
    stack.add_titled_with_icon(AboutTab(), "about", "Sobre", "help-about-symbolic")

    # Switcher
    switcher = Adw.ViewSwitcher()
    switcher.set_stack(stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

    # Header
    header = Adw.HeaderBar()
    header.set_title_widget(switcher)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    if WRAPPED_PACKAGES:
        toolbar.add_top_bar(_make_pkg_badges_bar())
    toolbar.set_content(stack)
    return toolbar


# ============================================================
# Window standalone (wraps build_content)
# ============================================================


class VigiaPrivacyWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Privacy Controls")
        self.set_default_size(720, 600)
        self.set_content(build_content())


# ============================================================
# Builders internos
# ============================================================


def _build_page() -> Gtk.Widget:
    """Constroi a aba Toggles.

    v0.3.1: wrap em Adw.Bin pra garantir alignment correto. Sem o wrap,
    em janelas grandes (VM em fullscreen ou monitor wide) o PreferencesPage
    perdia centralizacao e ficava encostado num lado. AboutTab desta mesma
    tool ja seguia esse pattern (herda de Adw.Bin) — agora a aba Toggles
    bate.
    """
    if not ALL_TOGGLES:
        return Adw.StatusPage(
            title="Nenhum toggle disponivel",
            description="Verifique se o GNOME esta instalado e schemas dconf estao presentes.",
            icon_name="dialog-warning-symbolic",
        )

    page = Adw.PreferencesPage()

    groups: dict[str, list[Toggle]] = {}
    for tog in ALL_TOGGLES:
        groups.setdefault(tog.category, []).append(tog)

    for category, items in groups.items():
        group = Adw.PreferencesGroup()
        group.set_title(category)
        for tog in items:
            group.add(_build_toggle_row(tog))
        page.add(group)

    # Wrap em Adw.Bin pra alignment consistente (v0.3.1)
    container = Adw.Bin()
    container.set_child(page)
    return container


def _build_toggle_row(tog: Toggle) -> Adw.ActionRow:
    """Constroi row com switch em estado 'carregando' (sensitive=False).

    O estado real (`is_available()`, `is_enabled()`) e' coletado em thread
    em background e aplicado via _apply_toggle_state. Isso evita rodar
    `systemctl is-active` × 3 + `bluetoothctl show` no UI thread durante init.
    """
    row = Adw.ActionRow()
    row.set_title(tog.name)
    row.set_subtitle(tog.description)

    switch = Gtk.Switch()
    switch.set_valign(Gtk.Align.CENTER)
    switch.set_sensitive(False)  # ate o worker retornar
    row.add_suffix(switch)
    row.set_activatable_widget(switch)

    # Coleta estado em thread
    threading.Thread(
        target=_toggle_state_worker, args=(switch, row, tog), daemon=True
    ).start()
    return row


def _toggle_state_worker(switch: Gtk.Switch, row: Adw.ActionRow, tog: Toggle) -> None:
    try:
        available = tog.is_available()
        enabled = tog.is_enabled() if available else False
    except Exception:  # pylint: disable=broad-except
        available, enabled = False, False
    GLib.idle_add(_apply_toggle_state, switch, row, tog, available, enabled)


def _apply_toggle_state(
    switch: Gtk.Switch,
    row: Adw.ActionRow,
    tog: Toggle,
    available: bool,
    enabled: bool,
) -> bool:
    if not available:
        row.set_sensitive(False)
        row.set_subtitle(f"{tog.description}\n[indisponivel neste sistema]")
        return False
    switch.set_active(enabled)
    switch.set_sensitive(True)
    switch.connect("state-set", _on_toggle, tog)
    return False


def _on_toggle(switch: Gtk.Switch, value: bool, tog: Toggle) -> bool:
    """Callback do switch — aplica em thread (set_enabled pode rodar pkexec)."""
    switch.set_sensitive(False)
    threading.Thread(
        target=_apply_toggle_worker, args=(switch, value, tog), daemon=True
    ).start()
    return True  # block default — vamos setar state via idle_add


def _apply_toggle_worker(switch: Gtk.Switch, value: bool, tog: Toggle) -> None:
    try:
        tog.set_enabled(value)
        err = None
    except Exception as e:  # pylint: disable=broad-except
        err = str(e)
    GLib.idle_add(_on_apply_done, switch, value, tog, err)


def _on_apply_done(
    switch: Gtk.Switch, value: bool, tog: Toggle, err: str | None
) -> bool:
    switch.set_sensitive(True)
    if err is not None:
        switch.set_state(not value)
        _show_error(switch, tog, err)
    else:
        switch.set_state(value)
    return False


def _show_error(widget: Gtk.Widget, tog: Toggle, message: str) -> None:
    """Mostra dialog de erro. Usa get_root() pra funcionar tanto em standalone
    quanto embarcado no Hub."""
    dlg = Adw.AlertDialog(
        heading=f"Falha em '{tog.name}'",
        body=message,
    )
    dlg.add_response("ok", "OK")
    win = widget.get_root()
    if win is not None:
        dlg.present(win)
