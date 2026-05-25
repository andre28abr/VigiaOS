"""Tab Connections: lista TCP/UDP ativas com auto-refresh."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


# Cores para estados (paleta zinc + emerald + amber)
STATE_COLORS_CSS = {
    "ESTAB": "success",      # verde — conexao ativa
    "LISTEN": "accent",      # accent — servidor escutando
    "TIME-WAIT": "dim-label",
    "CLOSE-WAIT": "warning",
    "UNCONN": "dim-label",   # UDP "conexao" basica
    "SYN-SENT": "warning",
    "SYN-RECV": "warning",
}


class ConnectionsTab(Gtk.Box):
    """Lista todas as conexoes (TCP+UDP, qualquer estado)."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        # ============= Toolbar ============= #
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Search
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(
            "Filtrar por processo, IP, porta (ex: firefox, 443, 192.168)"
        )
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda _e: self._list.invalidate_filter())
        toolbar.append(self._search)

        # Auto-refresh toggle
        auto_lbl = Gtk.Label(label="Auto:")
        auto_lbl.set_valign(Gtk.Align.CENTER)
        toolbar.append(auto_lbl)
        self._auto_switch = Gtk.Switch()
        self._auto_switch.set_valign(Gtk.Align.CENTER)
        self._auto_switch.set_active(True)
        self._auto_switch.connect("state-set", self._on_auto_toggle)
        toolbar.append(self._auto_switch)

        # Refresh now button
        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.add_css_class("pill")
        self._refresh_btn.connect("clicked", lambda _b: self._refresh())
        toolbar.append(self._refresh_btn)

        inner.append(toolbar)

        # ============= Modo admin (card explicativo) ============= #
        elevated_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        elevated_box.add_css_class("card")
        elevated_box.set_margin_top(4)
        elevated_box.set_margin_bottom(4)
        # Padding interno
        elevated_box.set_margin_start(0)
        elevated_box.set_margin_end(0)

        info_lbl = Gtk.Label()
        info_lbl.set_markup(
            "<b>Modo admin</b> — exibe nome de processos do sistema (root, "
            "systemd-resolve, etc.). Pede senha admin a cada Atualizar. "
            "Auto-refresh fica desabilitado neste modo."
        )
        info_lbl.set_wrap(True)
        info_lbl.set_xalign(0)
        info_lbl.set_hexpand(True)
        info_lbl.set_margin_start(12)
        info_lbl.set_margin_top(12)
        info_lbl.set_margin_bottom(12)
        elevated_box.append(info_lbl)

        self._elevated_switch = Gtk.Switch()
        self._elevated_switch.set_valign(Gtk.Align.CENTER)
        self._elevated_switch.set_margin_end(12)
        self._elevated_switch.set_active(False)
        self._elevated_switch.connect("state-set", self._on_elevated_toggle)
        elevated_box.append(self._elevated_switch)

        inner.append(elevated_box)

        # Estado inicial do modo
        self._elevated_mode = False

        # Count label
        self._count_label = Gtk.Label()
        self._count_label.set_xalign(0)
        self._count_label.add_css_class("dim-label")
        inner.append(self._count_label)

        # Lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_filter_func(self._filter)
        scrolled.set_child(self._list)
        inner.append(scrolled)

        self._row_search_text: dict[Adw.ActionRow, str] = {}
        self._refresh_source_id: int | None = None
        self._refresh_interval_s = 3
        self._initial_load_done = False
        self._fetch_running = False  # evita acumular refreshes concorrentes

        # Empty placeholder ate o primeiro fetch terminar
        loading_row = Adw.ActionRow()
        loading_row.set_title("Carregando…")
        loading_row.set_subtitle("Coletando conexoes via `ss -tunap`")
        loading_row.add_css_class("dim-label")
        self._list.append(loading_row)
        self._count_label.set_text("Carregando…")

        # Auto-refresh so liga quando o widget esta mapped (visivel).
        # Pausa quando o usuario sai pra outra tool no Hub.
        self.connect("map", self._on_widget_map)
        self.connect("unmap", self._on_widget_unmap)

        # Dispara primeiro fetch em thread — nao bloqueia UI
        self._refresh()

    # ========================================================================
    # Subclass hook — Listening tab override para usar backend.list_listening()
    # ========================================================================

    def _fetch(self) -> list[backend.NetConnection]:
        return backend.list_connections(elevated=self._elevated_mode)

    # ========================================================================
    # Refresh logic (async — subprocess vai pra worker thread)
    # ========================================================================

    def _refresh(self) -> None:
        """Dispara fetch em thread. Idempotente: se ja ha fetch em andamento,
        no-op (evita acumular pkexec dialogs sob spam de clique)."""
        if self._fetch_running:
            return
        self._fetch_running = True
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            conns = self._fetch()
        except Exception:  # pylint: disable=broad-except
            conns = []
        GLib.idle_add(self._apply_conns, conns)

    def _apply_conns(self, conns: list[backend.NetConnection]) -> bool:
        """Atualiza widgets com lista coletada. Roda no UI thread."""
        try:
            query = self._search.get_text()

            # Limpa lista
            while child := self._list.get_first_child():
                self._list.remove(child)
            self._row_search_text.clear()

            # Ordena: ESTABLISHED primeiro, depois LISTEN, depois resto
            order_key: Callable[[backend.NetConnection], tuple] = lambda c: (
                0 if c.state == "ESTAB" else (1 if c.state == "LISTEN" else 2),
                c.process,
                c.local_addr,
            )
            conns = sorted(conns, key=order_key)

            if not conns:
                empty = Adw.ActionRow()
                empty.set_title("Sem conexoes")
                empty.set_subtitle("`ss -tunap` nao retornou nada (raro) ou nao esta disponivel.")
                self._list.append(empty)
                self._count_label.set_text("0 conexoes")
                return False

            for c in conns:
                row = self._build_row(c)
                self._list.append(row)
                self._row_search_text[row] = (
                    f"{c.process} {c.pid} {c.local_addr} {c.peer_addr} "
                    f"{c.proto} {c.state}"
                ).lower()

            self._count_label.set_text(f"{len(conns)} conexoes")
            if query:
                self._list.invalidate_filter()
        finally:
            self._fetch_running = False
            self._initial_load_done = True
        return False

    def _build_row(self, c: backend.NetConnection) -> Adw.ActionRow:
        row = Adw.ActionRow()
        process_label = f"{c.process}" if c.process != "?" else "(processo restrito)"
        if c.pid != "?":
            process_label += f" [{c.pid}]"
        title = f"{c.proto.upper()} {c.local_addr} → {c.peer_addr}"
        row.set_title(title)
        row.set_subtitle(process_label)

        # State badge (suffix)
        state_label = Gtk.Label(label=c.state)
        state_label.set_valign(Gtk.Align.CENTER)
        css = STATE_COLORS_CSS.get(c.state, "dim-label")
        state_label.add_css_class(css)
        state_label.add_css_class("caption")
        row.add_suffix(state_label)

        return row

    def _filter(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search.get_text().lower().strip()
        if not query:
            return True
        haystack = self._row_search_text.get(row)
        if haystack is None:
            return True
        return query in haystack

    # ========================================================================
    # Auto-refresh control
    # ========================================================================

    def _on_auto_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        if value:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
        switch.set_state(value)
        return True

    def _start_auto_refresh(self) -> None:
        # So liga se o widget esta visivel. Quando o user troca de tool no
        # Hub, _on_widget_unmap chama _stop_auto_refresh; quando volta,
        # _on_widget_map chama _start_auto_refresh.
        if self._refresh_source_id is None and self.get_mapped():
            self._refresh_source_id = GLib.timeout_add_seconds(
                self._refresh_interval_s, self._on_auto_tick
            )

    def _stop_auto_refresh(self) -> None:
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
            self._refresh_source_id = None

    def _on_auto_tick(self) -> bool:
        self._refresh()
        return True  # GLib.SOURCE_CONTINUE

    # ========================================================================
    # Visibility tracking (Hub embedded mode)
    # ========================================================================

    def _on_widget_map(self, _widget) -> None:
        """Widget acabou de ficar visivel (tool selecionada no Hub)."""
        if self._auto_switch.get_active() and not self._elevated_mode:
            self._start_auto_refresh()

    def _on_widget_unmap(self, _widget) -> None:
        """Widget ficou invisivel (user trocou de tool). Para o auto-refresh
        pra nao gastar CPU/subprocess em background."""
        self._stop_auto_refresh()

    def _on_elevated_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        """Toggle modo admin (pkexec)."""
        self._elevated_mode = value
        if value:
            # Desliga auto-refresh para nao spammar polkit
            if self._auto_switch.get_active():
                self._auto_switch.set_active(False)
            self._auto_switch.set_sensitive(False)
        else:
            self._auto_switch.set_sensitive(True)
        # Forca refresh imediato (vai disparar polkit se elevated=True)
        self._refresh()
        switch.set_state(value)
        return True
