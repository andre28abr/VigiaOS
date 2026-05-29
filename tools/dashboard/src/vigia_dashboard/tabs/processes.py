"""Tab Processos: top processos com filtros + sort + kill."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend, proc_inspect
from ._helpers import make_clamp, show_error, show_info


REFRESH_MS = 2000  # 2s — processos nao precisam 1Hz
TOP_N = 30


SORT_OPTIONS = [
    ("cpu", "CPU"),
    ("mem", "Memoria"),
    ("io", "I/O (read+write)"),
    ("conn", "Conexoes ativas"),
    ("pid", "PID"),
    ("name", "Nome"),
]


class ProcessesTab(Adw.Bin):
    """Tabela de processos top N + filtros."""

    def __init__(self) -> None:
        super().__init__()
        self._tick_id: int = 0
        self._sort_by = "cpu"
        self._filter_user = ""
        self._filter_search = ""
        self._show_only_mine = False
        self._all_procs: list[backend.ProcessInfo] = []

        # ============================================================
        # Header
        # ============================================================
        header_lbl = Gtk.Label(label="Processos")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                f"Top {TOP_N} processos por padrao. Refresh a cada 2s. "
                "Killar processos que voce nao possui requer admin (pkexec)."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(20)

        # ============================================================
        # Filters toolbar
        # ============================================================
        filters_group = Adw.PreferencesGroup()
        filters_group.set_title("Filtros")

        # Search
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Buscar por nome ou comando...")
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search)
        search_row = Adw.ActionRow(title="Buscar")
        search_row.add_suffix(self._search_entry)
        filters_group.add(search_row)

        # Sort
        sort_combo = Gtk.DropDown.new_from_strings([name for _, name in SORT_OPTIONS])
        sort_combo.set_selected(0)  # CPU
        sort_combo.connect("notify::selected", self._on_sort_change)
        sort_row = Adw.ActionRow(title="Ordenar por")
        sort_row.add_suffix(sort_combo)
        filters_group.add(sort_row)

        # Filter "only mine"
        mine_switch = Adw.SwitchRow()
        mine_switch.set_title("Apenas meus processos")
        mine_switch.set_subtitle("Esconde processos de root e outros usuarios")
        mine_switch.set_active(False)
        mine_switch.connect("notify::active", self._on_mine_toggled)
        filters_group.add(mine_switch)

        # ============================================================
        # Process list
        # ============================================================
        self._procs_group = Adw.PreferencesGroup()
        self._procs_group.set_margin_top(28)
        self._procs_group.set_title("Processos")
        self._proc_rows: list = []

        self._status_lbl = Gtk.Label(label="Carregando...")
        self._status_lbl.add_css_class("dim-label")
        self._status_lbl.set_halign(Gtk.Align.START)
        self._status_lbl.set_xalign(0)
        self._status_lbl.set_margin_top(12)

        # ============================================================
        # Layout
        # ============================================================
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(filters_group)
        inner.append(self._procs_group)
        inner.append(self._status_lbl)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        self.set_child(scrolled)

        # Start
        self._refresh()
        self._tick_id = GLib.timeout_add(REFRESH_MS, self._refresh)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    # PERF: pause/resume usado por window.py
    def pause_tick(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def resume_tick(self) -> None:
        if self._tick_id == 0:
            self._refresh()
            self._tick_id = GLib.timeout_add(REFRESH_MS, self._refresh)

    # ============================================================
    # Filters callbacks
    # ============================================================

    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        self._filter_search = entry.get_text().strip().lower()
        self._render()

    def _on_sort_change(self, combo: Gtk.DropDown, *_args) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(SORT_OPTIONS):
            self._sort_by = SORT_OPTIONS[idx][0]
        self._render()

    def _on_mine_toggled(self, switch: Adw.SwitchRow, *_args) -> None:
        self._show_only_mine = switch.get_active()
        self._render()

    # ============================================================
    # Refresh
    # ============================================================

    def _refresh(self) -> bool:
        # Se o usuario tem uma linha expandida, NAO reconstroi a lista —
        # senao o rebuild (a cada 2s) colapsa a expansao e some com os
        # detalhes/botao Inspecionar antes do clique. Retoma o refresh
        # automaticamente quando tudo estiver fechado.
        if self._any_expanded():
            return True
        self._all_procs = backend.list_processes()
        self._render()
        return True

    def _any_expanded(self) -> bool:
        return any(
            isinstance(r, Adw.ExpanderRow) and r.get_expanded()
            for r in self._proc_rows
        )

    def _render(self) -> None:
        for r in self._proc_rows:
            self._procs_group.remove(r)
        self._proc_rows = []

        # Filter
        import os
        my_user = ""
        try:
            import pwd
            my_user = pwd.getpwuid(os.getuid()).pw_name
        except (KeyError, OSError):
            pass

        procs = self._all_procs

        if self._show_only_mine and my_user:
            procs = [p for p in procs if p.user == my_user]

        if self._filter_search:
            q = self._filter_search
            procs = [p for p in procs if q in p.comm.lower() or q in p.cmdline.lower()]

        # Sort
        if self._sort_by == "cpu":
            procs = sorted(procs, key=lambda p: p.cpu_pct, reverse=True)
        elif self._sort_by == "mem":
            procs = sorted(procs, key=lambda p: p.rss_kb, reverse=True)
        elif self._sort_by == "io":
            procs = sorted(procs, key=lambda p: p.read_mbs + p.write_mbs, reverse=True)
        elif self._sort_by == "conn":
            procs = sorted(
                procs,
                key=lambda p: p.n_tcp_established + p.n_tcp_listen + p.n_udp,
                reverse=True,
            )
        elif self._sort_by == "pid":
            procs = sorted(procs, key=lambda p: p.pid)
        elif self._sort_by == "name":
            procs = sorted(procs, key=lambda p: p.comm.lower())

        # Limit
        procs_shown = procs[:TOP_N]

        # Status line
        self._status_lbl.set_label(
            f"Mostrando {len(procs_shown)} de {len(self._all_procs)} processos · "
            f"refresh a cada {REFRESH_MS / 1000:.0f}s"
        )

        if not procs_shown:
            row = Adw.ActionRow(title="Nenhum processo")
            row.set_subtitle("Limpe os filtros para ver mais.")
            row.add_css_class("dim-label")
            self._procs_group.add(row)
            self._proc_rows.append(row)
            return

        # Render rows
        for p in procs_shown:
            row = self._build_row(p, my_user)
            self._procs_group.add(row)
            self._proc_rows.append(row)

    def _build_row(self, p: backend.ProcessInfo, my_user: str) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()
        row.set_title(p.comm)

        # Subtitle inclui I/O e conexoes se relevantes (v0.2)
        sub_bits = [
            f"PID {p.pid}",
            p.user,
            f"{p.cpu_pct:.1f}% CPU",
            backend.format_kb(p.rss_kb) + " RAM",
        ]
        io_total = p.read_mbs + p.write_mbs
        if io_total > 0.01:
            sub_bits.append(
                f"I/O {backend.format_mbps(p.read_mbs)}↓ {backend.format_mbps(p.write_mbs)}↑"
            )
        n_conn = p.n_tcp_established + p.n_tcp_listen + p.n_udp
        if n_conn > 0:
            sub_bits.append(f"{n_conn} conexao(oes)")
        row.set_subtitle(" · ".join(sub_bits))
        row.set_subtitle_lines(2)
        row.add_css_class("property")

        # CPU badge (prefix)
        cpu_badge = Gtk.Label(label=f"{p.cpu_pct:>5.1f}%")
        cpu_badge.add_css_class("monospace")
        cpu_badge.add_css_class("caption-heading")
        if p.cpu_pct > 50:
            cpu_badge.add_css_class("warning")
        elif p.cpu_pct > 10:
            cpu_badge.add_css_class("success")
        else:
            cpu_badge.add_css_class("dim-label")
        cpu_badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(cpu_badge)

        # Detail rows
        if p.cmdline and p.cmdline != p.comm:
            cmd_row = Adw.ActionRow(title="Comando completo")
            cmd_row.add_css_class("property")
            cmd_lbl = Gtk.Label(label=p.cmdline)
            cmd_lbl.add_css_class("monospace")
            cmd_lbl.add_css_class("caption")
            cmd_lbl.set_wrap(True)
            cmd_lbl.set_xalign(0)
            cmd_lbl.set_max_width_chars(80)
            cmd_row.add_suffix(cmd_lbl)
            row.add_row(cmd_row)

        state_row = Adw.ActionRow(title="Estado")
        state_row.add_css_class("property")
        state_human = {
            "R": "running", "S": "sleeping", "D": "disk wait",
            "Z": "zombie", "T": "stopped", "I": "idle",
        }.get(p.state, p.state)
        state_lbl = Gtk.Label(label=f"{p.state} ({state_human})")
        state_lbl.add_css_class("monospace")
        state_lbl.add_css_class("caption")
        state_row.add_suffix(state_lbl)
        row.add_row(state_row)

        # v0.2 — I/O row
        io_row = Adw.ActionRow(title="I/O em tempo real")
        io_row.add_css_class("property")
        io_row.set_subtitle("Bytes/s lidos/escritos vs leitura anterior")
        io_lbl = Gtk.Label(
            label=f"↓ {backend.format_mbps(p.read_mbs)} · ↑ {backend.format_mbps(p.write_mbs)}"
        )
        io_lbl.add_css_class("monospace")
        io_lbl.add_css_class("caption")
        io_row.add_suffix(io_lbl)
        row.add_row(io_row)

        # v0.2 — Conexoes row
        conn_row = Adw.ActionRow(title="Conexoes")
        conn_row.add_css_class("property")
        conn_row.set_subtitle(
            "TCP estabelecidas + TCP listening + UDP. Bytes/s "
            "por PID exigem eBPF (futuro)."
        )
        conn_lbl = Gtk.Label(
            label=(
                f"{p.n_tcp_established} EST · "
                f"{p.n_tcp_listen} LISTEN · "
                f"{p.n_udp} UDP"
            )
        )
        conn_lbl.add_css_class("monospace")
        conn_lbl.add_css_class("caption")
        conn_row.add_suffix(conn_lbl)
        row.add_row(conn_row)

        # Action row: kill buttons
        kill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        kill_box.set_halign(Gtk.Align.END)
        kill_box.set_margin_top(4)
        kill_box.set_margin_bottom(4)

        # Inspecionar (strace -c) — so' se o strace estiver instalado.
        if proc_inspect.strace_installed():
            inspect_btn = Gtk.Button(label="Inspecionar")
            inspect_btn.set_tooltip_text(
                "Rastreia as syscalls por ~5s e mostra um resumo (strace -c)"
            )
            inspect_btn.connect(
                "clicked", lambda _b, pid=p.pid: self._do_inspect(pid)
            )
            kill_box.append(inspect_btn)

        term_btn = Gtk.Button(label="Terminar (SIGTERM)")
        term_btn.connect("clicked", lambda _b, pid=p.pid: self._do_kill(pid, term=True))
        kill_box.append(term_btn)

        force_btn = Gtk.Button(label="Forcar (SIGKILL)")
        force_btn.add_css_class("destructive-action")
        force_btn.connect("clicked", lambda _b, pid=p.pid: self._do_kill(pid, term=False))
        kill_box.append(force_btn)

        kill_row = Adw.ActionRow(title="Acoes")
        kill_row.add_suffix(kill_box)
        row.add_row(kill_row)

        return row

    # ============================================================
    # Kill
    # ============================================================

    def _do_kill(self, pid: int, term: bool = True) -> None:
        import signal
        sig = signal.SIGTERM if term else signal.SIGKILL
        action = "Terminar" if term else "Forcar morte de"

        # Dialog de confirmacao
        proc = next((p for p in self._all_procs if p.pid == pid), None)
        proc_label = f"PID {pid}"
        if proc:
            proc_label = f"{proc.comm} (PID {pid}, user {proc.user})"

        dlg = Adw.AlertDialog(
            heading=f"{action} {proc_label}?",
            body=(
                "Esta acao envia o sinal "
                f"{'SIGTERM (graceful)' if term else 'SIGKILL (forcado, sem cleanup)'}.\n\n"
                "Se for processo de outro usuario ou do sistema, vai pedir "
                "senha admin (pkexec)."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("kill", "Confirmar")
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("kill", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda _d, response: self._on_kill_confirmed(response, pid, sig))
        dlg.present(self.get_root())

    def _on_kill_confirmed(self, response: str, pid: int, sig: int) -> None:
        if response != "kill":
            return
        ok, err = backend.kill_process(pid, sig)
        if ok:
            show_info(self, "Sinal enviado", f"Sinal enviado para PID {pid}.")
            # Force refresh para refletir
            self._refresh()
        else:
            show_error(self, "Falha", err or "Erro desconhecido.")

    # ============================================================
    # Inspect (strace -c)
    # ============================================================

    def _do_inspect(self, pid: int) -> None:
        proc = next((p for p in self._all_procs if p.pid == pid), None)
        label = f"{proc.comm} (PID {pid})" if proc else f"PID {pid}"
        dlg = Adw.AlertDialog(
            heading=f"Inspecionar {label}?",
            body=(
                "Rastreia as chamadas de sistema (syscalls) deste processo por "
                "~5 segundos e mostra um resumo. Read-only — nao altera o "
                "processo.\n\nPede senha de administrador (ptrace via pkexec)."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("go", "Inspecionar")
        dlg.set_default_response("go")
        dlg.connect(
            "response", lambda _d, r: self._on_inspect_confirmed(r, pid, label)
        )
        dlg.present(self.get_root())

    def _on_inspect_confirmed(self, response: str, pid: int, label: str) -> None:
        if response != "go":
            return
        self._status_lbl.set_label(
            f"Inspecionando {label} por ~5s (pode pedir senha)..."
        )
        threading.Thread(
            target=self._inspect_worker, args=(pid, label), daemon=True
        ).start()

    def _inspect_worker(self, pid: int, label: str) -> None:
        result = proc_inspect.inspect_process_blocking(pid)
        GLib.idle_add(self._show_inspect_result, result, label)

    def _show_inspect_result(self, result, label: str) -> bool:
        if result.error:
            show_error(self, "Inspecao falhou", result.error)
            return False

        dlg = Adw.AlertDialog(
            heading=f"Syscalls — {label}",
            body=f"{result.total_calls} chamada(s) em ~5s, por % de tempo:",
        )
        group = Adw.PreferencesGroup()
        for r in result.rows[:20]:
            arow = Adw.ActionRow(title=r.syscall)
            arow.add_css_class("property")
            sub = f"{r.calls} chamada(s)"
            if r.errors:
                sub += f" · {r.errors} erro(s)"
            arow.set_subtitle(sub)
            pct = Gtk.Label(label=f"{r.time_pct:.1f}%")
            pct.add_css_class("monospace")
            pct.add_css_class("caption-heading")
            pct.set_valign(Gtk.Align.CENTER)
            arow.add_suffix(pct)
            group.add(arow)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(360)
        scrolled.set_child(group)
        dlg.set_extra_child(scrolled)
        dlg.add_response("close", "Fechar")
        dlg.present(self.get_root())
        return False
