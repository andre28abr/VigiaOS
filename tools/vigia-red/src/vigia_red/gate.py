"""Portão de termo de uso reusável pelos módulos do VigiaRed.

Todo módulo ofensivo passa por aqui: na 1ª vez exibe o termo (Lei 12.737/2012);
aceito UMA vez (`vigia_red.consent`), destrava TODOS os módulos do Red. GTK fica
só aqui — `consent.py` continua puro/testável.

Uso no módulo:
    from ... import gate
    def build_content():
        return gate.build_gated(_build_tool)   # _build_tool() -> Gtk.Widget
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from . import consent  # noqa: E402

_TERM_TEXT = (
    "Os módulos do VigiaRed fazem teste de invasão (pentest). Use somente "
    "contra <b>sistemas próprios</b> ou com <b>autorização formal por "
    "escrito</b>.\n\n"
    "Módulos <b>passivos</b> (ex.: Recon) só leem fontes públicas; módulos "
    "<b>ativos</b> (ex.: Network Scanner) <b>tocam no alvo</b>. Acesso não "
    "autorizado a dispositivos é crime no Brasil (<b>Lei 12.737/2012</b>). "
    "Você é o único responsável pelo uso desta ferramenta."
)


def build_gated(build_tool: Callable[[], Gtk.Widget]) -> Gtk.Widget:
    """Termo (1ª vez) → ferramenta. `build_tool` só é chamado após o aceite."""
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    def _mount_tool() -> None:
        if stack.get_child_by_name("tool") is None:
            stack.add_named(build_tool(), "tool")
        stack.set_visible_child_name("tool")

    if consent.is_accepted():
        _mount_tool()
    else:
        stack.add_named(_build_consent_gate(_mount_tool), "gate")
        stack.set_visible_child_name("gate")
    return stack


def _build_consent_gate(on_accept: Callable[[], None]) -> Gtk.Widget:
    status = Adw.StatusPage()
    status.set_icon_name("dialog-warning-symbolic")
    status.set_title("Antes de começar — termo de uso")

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    box.set_halign(Gtk.Align.CENTER)
    box.set_size_request(540, -1)

    notice = Gtk.Label()
    notice.set_markup(_TERM_TEXT)
    notice.set_wrap(True)
    notice.set_xalign(0)
    notice.set_max_width_chars(60)
    box.append(notice)

    check = Gtk.CheckButton()
    check_lbl = Gtk.Label(
        label="Li e concordo: só vou usar contra sistemas próprios ou com "
              "autorização formal por escrito.")
    check_lbl.set_wrap(True)
    check_lbl.set_xalign(0)
    check_lbl.set_max_width_chars(56)
    check.set_child(check_lbl)
    box.append(check)

    btn = Gtk.Button(label="Aceitar e continuar")
    btn.add_css_class("suggested-action")
    btn.add_css_class("pill")
    btn.set_halign(Gtk.Align.CENTER)
    btn.set_sensitive(False)
    check.connect("toggled", lambda c: btn.set_sensitive(c.get_active()))

    def _accept(_b):
        consent.accept()
        on_accept()

    btn.connect("clicked", _accept)
    box.append(btn)
    status.set_child(box)

    header = Adw.HeaderBar()
    header.set_title_widget(
        Adw.WindowTitle(title="VigiaRed", subtitle="Termo de uso"))
    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(status)
    return tv
