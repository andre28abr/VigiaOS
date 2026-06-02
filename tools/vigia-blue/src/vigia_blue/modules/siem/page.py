"""GUI do Vigia SIEM — abas Alertas / Regras / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell do VigiaBlue via
`Module.impl`. A análise roda em thread (não trava a UI) e atualiza por
`GLib.idle_add`. Mesmo padrão visual do Vigia YARA.

GTK só é importado aqui (caminho da GUI) — o `backend.py` continua puro.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import backend  # noqa: E402


def build_content() -> Gtk.Widget:
    """Conteúdo auto-contido do Vigia SIEM (header próprio + abas)."""
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_AlertsView(), "alertas", "Alertas",
                               "dialog-warning-symbolic")
    stack.add_titled_with_icon(_build_rules(), "regras", "Regras",
                               "view-list-symbolic")
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


# severidade -> (rótulo, ícone, classe-css de cor) — mesma escala do Vigia YARA + "info"
_SEVERITY = {
    "info": ("Info", "dialog-information-symbolic", "accent"),
    "baixo": ("Baixo", "dialog-information-symbolic", "accent"),
    "suspeito": ("Suspeito", "dialog-warning-symbolic", "warning"),
    "alto": ("Alto", "dialog-error-symbolic", "error"),
    "critico": ("Crítico", "dialog-error-symbolic", "error"),
}


def _sev(severity: str) -> tuple[str, str, str]:
    return _SEVERITY.get(
        (severity or "").lower(), ("Alerta", "dialog-warning-symbolic", "warning")
    )


def _prop_row(title: str, value: str) -> Adw.ActionRow:
    r = Adw.ActionRow()
    r.set_title(title)
    r.set_subtitle(value)
    r.set_subtitle_lines(0)
    r.add_css_class("property")
    return r


def _sev_expander(title: str, subtitle: str, severity: str) -> Adw.ExpanderRow:
    """ExpanderRow com ícone + pílula de severidade (usado em Alertas e Regras)."""
    label, icon, css = _sev(severity)
    exp = Adw.ExpanderRow()
    exp.set_title(title)
    exp.set_subtitle(subtitle)
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
    return exp


# ============================================================
# Aba Alertas (a "análise")
# ============================================================


class _AlertsView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._include_audit = False

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Fontes ---
        g_src = Adw.PreferencesGroup()
        g_src.set_title("O que analisar")
        g_src.set_description(
            "Lê os eventos recentes do sistema (journal + fail2ban) e procura "
            "padrões suspeitos. O log de auditoria (audit) é mais rico, mas "
            "exige senha de administrador."
        )
        self._audit_row = Adw.SwitchRow()
        self._audit_row.set_title("Incluir o log de auditoria (audit)")
        self._audit_row.set_subtitle("Mais completo — pede senha (pkexec)")
        self._audit_row.add_prefix(
            Gtk.Image.new_from_icon_name("security-high-symbolic"))
        self._audit_row.connect("notify::active", self._on_audit_toggled)
        g_src.add(self._audit_row)
        page.add(g_src)

        # --- Ação ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._run_btn = Gtk.Button(label="Analisar agora")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.add_css_class("pill")
        self._run_btn.connect("clicked", self._on_run)
        box.append(self._run_btn)
        g_action.add(box)
        page.add(g_action)

        # --- Resultados ---
        self._results = Adw.PreferencesGroup()
        self._results.set_title("Alertas")
        page.add(self._results)
        self._rows: list[Gtk.Widget] = []
        self._set_empty("Clique em Analisar agora para examinar os eventos do sistema.")

        self._refresh_banner()

    # -- estado --
    def _refresh_banner(self) -> None:
        if not backend.core_available():
            self._banner.set_title(
                "Motor vigia-log não encontrado — veja a aba Sobre para instalar."
            )
            self._banner.set_revealed(True)
            self._run_btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._run_btn.set_sensitive(True)

    def _on_audit_toggled(self, row: Adw.SwitchRow, _p) -> None:
        self._include_audit = row.get_active()

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

    def _alert_row(self, a: backend.Alert) -> Adw.ExpanderRow:
        exp = _sev_expander(a.title, a.description, a.severity)
        exp.add_row(_prop_row("O que é", a.description))
        exp.add_row(_prop_row("O que fazer", a.recommendation))
        if a.when:
            exp.add_row(_prop_row("Quando", a.when))
        exp.add_row(_prop_row("Ocorrências", str(a.count)))
        if a.evidence:
            exp.add_row(_prop_row("Evidência (técnico)", "\n".join(a.evidence)))
        return exp

    # -- análise --
    def _on_run(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._running = True
        self._run_btn.set_sensitive(False)
        self._spinner.start()
        self._set_empty("Analisando os eventos do sistema…")
        sources = list(backend.DEFAULT_SOURCES)
        elevated = self._include_audit
        if elevated:
            sources = sources + ["audit"]
        threading.Thread(
            target=self._worker, args=(sources, elevated), daemon=True
        ).start()

    def _worker(self, sources: list[str], elevated: bool) -> None:
        result = backend.analyze(sources=sources, elevated=elevated)
        backend.save_report(result)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.SiemResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._run_btn.set_sensitive(True)
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

        alerts = result.alerts
        if not alerts:
            self._results.set_description(
                f"Nada suspeito. {result.events_count} evento(s) analisados · "
                f"{result.elapsed_sec:.1f}s."
            )
            row = Adw.ActionRow()
            row.set_title("Nenhum alerta — tudo limpo para as regras atuais.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add(row)
            return False

        counts = backend.severity_counts(alerts)
        resumo = " · ".join(
            f"{counts[s]} {_sev(s)[0].lower()}"
            for s in ("critico", "alto", "suspeito", "baixo", "info")
            if counts.get(s)
        )
        self._results.set_description(
            f"{len(alerts)} alerta(s) ({resumo}) · {result.events_count} "
            f"evento(s) · {result.elapsed_sec:.1f}s. Clique num alerta para "
            "ver o que é e o que fazer."
        )
        for a in alerts:
            self._add(self._alert_row(a))
        return False


# ============================================================
# Aba Regras (catálogo do que é detectado)
# ============================================================


def _build_rules() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Regras de detecção")
    g.set_description(
        "O que o Vigia SIEM procura nos eventos do sistema. Cada regra vira um "
        "alerta amigável quando dispara. Clique para ver detalhes."
    )
    for r in backend.rules_catalog():
        exp = _sev_expander(r.name, r.description, r.severity)
        exp.add_row(_prop_row("O que fazer", r.recommendation))
        exp.add_row(_prop_row("Categoria", r.category))
        exp.add_row(_prop_row("Fontes", ", ".join(r.sources)))
        g.add(exp)
    page.add(g)
    return page


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
        reports = backend.list_recent_reports()
        if not reports:
            row = Adw.ActionRow()
            row.set_title("Nenhuma análise salva ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            alerts = rep.get("alerts", [])
            n = len(alerts)
            row = Adw.ActionRow()
            row.set_title(rep.get("started_at", "?"))
            srcs = ", ".join(rep.get("sources", []) or [])
            row.set_subtitle(
                f"{n} alerta(s) · {rep.get('events_count', 0)} evento(s) · {srcs}"
            )
            row.set_subtitle_lines(0)
            icon = "dialog-warning-symbolic" if n else "emblem-ok-symbolic"
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self._group.add(row)
            self._rows.append(row)


# ============================================================
# Aba Sobre
# ============================================================


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()

    g = Adw.PreferencesGroup()
    g.set_title("Vigia SIEM")
    g.set_description(
        "Detecção e triagem de eventos de segurança. Lê os logs do sistema "
        "(audit / journald / fail2ban) e aplica regras para gerar alertas "
        "triados por severidade, com explicação leiga e recomendação. Módulo de "
        "Detecção & SIEM do VigiaBlue. Roda 100% local — nada sai da máquina; "
        "relatórios salvos com permissão 0600."
    )
    g.add(_prop_row(
        "Diferença para o Activity Log",
        "O Activity Log é o navegador (\"veja tudo que aconteceu\"); o SIEM é a "
        "camada de detecção (\"o que é suspeito?\"). Mesma fonte, focos "
        "diferentes."))
    page.add(g)

    g2 = Adw.PreferencesGroup()
    g2.set_title("Motor")
    g2.set_description(
        "O Vigia SIEM usa o mesmo motor do Activity Log — o binário Rust "
        "`vigia-log` — para coletar os eventos. Se ele não estiver instalado:"
    )
    g2.add(_prop_row("Instalar o vigia-log", backend.core_install_hint()))
    page.add(g2)
    return page
