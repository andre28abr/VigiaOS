"""Tab Scan: escolhe alvo, roda clamscan com progress streaming."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error


# Presets de alvo comum (path + label)
TARGET_PRESETS: list[tuple[str, str, str]] = [
    ("home", "Home (~/)", str(Path.home())),
    ("downloads", "Downloads", str(Path.home() / "Downloads")),
    ("documents", "Documents", str(Path.home() / "Documents")),
    ("tmp", "/tmp", "/tmp"),
]


class ScanTab(Adw.Bin):
    """Escolhe alvo + roda clamscan + mostra findings em tempo real."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._stop_requested = False
        self._current_findings: list[backend.Finding] = []

        # Header
        header_lbl = Gtk.Label(label="Scan on-demand")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Escolha um alvo e clique Iniciar. Scan roda em background; "
                "findings aparecem na lista abaixo conforme detectados."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Target selector
        target_group = Adw.PreferencesGroup()
        target_group.set_title("Alvo do scan")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_text(str(Path.home()))
        self._target_entry.set_placeholder_text("Caminho a escanear")
        self._target_entry.set_hexpand(True)

        choose_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        choose_btn.set_tooltip_text("Escolher pasta")
        choose_btn.connect("clicked", lambda _b: self._open_chooser())

        target_row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        target_row_box.append(self._target_entry)
        target_row_box.append(choose_btn)

        target_action_row = Adw.ActionRow(title="Caminho")
        target_action_row.add_suffix(target_row_box)
        target_group.add(target_action_row)

        # Preset chips
        chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chip_box.set_margin_top(4)
        chip_box.set_margin_bottom(4)
        chip_box.set_halign(Gtk.Align.START)
        chip_box.append(Gtk.Label(label="Atalhos:"))
        for _key, label, path in TARGET_PRESETS:
            btn = Gtk.Button(label=label)
            btn.add_css_class("pill")
            btn.add_css_class("flat")
            btn.connect("clicked", lambda _b, p=path: self._target_entry.set_text(p))
            chip_box.append(btn)

        preset_row = Adw.ActionRow()
        preset_row.set_child(chip_box)
        preset_row.set_activatable(False)
        target_group.add(preset_row)

        # Run / Stop
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)

        self._run_btn = Gtk.Button(label="Iniciar scan")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", lambda _b: self._start_scan())
        action_box.append(self._run_btn)

        self._stop_btn = Gtk.Button(label="Parar")
        self._stop_btn.add_css_class("destructive-action")
        self._stop_btn.set_sensitive(False)
        self._stop_btn.connect("clicked", lambda _b: self._request_stop())
        action_box.append(self._stop_btn)

        # Status bar
        self._status_label = Gtk.Label(label="Pronto.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(4)
        self._status_label.set_margin_bottom(8)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # Findings group
        self._findings_group = Adw.PreferencesGroup()
        self._findings_group.set_title("Findings")
        self._findings_group.set_description(
            "Arquivos suspeitos detectados durante o scan"
        )
        self._findings_rows: list = []
        self._render_findings()

        # Log group (linhas brutas — collapsable via expander)
        log_expander = Adw.ExpanderRow()
        log_expander.set_title("Log do scan")
        log_expander.set_subtitle("Output bruto do clamscan")

        self._log_view = Gtk.TextView()
        self._log_view.set_editable(False)
        self._log_view.set_monospace(True)
        self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._log_view.set_top_margin(8)
        self._log_view.set_bottom_margin(8)
        self._log_view.set_left_margin(8)
        self._log_view.set_right_margin(8)
        self._log_buf = self._log_view.get_buffer()

        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(200)
        log_scrolled.set_max_content_height(280)
        log_scrolled.set_child(self._log_view)

        log_row = Adw.ActionRow()
        log_row.set_child(log_scrolled)
        log_row.set_activatable(False)
        log_expander.add_row(log_row)

        log_group = Adw.PreferencesGroup()
        log_group.add(log_expander)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(target_group)
        outer.append(action_box)
        outer.append(self._status_label)
        outer.append(self._findings_group)
        outer.append(log_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    # ============================================================
    # File chooser
    # ============================================================

    def _open_chooser(self) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title("Escolher pasta para escanear")
        dlg.select_folder(self.get_root(), None, self._on_folder_selected)

    def _on_folder_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._target_entry.set_text(folder.get_path() or "")
        except GLib.Error:
            pass  # user cancelou

    # ============================================================
    # Scan lifecycle
    # ============================================================

    def _start_scan(self) -> None:
        if self._running:
            return

        target = self._target_entry.get_text().strip()
        if not target:
            show_error(self, "Sem alvo", "Informe um caminho.")
            return
        if not Path(target).exists():
            show_error(self, "Caminho nao existe", f"Nao encontrei: {target}")
            return
        if not backend.clamav_installed():
            show_error(
                self,
                "ClamAV nao instalado",
                "Instale com: rpm-ostree install clamav clamav-update && reboot",
            )
            return

        self._running = True
        self._stop_requested = False
        self._current_findings = []
        self._render_findings()
        self._log_buf.set_text("")
        self._set_running_ui(True)
        self._status_label.set_label(f"Escaneando {target}...")

        backend.scan_async(
            path=target,
            on_line=self._on_line_threadsafe,
            on_done=self._on_done_threadsafe,
            stop_flag=lambda: self._stop_requested,
        )

    def _request_stop(self) -> None:
        if not self._running:
            return
        self._stop_requested = True
        self._status_label.set_label("Cancelando...")

    def _set_running_ui(self, running: bool) -> None:
        self._run_btn.set_sensitive(not running)
        self._stop_btn.set_sensitive(running)
        self._target_entry.set_sensitive(not running)

    # ============================================================
    # Worker callbacks (chamados na thread do backend — usar GLib.idle_add)
    # ============================================================

    def _on_line_threadsafe(self, line: str) -> None:
        GLib.idle_add(self._on_line, line)

    def _on_done_threadsafe(self, result: backend.ScanResult) -> None:
        GLib.idle_add(self._on_done, result)

    def _on_line(self, line: str) -> bool:
        # Append no log
        end = self._log_buf.get_end_iter()
        self._log_buf.insert(end, line + "\n")

        # Se for finding, adiciona na lista
        if " FOUND" in line and ":" in line:
            path, _, rest = line.rpartition(":")
            signature = rest.replace("FOUND", "").strip()
            self._current_findings.append(backend.Finding(path=path.strip(), signature=signature))
            self._render_findings()

        return False

    def _on_done(self, result: backend.ScanResult) -> bool:
        self._running = False
        self._set_running_ui(False)

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            return False

        # Atualiza com finding list canonica do parser do summary
        self._current_findings = result.findings
        self._render_findings()

        if result.infected_files > 0:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{result.scanned_files} arquivos escaneados, "
                f"{result.infected_files} INFECTADO(S). Veja findings abaixo."
            )
        else:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{result.scanned_files} arquivos escaneados, nada suspeito."
            )

        return False

    # ============================================================
    # Findings render
    # ============================================================

    def _render_findings(self) -> None:
        for r in self._findings_rows:
            self._findings_group.remove(r)
        self._findings_rows = []

        if not self._current_findings:
            row = Adw.ActionRow(title="Nenhum finding")
            row.set_subtitle("Lista vazia significa que nada suspeito foi detectado.")
            row.add_css_class("dim-label")
            self._findings_group.add(row)
            self._findings_rows.append(row)
            return

        for f in self._current_findings:
            row = Adw.ActionRow(title=f.signature)
            row.set_subtitle(f.path)
            row.set_subtitle_lines(2)
            row.add_css_class("property")

            badge = Gtk.Label(label="!")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class("error")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_prefix(badge)

            self._findings_group.add(row)
            self._findings_rows.append(row)
