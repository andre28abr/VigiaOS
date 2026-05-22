"""Janela principal com painel de toggles agrupados por categoria."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .toggles import ALL_TOGGLES
from .toggles.base import Toggle


class VigiaPrivacyWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Privacy Controls")
        self.set_default_size(720, 600)

        # Layout: HeaderBar + ScrolledWindow com PreferencesPage agrupando toggles
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._build_content())
        self.set_content(toolbar)

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(
            title="Privacy Controls",
            subtitle="Vigia Suite",
        )
        header.set_title_widget(title)
        # Menu button (About/Quit) virá na v0.2; por ora sem
        return header

    def _build_content(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()

        # Agrupa toggles por categoria
        groups: dict[str, list[Toggle]] = {}
        for tog in ALL_TOGGLES:
            groups.setdefault(tog.category, []).append(tog)

        for category, items in groups.items():
            group = Adw.PreferencesGroup()
            group.set_title(category)
            for tog in items:
                row = self._build_toggle_row(tog)
                group.add(row)
            page.add(group)

        # Mensagem se nenhum toggle estiver disponivel
        if not ALL_TOGGLES:
            empty = Adw.StatusPage(
                title="Nenhum toggle disponivel",
                description="Verifique se o GNOME esta instalado e schemas dconf estao presentes.",
                icon_name="dialog-warning-symbolic",
            )
            return empty

        return page

    def _build_toggle_row(self, tog: Toggle) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(tog.name)
        row.set_subtitle(tog.description)

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)

        if not tog.is_available():
            # Toggle indisponivel — mostra row dimmed, switch desabilitado
            row.set_sensitive(False)
            row.set_subtitle(
                f"{tog.description}\n[indisponivel neste sistema]"
            )
        else:
            switch.set_active(tog.is_enabled())
            switch.connect("state-set", self._on_toggle, tog)

        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        return row

    def _on_toggle(self, switch: Gtk.Switch, value: bool, tog: Toggle) -> bool:
        """Callback do switch — aplica mudanca no sistema."""
        try:
            tog.set_enabled(value)
        except Exception as e:
            # Reverte switch se falhou
            switch.set_state(not value)
            self._show_error(tog, str(e))
            # True = "I handled state-set, do not propagate default behavior"
            return True
        # Confirma estado (sincroniza visual com sistema)
        switch.set_state(value)
        return True

    def _show_error(self, tog: Toggle, message: str) -> None:
        dlg = Adw.AlertDialog(
            heading=f"Falha em '{tog.name}'",
            body=message,
        )
        dlg.add_response("ok", "OK")
        dlg.present(self)
