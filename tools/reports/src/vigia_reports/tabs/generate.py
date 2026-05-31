"""Tab Gerar: formulario com template + periodo + modo admin + botao 'Gerar'."""

from __future__ import annotations

import subprocess
import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gio, Gtk  # noqa: E402

from .. import backend, renderer
from ._helpers import make_clamp, show_error


PERIOD_OPTIONS = [
    ("últimas 24 horas", 1),
    ("últimos 7 dias", 7),
    ("últimos 30 dias", 30),
    ("últimos 90 dias", 90),
]


class GenerateTab(Adw.Bin):
    """Form para gerar um novo relatorio."""

    def __init__(self, on_report_generated: Callable[[], None]) -> None:
        super().__init__()
        self._on_report_generated = on_report_generated
        self._running = False
        self._pulse_id: int | None = None
        self._templates = renderer.list_templates()  # [(id, name, desc)]

        # ---- Template group ---- #
        tpl_group = Adw.PreferencesGroup()
        tpl_group.set_title("Modelo do relatório")
        tpl_group.set_description("Escolha o que será consolidado no documento.")

        tpl_strings = Gtk.StringList.new([f"{name}" for _, name, _ in self._templates])
        self._tpl_combo = Adw.ComboRow(title="Modelo")
        self._tpl_combo.set_model(tpl_strings)
        self._tpl_combo.set_selected(0)
        self._tpl_combo.connect("notify::selected", self._on_template_changed)
        tpl_group.add(self._tpl_combo)

        self._tpl_desc_row = Adw.ActionRow()
        self._tpl_desc_row.set_subtitle(self._templates[0][2])
        self._tpl_desc_row.add_css_class("property")
        self._tpl_desc_row.set_activatable(False)
        tpl_group.add(self._tpl_desc_row)

        # ---- Periodo group ---- #
        period_group = Adw.PreferencesGroup()
        period_group.set_margin_top(24)
        period_group.set_title("Período")
        period_group.set_description("Janela de tempo a consolidar.")

        period_strings = Gtk.StringList.new([label for label, _ in PERIOD_OPTIONS])
        self._period_combo = Adw.ComboRow(title="Janela de tempo")
        self._period_combo.set_model(period_strings)
        self._period_combo.set_selected(1)  # 7 dias por padrao
        period_group.add(self._period_combo)

        # ---- Coleta group ---- #
        collect_group = Adw.PreferencesGroup()
        collect_group.set_margin_top(24)
        collect_group.set_title("Coleta")
        collect_group.set_description(
            "Modo admin usa pkexec para acessar journal do sistema e histórico btmp "
            "(logins falhados). Sem modo admin, alguns dados ficam incompletos."
        )

        self._admin_switch = Adw.SwitchRow(
            title="Modo admin",
            subtitle="Usar pkexec para coleta completa (será pedida a senha)",
        )
        self._admin_switch.set_active(False)
        collect_group.add(self._admin_switch)

        # ---- Action group ---- #
        action_group = Adw.PreferencesGroup()
        action_group.set_margin_top(24)
        action_row = Adw.ActionRow(title="Gerar relatório")
        action_row.set_subtitle("HTML será salvo em ~/.local/share/vigia-reports/")
        self._generate_btn = Gtk.Button(label="Gerar")
        self._generate_btn.add_css_class("suggested-action")
        self._generate_btn.set_valign(Gtk.Align.CENTER)
        self._generate_btn.connect("clicked", self._on_generate_clicked)
        action_row.add_suffix(self._generate_btn)
        action_group.add(action_row)

        # Progress (escondido)
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_box.set_visible(False)
        self._progress_box.set_margin_top(16)
        self._progress_label = Gtk.Label(label="Coletando dados...")
        self._progress_label.add_css_class("dim-label")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_box.append(self._progress_label)
        self._progress_box.append(self._progress_bar)

        # ---- Layout ---- #
        page = Adw.PreferencesPage()
        page.add(tpl_group)
        page.add(period_group)
        page.add(collect_group)
        page.add(action_group)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(page)
        outer.append(self._progress_box)

        self.set_child(make_clamp(outer))

    # ============================================================
    # Handlers
    # ============================================================

    def _on_template_changed(self, _combo, _pspec) -> None:
        idx = self._tpl_combo.get_selected()
        if 0 <= idx < len(self._templates):
            self._tpl_desc_row.set_subtitle(self._templates[idx][2])

    def _on_generate_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return

        tpl_idx = self._tpl_combo.get_selected()
        period_idx = self._period_combo.get_selected()
        if tpl_idx < 0 or period_idx < 0:
            return

        template_id = self._templates[tpl_idx][0]
        period_days = PERIOD_OPTIONS[period_idx][1]
        elevated = self._admin_switch.get_active()

        self._set_running(True, "Coletando dados...")
        threading.Thread(
            target=self._worker,
            args=(template_id, period_days, elevated),
            daemon=True,
        ).start()

    def _worker(self, template_id: str, period_days: int, elevated: bool) -> None:
        try:
            period = backend.make_period(period_days)
            GLib.idle_add(self._update_progress, "Coletando journal...")

            if template_id == "activity_overview":
                data = backend.collect_for_activity_overview(period, elevated=elevated)
            elif template_id == "auth_events":
                data = backend.collect_for_auth_events(period, elevated=elevated)
            elif template_id == "executive_summary":
                data = backend.collect_for_executive_summary(period, elevated=elevated)
            elif template_id == "admin_access":
                data = backend.collect_for_admin_access(period, elevated=elevated)
            elif template_id == "lgpd_compliance":
                data = backend.collect_for_lgpd_compliance(period, elevated=elevated)
            else:
                raise ValueError(f"Template não suportado: {template_id}")

            GLib.idle_add(self._update_progress, "Renderizando HTML...")

            html = renderer.render_html(template_id, data)
            output_dir = backend.ensure_reports_dir()
            path = renderer.write_report(html, template_id, output_dir)

            GLib.idle_add(self._on_done_success, str(path))
        except Exception as e:  # pylint: disable=broad-except
            GLib.idle_add(self._on_done_error, str(e))

    def _update_progress(self, label: str) -> bool:
        self._progress_label.set_label(label)
        return False

    def _on_done_success(self, path: str) -> bool:
        self._set_running(False)
        self._on_report_generated()
        # Abrir no navegador automaticamente
        try:
            Gio.AppInfo.launch_default_for_uri(f"file://{path}", None)
        except Exception:
            try:
                subprocess.Popen(["xdg-open", path])
            except Exception:
                pass
        return False

    def _on_done_error(self, msg: str) -> bool:
        self._set_running(False)
        show_error(self, "Falha ao gerar relatório", msg)
        return False

    def _set_running(self, running: bool, label: str = "Trabalhando...") -> None:
        self._running = running
        self._generate_btn.set_sensitive(not running)
        self._generate_btn.set_label("Gerando..." if running else "Gerar")
        self._progress_label.set_label(label)
        self._progress_box.set_visible(running)
        if running:
            self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        elif self._pulse_id is not None:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = None

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running
