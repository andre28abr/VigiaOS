"""Tab Conexões: "quem está usando a minha internet" — agrupado por app, com
nomes (DNS reverso), estados em PT-BR e conexões locais escondidas por padrão.

É também a BASE da aba Escutando (que sobrescreve os hooks de render/summary).
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend, humanize
from ._helpers import make_clamp

# Estado → classe de cor do selo
STATE_CSS = {
    "ESTAB": "success",
    "LISTEN": "accent",
    "TIME-WAIT": "dim-label",
    "CLOSE-WAIT": "warning",
    "UNCONN": "dim-label",
    "SYN-SENT": "warning",
    "SYN-RECV": "warning",
}


class ConnectionsTab(Gtk.Box):
    """Conexões com a internet, agrupadas por aplicativo."""

    # Subclasses ajustam estes:
    _show_hide_local = True   # mostra o toggle "conexões internas"

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12,
        )
        self.append(make_clamp(inner))

        # ---- toolbar ----
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(
            "Filtrar por app, site ou porta (ex: firefox, google, 443)")
        self._search.set_hexpand(True)
        self._search.connect("search-changed",
                             lambda _e: self._list.invalidate_filter())
        toolbar.append(self._search)

        if self._show_hide_local:
            local_lbl = Gtk.Label(label="Internas:")
            local_lbl.set_valign(Gtk.Align.CENTER)
            local_lbl.set_tooltip_text(
                "Mostrar também conexões locais (127.0.0.1) — geralmente ruído.")
            toolbar.append(local_lbl)
            self._hide_local_switch = Gtk.Switch()
            self._hide_local_switch.set_valign(Gtk.Align.CENTER)
            self._hide_local_switch.set_active(False)  # off = esconde internas
            self._hide_local_switch.connect(
                "state-set", lambda _s, _v: (self._refresh(), False)[1])
            toolbar.append(self._hide_local_switch)
        else:
            self._hide_local_switch = None

        auto_lbl = Gtk.Label(label="Auto:")
        auto_lbl.set_valign(Gtk.Align.CENTER)
        toolbar.append(auto_lbl)
        self._auto_switch = Gtk.Switch()
        self._auto_switch.set_valign(Gtk.Align.CENTER)
        self._auto_switch.set_active(True)
        self._auto_switch.connect("state-set", self._on_auto_toggle)
        toolbar.append(self._auto_switch)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.connect("clicked", lambda _b: self._refresh())
        toolbar.append(self._refresh_btn)
        inner.append(toolbar)

        # ---- modo admin ----
        elevated_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        elevated_box.add_css_class("card")
        elevated_box.set_margin_top(4)
        elevated_box.set_margin_bottom(4)
        info_lbl = Gtk.Label()
        info_lbl.set_markup(
            "<b>Modo admin</b> — mostra o nome dos apps do sistema (root, "
            "systemd, etc.). Pede senha a cada Atualizar; desliga o auto.")
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
        self._elevated_mode = False

        # ---- resumo ----
        self._summary_label = Gtk.Label()
        self._summary_label.set_xalign(0)
        self._summary_label.add_css_class("dim-label")
        inner.append(self._summary_label)

        # ---- lista ----
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_filter_func(self._filter)
        scrolled.set_child(self._list)
        inner.append(scrolled)

        self._row_search_text: dict[Gtk.Widget, str] = {}
        self._resolve_rows: list[tuple[Adw.ActionRow, str, str]] = []
        self._refresh_source_id: int | None = None
        self._refresh_interval_s = 3
        self._fetch_running = False

        loading = Adw.ActionRow()
        loading.set_title("Carregando…")
        loading.set_subtitle("Coletando conexões via `ss`")
        loading.add_css_class("dim-label")
        self._list.append(loading)
        self._summary_label.set_text("Carregando…")

        self.connect("map", self._on_widget_map)
        self.connect("unmap", self._on_widget_unmap)
        self._refresh()

    # ============================================================
    # Hooks (subclasses sobrescrevem)
    # ============================================================

    def _fetch(self) -> list[backend.NetConnection]:
        return backend.list_connections(elevated=self._elevated_mode)

    def _prefilter(self, conns: list[backend.NetConnection]
                   ) -> list[backend.NetConnection]:
        """Conexões mostra CONEXÕES — sockets só escutando vão pra aba Escutando.
        'Internas' desligado também esconde loopback (só internet)."""
        conns = [c for c in conns if not c.is_listening]
        if (self._hide_local_switch is not None
                and not self._hide_local_switch.get_active()):
            conns = [c for c in conns
                     if humanize.is_internet_peer(c.peer_addr)]
        return conns

    def _summary_text(self, conns: list[backend.NetConnection]) -> str:
        apps = {c.process for c in conns if c.process != "?"}
        n_app = len(apps)
        return (f"{n_app} app{'s' if n_app != 1 else ''} na internet · "
                f"{len(conns)} conexõ{'es' if len(conns) != 1 else 'es'}")

    def _render_into(self, conns: list[backend.NetConnection]) -> None:
        """View padrão: agrupada por app, com DNS reverso async."""
        groups: dict[str, list[backend.NetConnection]] = {}
        for c in conns:
            key = c.process if c.process != "?" else "(apps do sistema)"
            groups.setdefault(key, []).append(c)

        for proc in sorted(groups, key=lambda p: (p.startswith("("), p.lower())):
            items = groups[proc]
            exp = Adw.ExpanderRow()
            exp.set_title(proc)
            n = len(items)
            exp.set_subtitle(f"{n} conexã{'o' if n == 1 else 'es'}")
            exp.add_prefix(Gtk.Image.new_from_icon_name(
                "network-transmit-receive-symbolic"))
            exp.set_expanded(n <= 4)

            hay = [proc]
            for c in items:
                host, port = humanize.split_host_port(c.peer_addr)
                base_sub = f"{humanize.state_label(c.state)} · porta {port}"
                sub = Adw.ActionRow()
                sub.set_title(host or c.peer_addr)
                sub.set_subtitle(base_sub)
                badge = Gtk.Label(label=humanize.state_label(c.state))
                badge.add_css_class(STATE_CSS.get(c.state, "dim-label"))
                badge.add_css_class("caption")
                badge.set_valign(Gtk.Align.CENTER)
                sub.add_suffix(badge)
                exp.add_row(sub)
                hay.append(f"{host} {port} {humanize.state_label(c.state)}")
                if humanize.is_internet_peer(c.peer_addr):
                    self._resolve_rows.append((sub, host, base_sub))

            self._list.append(exp)
            self._row_search_text[exp] = " ".join(hay).lower()

        self._kick_resolve()

    # ============================================================
    # Refresh (async)
    # ============================================================

    def _refresh(self) -> None:
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
        try:
            conns = self._prefilter(conns)

            while child := self._list.get_first_child():
                self._list.remove(child)
            self._row_search_text.clear()
            self._resolve_rows = []

            self._summary_label.set_text(self._summary_text(conns))

            if not conns:
                empty = Adw.ActionRow()
                empty.set_title("Nenhuma conexão")
                empty.set_subtitle(
                    "Nada com a internet agora. (Ligue 'Internas' pra ver as "
                    "locais, ou o Modo admin pros apps do sistema.)")
                empty.add_css_class("dim-label")
                self._list.append(empty)
                return False

            self._render_into(conns)
            if self._search.get_text():
                self._list.invalidate_filter()
        finally:
            self._fetch_running = False
        return False

    # ============================================================
    # DNS reverso (async, em cima da lista já mostrada)
    # ============================================================

    def _kick_resolve(self) -> None:
        ips = list({ip for _row, ip, _sub in self._resolve_rows if ip})
        if not ips:
            return
        threading.Thread(target=self._resolve_worker, args=(ips,),
                         daemon=True).start()

    def _resolve_worker(self, ips: list[str]) -> None:
        names = {ip: humanize.resolve_host(ip) for ip in ips}
        GLib.idle_add(self._apply_names, names)

    def _apply_names(self, names: dict) -> bool:
        for row, ip, base_sub in self._resolve_rows:
            name = names.get(ip)
            if name:
                row.set_title(name)
                row.set_subtitle(f"{ip} · {base_sub}")
        return False

    # ============================================================
    # Filtro / auto-refresh / visibilidade / admin (machinery)
    # ============================================================

    def _filter(self, row: Gtk.ListBoxRow) -> bool:
        query = self._search.get_text().lower().strip()
        if not query:
            return True
        hay = self._row_search_text.get(row)
        return hay is None or query in hay

    def _on_auto_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        if value:
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()
        switch.set_state(value)
        return True

    def _start_auto_refresh(self) -> None:
        if self._refresh_source_id is None and self.get_mapped():
            self._refresh_source_id = GLib.timeout_add_seconds(
                self._refresh_interval_s, self._on_auto_tick)

    def _stop_auto_refresh(self) -> None:
        if self._refresh_source_id is not None:
            GLib.source_remove(self._refresh_source_id)
            self._refresh_source_id = None

    def _on_auto_tick(self) -> bool:
        self._refresh()
        return True

    def _on_widget_map(self, _widget) -> None:
        if self._auto_switch.get_active() and not self._elevated_mode:
            self._start_auto_refresh()

    def _on_widget_unmap(self, _widget) -> None:
        self._stop_auto_refresh()

    def _on_elevated_toggle(self, switch: Gtk.Switch, value: bool) -> bool:
        self._elevated_mode = value
        if value:
            if self._auto_switch.get_active():
                self._auto_switch.set_active(False)
            self._auto_switch.set_sensitive(False)
        else:
            self._auto_switch.set_sensitive(True)
        switch.set_state(value)
        return True
