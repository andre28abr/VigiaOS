"""Tab Stats (v0.2 — modo avancado dnscrypt-proxy).

Dashboard mini com queries do query.log:
- KPIs: total / blocked / cached (24h)
- Top 10 dominios consultados
- Banner se query log nao esta habilitado
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import dnscrypt_backend as dc
from .. import migration
from ._helpers import make_clamp


REFRESH_MS = 10_000  # 10s (logs nao mudam tao rapido)


class StatsTab(Adw.Bin):
    """KPIs + top dominios do query.log do dnscrypt-proxy."""

    def __init__(self) -> None:
        super().__init__()
        self._tick_id = 0
        # v0.2.6: flag pra evitar update de widgets ja destruidos.
        # Sem isso, um GLib.idle_add ja pendente apos destroy() crashava
        # ao tentar mexer em self._mode_banner etc.
        self._destroyed = False

        # ===== Header =====
        header_lbl = Gtk.Label(label="Estatisticas de queries")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Resumo de queries das ultimas <b>24h</b> a partir do "
                "<tt>/var/log/dnscrypt-proxy/query.log</tt>. Requer "
                "query_log habilitado no <tt>dnscrypt-proxy.toml</tt>.\n\n"
                "<i>Privacidade</i>: o query log fica local — nenhum dado "
                "vai pra rede. Para LGPD-strictness total, mantenha "
                "<tt>require_nolog = true</tt> no resolver."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # ===== Banner de estado =====
        self._mode_banner = Adw.Banner()
        self._mode_banner.set_revealed(False)

        # ===== KPI cards (3 cards lado-a-lado) =====
        kpis_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        kpis_box.set_halign(Gtk.Align.CENTER)
        kpis_box.set_margin_bottom(24)

        self._total_card = self._build_kpi_card("Queries (24h)", "—")
        kpis_box.append(self._total_card["widget"])

        self._blocked_card = self._build_kpi_card("Bloqueadas", "—")
        kpis_box.append(self._blocked_card["widget"])

        self._cached_card = self._build_kpi_card("Cacheadas", "—")
        kpis_box.append(self._cached_card["widget"])

        # ===== Top domains group =====
        self._top_group = Adw.PreferencesGroup()
        self._top_group.set_margin_top(8)
        self._top_group.set_title("Top 10 dominios consultados (24h)")
        self._top_rows: list = []

        # ===== Refresh button =====
        refresh_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        refresh_btn_box.set_halign(Gtk.Align.END)
        refresh_btn_box.set_margin_top(16)
        refresh_btn = Gtk.Button(label="Recarregar")
        refresh_btn.connect("clicked", lambda _b: self.refresh())
        refresh_btn_box.append(refresh_btn)

        # ===== Layout =====
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(kpis_box)
        inner.append(self._top_group)
        inner.append(refresh_btn_box)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._mode_banner)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        outer.append(scrolled)

        self.set_child(outer)

        # Start
        self.refresh()
        self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args) -> None:
        self._destroyed = True
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _on_tick(self) -> bool:
        # v0.2.6: defensivo — se destruido mas timer ainda armado
        if self._destroyed:
            return False
        self.refresh()
        return True

    # ============================================================
    # KPI builder
    # ============================================================

    def _build_kpi_card(self, label: str, default_value: str) -> dict:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.add_css_class("card")
        card.set_size_request(160, 80)

        val_lbl = Gtk.Label(label=default_value)
        val_lbl.add_css_class("title-1")
        val_lbl.set_halign(Gtk.Align.CENTER)
        val_lbl.set_margin_top(10)
        card.append(val_lbl)

        lbl = Gtk.Label(label=label)
        lbl.add_css_class("caption")
        lbl.add_css_class("dim-label")
        lbl.set_halign(Gtk.Align.CENTER)
        lbl.set_margin_bottom(8)
        card.append(lbl)

        return {"widget": card, "val": val_lbl, "label": lbl}

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        installed = dc.dnscrypt_installed()
        mode = migration.get_current_mode() if installed else "unknown"
        stats = dc.get_stats() if installed else dc.DnsCryptStats()
        GLib.idle_add(self._apply, installed, mode, stats)

    def _apply(self, installed: bool, mode: str, stats) -> bool:
        # v0.2.6: aborta se a tab ja foi destruida (idle_add pendente)
        if self._destroyed:
            return False
        # Banner
        if not installed:
            self._mode_banner.set_title(
                "dnscrypt-proxy nao instalado."
            )
            self._mode_banner.set_revealed(True)
        elif mode != "advanced":
            self._mode_banner.set_title(
                "Modo avancado nao esta ativo. Ative em Status para coletar stats."
            )
            self._mode_banner.set_revealed(True)
        elif not stats.log_available:
            self._mode_banner.set_title(
                "Query log nao disponivel. Habilite query_log no "
                "/etc/dnscrypt-proxy/dnscrypt-proxy.toml e reinicie o servico."
            )
            self._mode_banner.set_revealed(True)
        else:
            self._mode_banner.set_revealed(False)

        # KPIs
        self._total_card["val"].set_label(f"{stats.total_queries:,}".replace(",", "."))
        self._blocked_card["val"].set_label(
            f"{stats.blocked_count:,}".replace(",", ".") if stats.blocked_count > 0 else "0"
        )
        self._cached_card["val"].set_label(
            f"{stats.cached_count:,}".replace(",", ".") if stats.cached_count > 0 else "0"
        )

        # Colorize blocked badge if > 0
        for cls in ("warning", "success"):
            self._blocked_card["val"].remove_css_class(cls)
        if stats.blocked_count > 0:
            self._blocked_card["val"].add_css_class("warning")

        # Top domains
        for r in self._top_rows:
            self._top_group.remove(r)
        self._top_rows = []

        if not stats.top_domains:
            row = Adw.ActionRow(title="Sem dados ainda")
            row.set_subtitle(
                "Aguarde algumas queries serem processadas, ou verifique "
                "se query_log esta habilitado."
            )
            row.add_css_class("dim-label")
            self._top_group.add(row)
            self._top_rows.append(row)
            return False

        for domain, count in stats.top_domains:
            row = Adw.ActionRow(title=domain)
            row.add_css_class("property")
            count_lbl = Gtk.Label(label=str(count))
            count_lbl.add_css_class("monospace")
            count_lbl.add_css_class("caption-heading")
            count_lbl.set_valign(Gtk.Align.CENTER)
            row.add_suffix(count_lbl)
            self._top_group.add(row)
            self._top_rows.append(row)

        return False
