"""Tab Scan: roda clamscan com streaming colorido num terminal.

Sem pasta escolhida faz varredura do sistema todo ("/"); o botao de
pasta restringe a um diretorio. Banner no topo mostra estado essencial
do ClamAV (idade da base de dados). Estatisticas (escaneados/infectados/
tempo) atualizam ao vivo, espelhando o Rootkit Scanner.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402

from vigia_common.notifications import PRIORITY_HIGH, notify_if_unfocused
from vigia_common.platform import install_hint

from .. import backend
from ._helpers import make_clamp, show_error


HEADER_DESC = (
    "<b>ClamAV</b> e' um antivirus open-source que detecta virus, trojans, "
    "malware e ransomware por assinatura. O scan roda em background e o "
    "progresso aparece em tempo real na <i>Saida do scan</i> — arquivos "
    "limpos em verde, ameacas em vermelho.\n\n"
    "Sem pasta selecionada faz uma <b>varredura completa do sistema</b>. "
    "Use o botao de pasta pra escanear so um diretorio. Mantenha a base de "
    "assinaturas atualizada na aba <i>Base de dados</i> (recomendado "
    "1x/semana)."
)


class ScanTab(Adw.Bin):
    """Roda clamscan (pasta escolhida ou sistema todo) com terminal colorido."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._stop_requested = False
        self._scan_path: str | None = None  # None = varredura do sistema todo ("/")
        self._scanned_live = 0
        self._infected_live = 0

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
        header_lbl = Gtk.Label(label="ClamAV")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label()
        header_desc.set_markup(HEADER_DESC)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ------------------------------------------------------------
        # Run / Stop / escolher pasta
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

        self._folder_btn = Gtk.Button.new_from_icon_name("folder-open-symbolic")
        self._folder_btn.set_tooltip_text(
            "Escolher pasta para escanear (vazio = sistema todo)"
        )
        self._folder_btn.connect("clicked", lambda _b: self._open_chooser())
        action_box.append(self._folder_btn)

        # Status / progress line
        self._status_label = Gtk.Label()
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_margin_top(4)
        self._status_label.set_margin_bottom(16)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)
        self._status_label.set_label(f"Pronto — alvo: {self._target_desc()}")

        # ------------------------------------------------------------
        # Estatisticas (mesmo pattern do Rootkit Scanner)
        # ------------------------------------------------------------
        kpis_group = Adw.PreferencesGroup()
        kpis_group.set_margin_top(8)
        kpis_group.set_title("Estatisticas")

        self._row_scanned = Adw.ActionRow(title="Arquivos escaneados")
        self._row_scanned.add_css_class("property")
        self._lbl_scanned = Gtk.Label(label="—")
        self._lbl_scanned.add_css_class("monospace")
        self._row_scanned.add_suffix(self._lbl_scanned)
        kpis_group.add(self._row_scanned)

        self._row_infected = Adw.ActionRow(title="Infectados")
        self._row_infected.add_css_class("property")
        self._lbl_infected = Gtk.Label(label="—")
        self._lbl_infected.add_css_class("monospace")
        self._row_infected.add_suffix(self._lbl_infected)
        kpis_group.add(self._row_infected)

        self._row_elapsed = Adw.ActionRow(title="Tempo decorrido")
        self._row_elapsed.add_css_class("property")
        self._lbl_elapsed = Gtk.Label(label="—")
        self._lbl_elapsed.add_css_class("monospace")
        self._row_elapsed.add_suffix(self._lbl_elapsed)
        kpis_group.add(self._row_elapsed)

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
        inner.append(action_box)
        inner.append(self._status_label)
        inner.append(kpis_group)
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
            if folder and folder.get_path():
                self._scan_path = folder.get_path()
                self._status_label.set_label(f"Pronto — alvo: {self._target_desc()}")
        except GLib.Error:
            pass  # user cancelou

    def _target_desc(self) -> str:
        """Texto human-readable do alvo atual (pasta escolhida ou sistema todo)."""
        return self._scan_path if self._scan_path else "sistema completo (/)"

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
                "Instale via: " + install_hint("clamav", "clamav-update")
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
        if not backend.clamav_installed():
            show_error(
                self,
                "ClamAV nao instalado",
                "Instale com: " + install_hint("clamav", "clamav-update"),
            )
            return

        target = self._scan_path or "/"

        self._running = True
        self._stop_requested = False
        self._scanned_live = 0
        self._infected_live = 0
        self._log_buf.set_text("")
        self._lbl_scanned.set_label("0")
        self._lbl_infected.set_label("0")
        self._lbl_elapsed.set_label("—")
        self._set_label_color(self._lbl_infected, "")
        self._set_running_ui(True)
        if self._scan_path:
            self._status_label.set_label(f"Escaneando {target}...")
        else:
            self._status_label.set_label(
                "Escaneando o sistema completo (/) — pode demorar bastante..."
            )

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
        self._folder_btn.set_sensitive(not running)

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

        - Linha com ' FOUND' (ameaca) → vermelho inteiro + conta infectado.
        - Arquivo limpo (': OK') → caminho neutro + 'OK' verde + conta scan.
        - 'Infected files: N' do sumario → verde se 0, vermelho se >0.
        - Cabecalho 'SCAN SUMMARY' → amber.
        """
        end = self._log_buf.get_end_iter()
        stripped = line.strip()

        if " FOUND" in line:
            self._log_buf.insert_with_tags(end, line + "\n", self._tag_infected)
            self._infected_live += 1
            self._scanned_live += 1
            self._lbl_infected.set_label(str(self._infected_live))
            self._set_label_color(self._lbl_infected, "error")
            self._lbl_scanned.set_label(str(self._scanned_live))
        elif stripped.endswith(": OK"):
            head = line[: line.rfind("OK")]
            self._log_buf.insert(end, head)
            self._log_buf.insert_with_tags(
                self._log_buf.get_end_iter(), "OK\n", self._tag_ok
            )
            self._scanned_live += 1
            self._lbl_scanned.set_label(str(self._scanned_live))
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

        # Stats finais: usa o summary do clamscan quando disponivel, senao
        # mantem a contagem ao vivo (ex: scan cancelado no meio).
        scanned = result.scanned_files or self._scanned_live
        infected = max(result.infected_files, self._infected_live)
        self._lbl_scanned.set_label(str(scanned))
        self._lbl_infected.set_label(str(infected))
        self._lbl_elapsed.set_label(f"{result.elapsed_sec}s")
        self._set_label_color(self._lbl_infected, "error" if infected > 0 else "")

        if result.error:
            if "cancelad" in result.error.lower():
                self._status_label.set_label("Scan cancelado pelo usuario.")
                self._append_summary_line("\n══ Scan cancelado ══", self._tag_summary)
            else:
                self._status_label.set_label(f"Erro: {result.error}")
                self._append_summary_line(
                    f"\n══ Erro: {result.error[:120]} ══", self._tag_infected
                )
            return False

        if infected > 0:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{scanned} arquivos escaneados, {infected} INFECTADO(S)."
            )
            self._append_summary_line(
                f"\n══ {infected} INFECTADO(S) ══", self._tag_infected,
            )
            notify_if_unfocused(
                f"Antivirus: {infected} infectado(s)",
                f"{scanned} arquivos escaneados. Abra o Vigia pra ver os detalhes.",
                notif_id="vigia-antivirus-scan",
                priority=PRIORITY_HIGH,
            )
        else:
            self._status_label.set_label(
                f"Scan concluido em {result.elapsed_sec}s. "
                f"{scanned} arquivos escaneados, nada suspeito."
            )
            self._append_summary_line("\n══ Nada suspeito ══", self._tag_ok)
            notify_if_unfocused(
                "Antivirus: nada suspeito",
                f"{scanned} arquivos escaneados em {result.elapsed_sec}s.",
                notif_id="vigia-antivirus-scan",
            )

        return False

    def _append_summary_line(self, text: str, tag) -> None:
        """Linha-resumo colorida garantida no final do terminal."""
        end = self._log_buf.get_end_iter()
        self._log_buf.insert_with_tags(end, text + "\n", tag)
        self._scroll_to_end()

    @staticmethod
    def _set_label_color(label: Gtk.Label, level: str) -> None:
        for cls in ("success", "warning", "error"):
            label.remove_css_class(cls)
        if level:
            label.add_css_class(level)
