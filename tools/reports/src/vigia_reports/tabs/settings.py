"""Tab Configurações: identidade do escritório (branding) nos relatórios."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import config, renderer, scheduler
from ._helpers import show_error

_LOGO_HINT = "Nenhum (PNG, JPG ou SVG, até 512 KB)"


class SettingsTab(Adw.Bin):
    """Identidade do escritório + agendamento automático dos relatórios."""

    def __init__(self) -> None:
        super().__init__()
        self._cfg = config.load_config()
        self._sched_busy = False

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

        # ---- Agendamento automático ---- #
        sched_group = Adw.PreferencesGroup(
            title="Agendamento automático",
            description=(
                "Gera um relatório sozinho todo mês (dia 1, 9h) e salva na "
                "Biblioteca. A trilha de auditoria LGPD se monta sem você "
                "precisar lembrar. Use um modelo que não peça senha "
                "(Conformidade LGPD ou Saúde do sistema)."
            ),
        )
        self._sched_ids = [tid for tid, _, _ in renderer.list_templates()]
        names = Gtk.StringList.new([name for _, name, _ in renderer.list_templates()])
        self._sched_combo = Adw.ComboRow(title="Modelo do relatório mensal")
        self._sched_combo.set_model(names)
        cur = scheduler.scheduled_model()
        default = cur if cur in self._sched_ids else "lgpd_compliance"
        self._sched_combo.set_selected(
            self._sched_ids.index(default) if default in self._sched_ids else 0
        )
        self._sched_combo.connect("notify::selected", self._on_sched_model_changed)
        sched_group.add(self._sched_combo)

        self._sched_switch = Adw.SwitchRow(
            title="Gerar automaticamente todo mês",
            subtitle="Cria um timer do systemd no seu usuário (sem senha).",
        )
        self._sched_switch.set_active(scheduler.is_enabled())
        self._sched_switch.connect("notify::active", self._on_sched_toggled)
        sched_group.add(self._sched_switch)
        page.add(sched_group)

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

    # ============================================================
    # Agendamento (systemd user timer)
    # ============================================================

    def _selected_sched_model(self) -> str:
        i = self._sched_combo.get_selected()
        if 0 <= i < len(self._sched_ids):
            return self._sched_ids[i]
        return self._sched_ids[0]

    def _on_sched_toggled(self, switch: Adw.SwitchRow, _pspec) -> None:
        if self._sched_busy:  # ignora o set_active de reversão
            return
        if switch.get_active():
            ok, msg = scheduler.enable_schedule(self._selected_sched_model(), 30)
        else:
            ok, msg = scheduler.disable_schedule()
        if not ok:
            self._sched_busy = True
            switch.set_active(not switch.get_active())  # reverte visualmente
            self._sched_busy = False
            show_error(self, "Falha no agendamento", msg or "Erro desconhecido.")

    def _on_sched_model_changed(self, _combo, _pspec) -> None:
        # Se já está ligado, re-aplica o timer com o novo modelo.
        if self._sched_switch.get_active() and not self._sched_busy:
            scheduler.enable_schedule(self._selected_sched_model(), 30)
