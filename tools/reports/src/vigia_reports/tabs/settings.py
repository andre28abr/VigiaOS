"""Tab Configurações: identidade do escritório (branding) nos relatórios."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import config

_LOGO_HINT = "Nenhum (PNG, JPG ou SVG, até 512 KB)"


class SettingsTab(Adw.Bin):
    """Edita ~/.config/vigia/reports.json — nome, subtítulo, responsável, logo."""

    def __init__(self) -> None:
        super().__init__()
        self._cfg = config.load_config()

        page = Adw.PreferencesPage()

        group = Adw.PreferencesGroup(
            title="Identidade do escritório",
            description=(
                "Aparece no cabeçalho e no rodapé de todos os relatórios gerados. "
                "Deixe em branco para usar o padrão Vigia."
            ),
        )

        self._name = Adw.EntryRow(title="Nome do escritório")
        self._name.set_text(self._cfg["org_name"])
        self._name.connect("changed", self._on_changed)
        group.add(self._name)

        self._subtitle = Adw.EntryRow(title="Subtítulo (ex: OAB/SP · São Paulo)")
        self._subtitle.set_text(self._cfg["org_subtitle"])
        self._subtitle.connect("changed", self._on_changed)
        group.add(self._subtitle)

        self._responsible = Adw.EntryRow(title="Responsável técnico")
        self._responsible.set_text(self._cfg["responsible"])
        self._responsible.connect("changed", self._on_changed)
        group.add(self._responsible)

        self._logo_row = Adw.ActionRow(title="Logo")
        self._logo_row.set_subtitle(self._cfg["logo_path"] or _LOGO_HINT)
        pick = Gtk.Button(label="Escolher…")
        pick.set_valign(Gtk.Align.CENTER)
        pick.connect("clicked", self._on_pick_logo)
        clear = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        clear.set_valign(Gtk.Align.CENTER)
        clear.add_css_class("flat")
        clear.set_tooltip_text("Remover logo")
        clear.connect("clicked", self._on_clear_logo)
        self._logo_row.add_suffix(pick)
        self._logo_row.add_suffix(clear)
        group.add(self._logo_row)

        page.add(group)

        info = Adw.PreferencesGroup()
        info_row = Adw.ActionRow(
            title="Onde fica salvo",
            subtitle="~/.config/vigia/reports.json (0600). Vale no próximo relatório gerado.",
        )
        info_row.set_activatable(False)
        info.add(info_row)
        page.add(info)

        self.set_child(page)

    # ============================================================
    # Persistência
    # ============================================================

    def _on_changed(self, _row: Adw.EntryRow) -> None:
        self._save()

    def _save(self) -> None:
        self._cfg["org_name"] = self._name.get_text()
        self._cfg["org_subtitle"] = self._subtitle.get_text()
        self._cfg["responsible"] = self._responsible.get_text()
        config.save_config(self._cfg)  # logo_path já mora em self._cfg

    # ============================================================
    # Logo (Gtk.FileDialog assíncrono)
    # ============================================================

    def _on_pick_logo(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolher logo")
        filt = Gtk.FileFilter()
        filt.set_name("Imagens")
        for pat in ("*.png", "*.jpg", "*.jpeg", "*.svg", "*.gif", "*.webp"):
            filt.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filt)
        dialog.set_filters(filters)
        dialog.open(self.get_root(), None, self._on_logo_chosen)

    def _on_logo_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except Exception:  # pylint: disable=broad-except
            return  # usuário cancelou
        path = f.get_path() if f is not None else None
        if path:
            self._cfg["logo_path"] = path
            self._logo_row.set_subtitle(path)
            self._save()

    def _on_clear_logo(self, _btn: Gtk.Button) -> None:
        self._cfg["logo_path"] = ""
        self._logo_row.set_subtitle(_LOGO_HINT)
        self._save()
