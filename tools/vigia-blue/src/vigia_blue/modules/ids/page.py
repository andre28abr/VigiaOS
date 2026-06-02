"""GUI do Vigia IDS — abas Alertas / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell via `Module.impl`.
Lê um eve.json (Suricata) ou roda o Suricata sobre um pcap, em thread →
`GLib.idle_add`. GTK só é importado aqui.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from vigia_common.platform import install_hint  # noqa: E402

from . import backend  # noqa: E402

_SEVERITY = {
    "info": ("Info", "dialog-information-symbolic", "accent"),
    "baixo": ("Baixo", "dialog-information-symbolic", "accent"),
    "suspeito": ("Suspeito", "dialog-warning-symbolic", "warning"),
    "alto": ("Alto", "dialog-error-symbolic", "error"),
    "critico": ("Crítico", "dialog-error-symbolic", "error"),
}


def _sev(s: str) -> tuple[str, str, str]:
    return _SEVERITY.get((s or "").lower(),
                         ("Alerta", "dialog-warning-symbolic", "warning"))


def _prop(title: str, value: str) -> Adw.ActionRow:
    r = Adw.ActionRow()
    r.set_title(title)
    r.set_subtitle(value or "—")
    r.set_subtitle_lines(0)
    r.add_css_class("property")
    return r


def build_content() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_AlertsView(), "alertas", "Alertas",
                               "dialog-warning-symbolic")
    stack.add_titled_with_icon(_HistoryView(), "hist", "Histórico",
                               "document-open-recent-symbolic")
    stack.add_titled_with_icon(_build_about(), "sobre", "Sobre",
                               "help-about-symbolic")
    switcher = Adw.ViewSwitcher()
    switcher.set_stack(stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
    header = Adw.HeaderBar()
    header.set_title_widget(switcher)
    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(stack)
    return tv


class _AlertsView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._last_result: backend.IdsResult | None = None
        self._hide_noise = False
        found = backend.find_eve()
        self._eve_path: str | None = str(found) if found else None

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        g = Adw.PreferencesGroup()
        g.set_title("Fonte dos alertas")
        g.set_description(
            "O eve.json é criado por um Suricata em execução — não por este "
            "módulo (ele só LÊ os alertas). Sem um Suricata rodando esse arquivo "
            "não existe (por isso o seletor pode não achar nada). Para testar "
            "agora, use \"Analisar um arquivo .pcap\" — o jeito mais fácil."
        )
        self._eve_row = Adw.ActionRow()
        self._eve_row.set_title("Arquivo eve.json")
        self._eve_row.set_subtitle(
            self._eve_path
            or "Nenhum encontrado (normal se o Suricata não está rodando)")
        self._eve_row.set_subtitle_lines(0)
        self._eve_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
        pick = Gtk.Button(label="Selecionar")
        pick.set_valign(Gtk.Align.CENTER)
        pick.connect("clicked", self._on_pick_eve)
        self._eve_row.add_suffix(pick)
        g.add(self._eve_row)

        pcap_row = Adw.ActionRow()
        pcap_row.set_title("Analisar um arquivo .pcap")
        pcap_row.set_subtitle(
            "Roda o Suricata sobre a captura (pode pedir senha) — jeito fácil de testar")
        pcap_row.set_subtitle_lines(0)
        pcap_row.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        pcap_btn = Gtk.Button(label="Selecionar .pcap")
        pcap_btn.set_valign(Gtk.Align.CENTER)
        pcap_btn.connect("clicked", self._on_pick_pcap)
        pcap_row.add_suffix(pcap_btn)
        self._pcap_btn = pcap_btn
        g.add(pcap_row)

        cap_row = Adw.ActionRow()
        cap_row.set_title("Capturar tráfego agora")
        cap_row.set_subtitle(
            "Grava a sua rede por alguns segundos e já analisa (pede senha)")
        cap_row.set_subtitle_lines(0)
        cap_row.add_prefix(Gtk.Image.new_from_icon_name("media-record-symbolic"))
        self._cap_buttons: list[Gtk.Button] = []
        for _txt, _secs in (("30s", 30), ("1 min", 60), ("5 min", 300)):
            b = Gtk.Button(label=_txt)
            b.set_valign(Gtk.Align.CENTER)
            b.connect("clicked", self._on_capture, _secs)
            cap_row.add_suffix(b)
            self._cap_buttons.append(b)
        g.add(cap_row)
        page.add(g)

        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._run_btn = Gtk.Button(label="Analisar eve.json")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.add_css_class("pill")
        self._run_btn.connect("clicked", self._on_run_eve)
        box.append(self._run_btn)
        g_action.add(box)
        page.add(g_action)

        self._results = Adw.PreferencesGroup()
        self._results.set_title("Alertas")
        self._noise_toggle = Gtk.ToggleButton(label="Esconder ruído")
        self._noise_toggle.add_css_class("flat")
        self._noise_toggle.set_tooltip_text("Mostrar só severidade Suspeito ou maior")
        self._noise_toggle.connect("toggled", self._on_filter)
        self._results.set_header_suffix(self._noise_toggle)
        page.add(self._results)
        self._rows: list[Gtk.Widget] = []
        self._set_empty(
            "Nenhuma análise ainda. Sem Suricata rodando não há eve.json — "
            "o jeito fácil de testar é escolher um arquivo .pcap acima.")
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        suri = backend.suricata_available()
        if not self._eve_path and not suri:
            self._banner.set_title(
                "Nenhum eve.json encontrado e Suricata ausente. Instale: "
                + install_hint("suricata"))
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)
        busy = self._running
        self._run_btn.set_sensitive(bool(self._eve_path) and not busy)
        self._pcap_btn.set_sensitive(suri and not busy)
        tdump = backend.tcpdump_available()
        for b in self._cap_buttons:
            b.set_sensitive(suri and tdump and not busy)
            b.set_tooltip_text(
                "Precisa do tcpdump instalado" if not tdump
                else "Precisa do Suricata instalado" if not suri
                else "Captura e analisa o seu tráfego")

    def _add(self, row: Gtk.Widget) -> None:
        self._results.add(row)
        self._rows.append(row)

    def _clear(self) -> None:
        for r in self._rows:
            self._results.remove(r)
        self._rows = []

    def _set_empty(self, text: str, icon: str = "dialog-information-symbolic") -> None:
        self._clear()
        self._results.set_description(None)
        row = Adw.ActionRow()
        row.set_title(text)
        row.set_subtitle_lines(0)
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        self._add(row)

    # -- pickers --
    def _on_pick_eve(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha o eve.json (ex.: /var/log/suricata/eve.json)")
        # abre já na pasta padrão do Suricata, se existir
        eve_dir = Gio.File.new_for_path("/var/log/suricata")
        if eve_dir.query_exists(None):
            dialog.set_initial_folder(eve_dir)
        dialog.open(self.get_root(), None, self._on_eve_chosen)

    def _on_eve_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            self._eve_path = f.get_path()
            self._eve_row.set_subtitle(self._eve_path)
            self._refresh_banner()

    def _on_pick_pcap(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha o arquivo .pcap")
        dialog.open(self.get_root(), None, self._on_pcap_chosen)

    def _on_pcap_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            path = f.get_path()
            self._start(lambda: backend.analyze_pcap(path),
                        "Analisando a captura (pode pedir senha)…")

    # -- run --
    def _on_run_eve(self, _btn: Gtk.Button) -> None:
        if self._eve_path:
            path = self._eve_path
            self._start(lambda: backend.analyze_eve(path),
                        "Analisando o eve.json…")

    def _start(self, work, busy: str = "Analisando…") -> None:
        if self._running:
            return
        self._running = True
        self._last_result = None
        self._refresh_banner()          # desabilita os botões enquanto roda
        self._spinner.start()
        self._set_empty(busy)
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _worker(self, work) -> None:
        result = work()
        backend.save_report(result)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.IdsResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._last_result = result
        backend.save_report(result)
        self._refresh_banner()
        self._render()
        return False

    def _render(self) -> None:
        """(Re)desenha os resultados: agrupados, com resumo e filtro de ruído."""
        self._clear()
        self._results.set_description(None)
        r = self._last_result
        if r is None:
            return

        if r.error:
            row = Adw.ActionRow()
            row.set_title("Não foi possível analisar")
            row.set_subtitle(r.error)
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add(row)
            return

        if not r.alerts:
            self._results.set_description(
                f"Nenhum alerta. {r.total_lines} linha(s) lidas · "
                f"{r.elapsed_sec:.1f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhum alerta de intrusão na fonte analisada.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add(row)
            return

        all_groups = backend.group_alerts(r.alerts)
        shown = all_groups
        if self._hide_noise:
            shown = [g for g in all_groups
                     if backend.SEVERITY_RANK.get(g.severity, 0) >= 2]
        counts = backend.severity_counts(r.alerts)
        resumo = " · ".join(
            f"{counts[s]} {_sev(s)[0].lower()}"
            for s in ("critico", "alto", "suspeito", "baixo", "info")
            if counts.get(s))
        hidden = len(all_groups) - len(shown)
        extra = f" · {hidden} tipo(s) de ruído ocultos" if (
            self._hide_noise and hidden) else ""
        self._results.set_description(
            f"{len(r.alerts)} alerta(s) em {len(all_groups)} tipo(s) · {resumo}"
            f"{extra} · {r.elapsed_sec:.1f}s. Clique num tipo para ver detalhes.")

        if not shown:
            row = Adw.ActionRow()
            row.set_title("Só ruído de baixa severidade — nada acima de 'Baixo'.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add(row)
            return
        for g in shown:
            self._add(self._group_row(g))

    def _on_filter(self, btn: Gtk.ToggleButton) -> None:
        self._hide_noise = btn.get_active()
        if self._last_result is not None:
            self._render()

    def _on_capture(self, _btn: Gtk.Button, seconds: int) -> None:
        self._start(
            lambda: backend.capture_and_analyze(seconds),
            f"Capturando {seconds}s de tráfego… (vai pedir a senha)")

    def _group_row(self, g: backend.AlertGroup) -> Adw.ExpanderRow:
        label, icon, css = _sev(g.severity)
        exp = Adw.ExpanderRow()
        exp.set_title(g.signature + (f"   ({g.count}×)" if g.count > 1 else ""))
        exp.set_subtitle(g.category or "—")
        exp.set_subtitle_lines(0)
        img = Gtk.Image.new_from_icon_name(icon)
        if css in ("warning", "error"):
            img.add_css_class(css)
        exp.add_prefix(img)
        pill = Gtk.Label(label=label)
        pill.add_css_class("caption")
        if css in ("warning", "error"):
            pill.add_css_class(css)
        exp.add_suffix(pill)
        exp.add_row(_prop("O que é", backend.explain(g)))
        if g.count > 1:
            exp.add_row(_prop("Ocorrências", f"{g.count} vezes"))
        if g.endpoints:
            exp.add_row(_prop("Origem → destino", "\n".join(g.endpoints)))
        exp.add_row(_prop("Protocolo", g.proto))
        exp.add_row(_prop("Quando", g.when))
        exp.add_row(_prop("Assinatura (SID)", str(g.sid)))
        return exp


# ============================================================
# Aba Histórico
# ============================================================


class _HistoryView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._page = Adw.PreferencesPage()
        self._page.set_vexpand(True)
        self.append(self._page)
        self._group = Adw.PreferencesGroup()
        self._group.set_title("Análises recentes")
        refresh = Gtk.Button(label="Atualizar")
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda _b: self._reload())
        self._group.set_header_suffix(refresh)
        self._page.add(self._group)
        self._rows: list[Gtk.Widget] = []
        self._reload()

    def _reload(self) -> None:
        for r in self._rows:
            self._group.remove(r)
        self._rows = []
        for rep in backend.list_recent_reports():
            n = len(rep.get("alerts", []))
            row = Adw.ActionRow()
            row.set_title(rep.get("source", "?"))
            row.set_subtitle(f"{rep.get('started_at', '?')} · {n} alerta(s)")
            row.set_subtitle_lines(0)
            icon = "dialog-warning-symbolic" if n else "emblem-ok-symbolic"
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self._group.add(row)
            self._rows.append(row)
        if not self._rows:
            row = Adw.ActionRow()
            row.set_title("Nenhuma análise salva ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)


# ============================================================
# Aba Sobre
# ============================================================


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Vigia IDS")
    g.set_description(
        "Painel de alertas de intrusão de rede. Lê o eve.json do Suricata (um "
        "IDS de rede) e mostra os alertas de forma triada. Módulo de Detecção do "
        "VigiaBlue. Roda local; relatórios salvos com permissão 0600."
    )
    g.add(_prop(
        "Ler eve.json existente",
        "Se você tem um Suricata em execução, aponte para o /var/log/suricata/"
        "eve.json. Não precisa do Suricata instalado nesta máquina para só ler."))
    g.add(_prop(
        "Analisar um .pcap",
        "Com o Suricata instalado, escolha uma captura .pcap — ele roda o "
        "Suricata sobre ela e mostra os alertas gerados."))
    page.add(g)
    return page
