"""Aba Fontes: explica cada log padrão do Fedora + botão 'ver só este'."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import detect_available_sources
from ..glossary import SOURCES_INFO


class SourcesTab(Adw.Bin):
    """Cartões explicando os logs do sistema, com 'ver só este na Timeline'.

    `on_focus(code)` é chamado quando o usuário pede pra focar numa fonte —
    o controller troca pra aba Timeline e filtra por ela.
    """

    def __init__(self, on_focus=None) -> None:
        super().__init__()
        self._on_focus = on_focus

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        group.set_title("Logs do sistema")
        group.set_description(
            "De onde vêm os eventos. Cada log do Fedora guarda um tipo de "
            "informação — aqui está o que é cada um e quando vale a pena olhar."
        )

        available = detect_available_sources()
        for info in SOURCES_INFO:
            row = Adw.ExpanderRow()
            row.set_title(info.label)
            row.set_subtitle(info.what)
            row.add_prefix(Gtk.Image.new_from_icon_name(info.icon))

            if info.code not in available:
                tag = Gtk.Label(label="indisponível neste PC")
                tag.add_css_class("caption")
                tag.add_css_class("dim-label")
                tag.set_valign(Gtk.Align.CENTER)
                row.add_suffix(tag)

            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            body.set_margin_start(12)
            body.set_margin_end(12)
            body.set_margin_top(8)
            body.set_margin_bottom(8)

            when = Gtk.Label()
            when.set_markup(f"<b>Quando olhar aqui:</b> {info.when}")
            when.set_xalign(0)
            when.set_wrap(True)
            body.append(when)

            btn = Gtk.Button(label="Ver só este na Timeline")
            btn.set_halign(Gtk.Align.START)
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_click, info.code)
            body.append(btn)

            brow = Adw.PreferencesRow()
            brow.set_child(body)
            brow.set_activatable(False)
            row.add_row(brow)
            group.add(row)

        page.add(group)
        self.set_child(page)

    def _on_click(self, _btn: Gtk.Button, code: str) -> None:
        if self._on_focus is not None:
            self._on_focus(code)
