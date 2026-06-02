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
        page.add(self._results)
        self._rows: list[Gtk.Widget] = []
        self._set_empty(
            "Nenhuma análise ainda. Sem Suricata rodando não há eve.json — "
            "o jeito fácil de testar é escolher um arquivo .pcap acima.")
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        if not self._eve_path and not backend.suricata_available():
            self._banner.set_title(
                "Nenhum eve.json encontrado e Suricata ausente. Instale: "
                + install_hint("suricata"))
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)
        self._run_btn.set_sensitive(bool(self._eve_path))
        self._pcap_btn.set_sensitive(backend.suricata_available())

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
            self._start(lambda: backend.analyze_pcap(f.get_path()))

    # -- run --
    def _on_run_eve(self, _btn: Gtk.Button) -> None:
        if self._eve_path:
            path = self._eve_path
            self._start(lambda: backend.analyze_eve(path))

    def _start(self, work) -> None:
        if self._running:
            return
        self._running = True
        self._run_btn.set_sensitive(False)
        self._pcap_btn.set_sensitive(False)
        self._spinner.start()
        self._set_empty("Analisando…")
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _worker(self, work) -> None:
        result = work()
        backend.save_report(result)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.IdsResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._refresh_banner()
        self._clear()
        self._results.set_description(None)

        if result.error:
            row = Adw.ActionRow()
            row.set_title("Não foi possível analisar")
            row.set_subtitle(result.error)
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add(row)
            return False

        if not result.alerts:
            self._results.set_description(
                f"Nenhum alerta. {result.total_lines} linha(s) lidas · "
                f"{result.elapsed_sec:.1f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhum alerta de intrusão na fonte analisada.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add(row)
            return False

        self._results.set_description(
            f"{len(result.alerts)} alerta(s) · {result.total_lines} linha(s) · "
            f"{result.elapsed_sec:.1f}s. Clique num alerta para ver os detalhes.")
        for a in result.alerts:
            self._add(self._alert_row(a))
        return False

    def _alert_row(self, a: backend.Alert) -> Adw.ExpanderRow:
        label, icon, css = _sev(a.severity)
        exp = Adw.ExpanderRow()
        exp.set_title(a.signature)
        exp.set_subtitle(a.category or "—")
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
        exp.add_row(_prop("O que é", backend.explain(a)))
        exp.add_row(_prop("Origem", a.src))
        exp.add_row(_prop("Destino", a.dest))
        exp.add_row(_prop("Protocolo", a.proto))
        exp.add_row(_prop("Quando", a.timestamp))
        exp.add_row(_prop("Assinatura (SID)", str(a.sid)))
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
