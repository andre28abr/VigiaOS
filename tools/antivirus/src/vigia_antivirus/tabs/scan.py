"""Tab Scan: escolhe alvo, roda clamscan com progress streaming.

Em v0.1.1 absorveu o que era a aba Status — banner no topo mostra
estado essencial do ClamAV (idade da base de dados, daemon ativo).
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402

from vigia_common.notifications import PRIORITY_HIGH, notify_if_unfocused

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

        # ------------------------------------------------------------
        # Banner de estado (idade da base + ClamAV instalado?)
        # ------------------------------------------------------------
        self._status_banner = Adw.Banner()
        self._status_banner.set_revealed(False)
        # Adw.Banner por design fica colado nas bordas — colocamos
        # acima do clamp para ocupar largura inteira.

        # ------------------------------------------------------------
        # Header
        # ------------------------------------------------------------
        header_lbl = Gtk.Label(label="Scan on-demand")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label(
            label=(
                "Escolha um alvo e clique <i>Iniciar scan</i>. O scan roda em "
                "background e o progresso aparece em tempo real na "
                "<i>Saida do scan</i> — arquivos limpos em verde, "
                "ameacas em vermelho.\n\n"
                "Verifique periodicamente a aba <i>Base de dados</i> para "
                "manter as assinaturas atualizadas (recomendado 1x/semana)."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ------------------------------------------------------------
        # Target selector
        # ------------------------------------------------------------
        target_group = Adw.PreferencesGroup()
        target_group.set_title("Alvo do scan")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_text(str(Path.home()))
        self._target_entry.set_placeholder_text("Caminho a escanear")
        self._target_entry.set_hexpand(True)

        choose_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        choose_btn.set_tooltip_text("Escolher pasta")
        choose_btn.set_valign(Gtk.Align.CENTER)
        choose_btn.connect("clicked", lambda _b: self._open_chooser())

        target_row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        target_row_box.append(self._target_entry)
        target_row_box.append(choose_btn)

        target_action_row = Adw.ActionRow(title="Caminho")
        target_action_row.add_suffix(target_row_box)
        target_group.add(target_action_row)

        # Preset chips
        chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
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

        # ------------------------------------------------------------
        # Run / Stop
        # ------------------------------------------------------------
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(16)
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

        # Status / progress line
        self._status_label = Gtk.Label(label="Pronto.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(4)
        self._status_label.set_margin_bottom(16)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # ------------------------------------------------------------
        # Saida do scan (terminal — streaming colorido + auto-scroll)
        # ------------------------------------------------------------
        log_expander = Adw.ExpanderRow()
        log_expander.set_title("Saida do scan")
        log_expander.set_subtitle("Output do clamscan em tempo real")
        log_expander.set_expanded(True)

        self._log_view = Gtk.TextView()
        self._log_view.set_editable(False)
        self._log_view.set_cursor_visible(False)
        self._log_view.set_monospace(True)
        self._log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._log_view.set_top_margin(8)
        self._log_view.set_bottom_margin(8)
        self._log_view.set_left_margin(8)
        self._log_view.set_right_margin(8)
        self._log_buf = self._log_view.get_buffer()

        self._tag_ok = self._log_buf.create_tag(
            "ok", foreground="#4ade80", weight=Pango.Weight.BOLD,
        )
        self._tag_infected = self._log_buf.create_tag(
            "infected", foreground="#f87171", weight=Pango.Weight.BOLD,
        )
        self._tag_summary = self._log_buf.create_tag(
            "summary", foreground="#fbbf24", weight=Pango.Weight.BOLD,
        )

        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_min_content_height(240)
        log_scrolled.set_max_content_height(380)
        log_scrolled.set_child(self._log_view)

        log_row = Adw.ActionRow()
        log_row.set_child(log_scrolled)
        log_row.set_activatable(False)
        log_expander.add_row(log_row)

        log_group = Adw.PreferencesGroup()
        log_group.set_margin_top(16)
        log_group.add(log_expander)

        # ------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(28)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(target_group)
        inner.append(action_box)
        inner.append(self._status_label)
        inner.append(log_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))

        # Banner fica fora do clamp para usar largura total
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._status_banner)
        outer.append(scrolled)
        self.set_child(outer)

        # Carrega estado da base ao montar
        self._refresh_status_banner()

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
    # Status banner (idade da base + sanity checks)
    # ============================================================

    def _refresh_status_banner(self) -> None:
        """Atualiza banner no topo com idade da base / instalacao."""
        threading.Thread(target=self._status_worker, daemon=True).start()

    def _status_worker(self) -> None:
        installed = backend.clamav_installed()
        info = backend.get_db_info() if installed else backend.DbInfo()
        age = backend.db_age_days(info) if installed else None
        GLib.idle_add(self._apply_status_banner, installed, info, age)

    def _apply_status_banner(self, installed: bool, info, age) -> bool:
        if not installed:
            self._status_banner.set_title(
                "ClamAV nao instalado. "
                "Instale via: rpm-ostree install clamav clamav-update"
            )
            self._status_banner.set_revealed(True)
            self._run_btn.set_sensitive(False)
            return False

        # Instalado — verifica idade da base
        if age is None:
            self._status_banner.set_title(
                "Base de assinaturas: idade desconhecida. "
                "Atualize na aba 'Base de dados' antes do primeiro scan."
            )
            self._status_banner.set_revealed(True)
        elif age > 14:
            self._status_banner.set_title(
                f"Base de assinaturas desatualizada ha {age} dias. "
                "Va a 'Base de dados' e atualize."
            )
            self._status_banner.set_revealed(True)
        elif age > 7:
            self._status_banner.set_title(
                f"Base com {age} dias. Considere atualizar na aba 'Base de dados'."
            )
            self._status_banner.set_revealed(True)
        else:
            # Tudo bem — esconde o banner
            self._status_banner.set_revealed(False)

        return False

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
        self._append_log_line(line)
        return False

    def _append_log_line(self, line: str) -> None:
        """Insere uma linha no terminal com coloracao + auto-scroll.

        - Linha com ' FOUND' (ameaca) → vermelho inteiro.
        - Arquivo limpo (': OK') → caminho neutro + 'OK' verde.
        - 'Infected files: N' do sumario → verde se 0, vermelho se >0.
        - Cabecalho 'SCAN SUMMARY' → amber.
        """
        end = self._log_buf.get_end_iter()
        stripped = line.strip()

        if " FOUND" in line:
            self._log_buf.insert_with_tags(end, line + "\n", self._tag_infected)
        elif stripped.endswith(": OK"):
            head = line[: line.rfind("OK")]
            self._log_buf.insert(end, head)
            self._log_buf.insert_with_tags(
                self._log_buf.get_end_iter(), "OK\n", self._tag_ok
            )
        elif stripped.startswith("Infected files:"):
            tag = self._tag_ok if stripped.endswith(": 0") else self._tag_infected
            self._log_buf.insert_with_tags(end, line + "\n", tag)
        elif "SCAN SUMMARY" in line:
            self._log_buf.insert_with_tags(end, line + "\n", self._tag_summary)
        else:
            self._log_buf.insert(end, line + "\n")

        self._scroll_to_end()

    def _scroll_to_end(self) -> None:
        """Empurra a barra de rolagem pro final (auto-scroll do terminal)."""
        mark = self._log_buf.create_mark(None, self._log_buf.get_end_iter(), False)
        self._log_view.scroll_to_mark(mark, 0, False, 0, 0)
        self._log_buf.delete_mark(mark)

    def _on_done(self, result: backend.ScanResult) -> bool:
        self._running = False
        self._set_running_ui(False)

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            self._append_summary_line(
                f"\n══ Erro: {result.error[:120]} ══", self._tag_infected
            )
            return False

        if result.infected_files > 0:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{result.scanned_files} arquivos escaneados, "
                f"{result.infected_files} INFECTADO(S)."
            )
            self._append_summary_line(
                f"\n══ {result.infected_files} INFECTADO(S) ══",
                self._tag_infected,
            )
            notify_if_unfocused(
                f"Antivirus: {result.infected_files} infectado(s)",
                f"{result.scanned_files} arquivos escaneados. "
                "Abra o Vigia pra ver os detalhes.",
                notif_id="vigia-antivirus-scan",
                priority=PRIORITY_HIGH,
            )
        else:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{result.scanned_files} arquivos escaneados, nada suspeito."
            )
            self._append_summary_line("\n══ Nada suspeito ══", self._tag_ok)
            notify_if_unfocused(
                "Antivirus: nada suspeito",
                f"{result.scanned_files} arquivos escaneados em "
                f"{result.elapsed_sec}s.",
                notif_id="vigia-antivirus-scan",
            )

        return False

    def _append_summary_line(self, text: str, tag) -> None:
        """Linha-resumo colorida garantida no final do terminal."""
        end = self._log_buf.get_end_iter()
        self._log_buf.insert_with_tags(end, text + "\n", tag)
        self._scroll_to_end()
