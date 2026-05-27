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
from ._helpers import make_clamp, show_error, show_info


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
        # v0.2.9: estado do running pra disable do botao
        self._running = False

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
        # v0.2.9: ganha button-label condicional pra habilitar query log
        self._mode_banner = Adw.Banner()
        self._mode_banner.set_revealed(False)
        self._mode_banner.connect("button-clicked", self._on_banner_clicked)
        # Acao do botao do banner: muda conforme o estado
        # ("enable_query_log" ou "" — vazio nao mostra botao)
        self._banner_action: str = ""

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
    # v0.2.9: habilitar query_log via UI (sem precisar editar .toml)
    # ============================================================

    def _on_banner_clicked(self, _banner) -> None:
        """Acao do botao do banner — depende do estado atual."""
        if self._banner_action == "enable_query_log":
            self._show_enable_query_log_dialog()

    def _show_enable_query_log_dialog(self) -> None:
        if self._running:
            return
        dlg = Adw.AlertDialog(
            heading="Habilitar query log?",
            body=(
                "Vai editar /etc/dnscrypt-proxy/dnscrypt-proxy.toml para "
                "adicionar:\n\n"
                "  [query_log]\n"
                "  file = '/var/log/dnscrypt-proxy/query.log'\n\n"
                "<b>Aviso LGPD/privacidade</b>: o query log registra TODA "
                "query DNS feita pelo sistema (incluindo sites visitados). "
                "O arquivo fica LOCAL — nenhum dado vai pra rede. Mas "
                "qualquer um com acesso ao arquivo (root) pode ver seu "
                "historico de DNS.\n\n"
                "Pra preservar privacidade, mantenha <tt>require_nolog = true</tt> "
                "no resolver (configuracao default).\n\n"
                "dnscrypt-proxy sera reiniciado."
            ),
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("enable", "Habilitar")
        dlg.set_response_appearance("enable", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_enable_query_log_response)
        dlg.present(self.get_root())

    def _on_enable_query_log_response(self, _dlg, response: str) -> None:
        if response != "enable":
            return
        self._running = True
        threading.Thread(
            target=self._enable_query_log_worker, daemon=True,
        ).start()

    def _enable_query_log_worker(self) -> None:
        try:
            ok, err = dc.enable_query_log_in_config()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"

        # v0.2.10: apos enable, espera ate 5s pelo daemon criar o file
        file_created = False
        if ok:
            import time as _t
            for _ in range(10):
                if dc.QUERY_LOG_PATH.exists():
                    file_created = True
                    break
                _t.sleep(0.5)

        GLib.idle_add(self._on_enable_query_log_done, ok, err, file_created)

    def _on_enable_query_log_done(
        self, ok: bool, err: str, file_created: bool,
    ) -> bool:
        if self._destroyed:
            return False
        self._running = False
        if not ok:
            show_error(self, "Falha ao habilitar query log", err)
        elif not file_created:
            # v0.2.10: edit foi OK mas daemon nao criou o file
            # Provavel: permissoes do dir ou SELinux
            show_error(
                self,
                "Config editado mas log nao foi criado",
                "O dnscrypt-proxy.toml foi atualizado e o servico "
                "reiniciado, mas o arquivo /var/log/dnscrypt-proxy/"
                "query.log nao foi criado.\n\n"
                "Causas possiveis:\n"
                "• Permissoes do diretorio /var/log/dnscrypt-proxy/\n"
                "• Politica SELinux bloqueando escrita\n"
                "• Erro de syntax no dnscrypt-proxy.toml\n\n"
                "Diagnostico:\n"
                "  sudo journalctl -u dnscrypt-proxy -n 50\n"
                "  sudo ls -la /var/log/dnscrypt-proxy/\n"
                "  sudo audit2why -a 2>/dev/null | head -20",
            )
        else:
            show_info(
                self,
                "Query log habilitado",
                "dnscrypt-proxy reiniciado e log file criado. As "
                "primeiras queries comecarao a aparecer em segundos. "
                "Aguarde o proximo refresh (10s).",
            )
        self.refresh()
        return False

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
        # Banner — v0.2.9: ganha botao de acao quando query log desabilitado
        self._banner_action = ""
        self._mode_banner.set_button_label("")
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
                "Query log esta desabilitado. Habilite pra ver estatisticas."
            )
            self._mode_banner.set_button_label("Habilitar")
            self._banner_action = "enable_query_log"
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
