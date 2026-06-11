"""GUI do Vigia Web Scanner — termo de uso + Varredura / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget` (embarcado pelo shell via `Module.impl`).
Passa pelo portão do termo (gate.build_gated). A varredura (wapiti) roda em
thread, é cancelável e atualiza por `GLib.idle_add`. GTK só aqui.
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ... import gate  # noqa: E402
from . import backend  # noqa: E402


def build_content() -> Gtk.Widget:
    return gate.build_gated(_build_tool)


def _build_tool() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(
        _ScanView(), "scan", "Varredura", "applications-internet-symbolic")
    stack.add_titled_with_icon(
        _HistoryView(), "hist", "Histórico", "document-open-recent-symbolic")
    stack.add_titled_with_icon(
        _build_about(), "sobre", "Sobre", "help-about-symbolic")

    switcher = Adw.ViewSwitcher()
    switcher.set_stack(stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

    header = Adw.HeaderBar()
    header.set_title_widget(switcher)

    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(stack)
    return tv


def _open_path(path: str) -> None:
    try:
        Gio.AppInfo.launch_default_for_uri(f"file://{path}", None)
    except GLib.Error as e:
        print(f"[web] falha ao abrir {path}: {e}", flush=True)


_SEV = {
    "critical": ("Crítico", "error", "dialog-error-symbolic"),
    "high": ("Alto", "error", "dialog-error-symbolic"),
    "medium": ("Médio", "warning", "dialog-warning-symbolic"),
    "low": ("Baixo", "accent", "dialog-information-symbolic"),
    "info": ("Informativo", "dim-label", "dialog-information-symbolic"),
}


def _sev(s: str) -> tuple[str, str, str]:
    return _SEV.get((s or "").lower(),
                    ("Outro", "dim-label", "dialog-information-symbolic"))


class _ScanView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._handle: backend.ScanProcess | None = None
        self._last_result: backend.ScanResult | None = None

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Alvo ---
        g_target = Adw.PreferencesGroup()
        g_target.set_title("Alvo autorizado")
        g_target.set_description(
            "URL da aplicação web (ex.: https://exemplo.com.br). Varredura ATIVA "
            "— ela envia requisições ao site. Use só com autorização.")
        self._entry = Adw.EntryRow()
        self._entry.set_title("URL")
        self._entry.add_prefix(
            Gtk.Image.new_from_icon_name("applications-internet-symbolic"))
        self._entry.connect("entry-activated", self._on_scan)
        g_target.add(self._entry)
        page.add(g_target)

        # --- Perfil ---
        g_prof = Adw.PreferencesGroup()
        g_prof.set_title("Perfil")
        self._profiles = backend.PROFILES
        self._combo = Adw.ComboRow()
        self._combo.set_title("Escopo")
        self._combo.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        model = Gtk.StringList()
        default_idx = 0
        for i, p in enumerate(self._profiles):
            model.append(p.label)
            if p.id == backend.DEFAULT_PROFILE:
                default_idx = i
        self._combo.set_model(model)
        self._combo.set_selected(default_idx)
        self._combo.connect("notify::selected", self._on_profile_changed)
        g_prof.add(self._combo)
        page.add(g_prof)
        self._on_profile_changed(self._combo, None)

        # --- Ação ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._btn = Gtk.Button(label="Escanear")
        self._btn.add_css_class("suggested-action")
        self._btn.add_css_class("pill")
        self._btn.connect("clicked", self._on_scan)
        box.append(self._btn)
        self._export_btn = Gtk.Button(label="Exportar")
        self._export_btn.add_css_class("pill")
        self._export_btn.set_sensitive(False)
        self._export_btn.connect("clicked", self._on_export)
        box.append(self._export_btn)
        g_action.add(box)
        page.add(g_action)

        # --- Resultados ---
        self._results = Adw.PreferencesGroup()
        self._results.set_title("Achados")
        page.add(self._results)
        self._result_rows: list[Gtk.Widget] = []
        self._set_results_info("Nenhuma varredura ainda.",
                               "dialog-information-symbolic")
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        if not backend.wapiti_available():
            self._banner.set_title(
                "wapiti não instalado — veja a aba Sobre para instalar.")
            self._banner.set_revealed(True)
            self._btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._btn.set_sensitive(True)

    def _add_result(self, row: Gtk.Widget) -> None:
        self._results.add(row)
        self._result_rows.append(row)

    def _clear_results(self) -> None:
        for r in self._result_rows:
            self._results.remove(r)
        self._result_rows = []

    def _set_results_info(self, text: str, icon: str) -> None:
        self._clear_results()
        self._results.set_description(None)
        row = Adw.ActionRow()
        row.set_title(text)
        row.set_subtitle_lines(0)
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        self._add_result(row)

    def _on_profile_changed(self, combo: Adw.ComboRow, _param) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._profiles):
            combo.set_subtitle(self._profiles[idx].description)

    @staticmethod
    def _detail(title: str, value: str) -> Adw.ActionRow:
        r = Adw.ActionRow()
        r.set_title(title)
        r.set_subtitle(value)
        r.set_subtitle_lines(0)
        r.set_subtitle_selectable(True)
        return r

    def _finding_row(self, f: backend.Finding) -> Adw.ExpanderRow:
        label, css, icon = _sev(f.severity)
        exp = Adw.ExpanderRow()
        exp.set_title(f.category)
        loc = f"{f.method} {f.path}".strip()
        exp.set_subtitle(loc or "—")
        exp.set_subtitle_lines(0)
        img = Gtk.Image.new_from_icon_name(icon)
        if css in ("error", "warning"):
            img.add_css_class(css)
        exp.add_prefix(img)
        badge = Gtk.Label(label=label)
        badge.add_css_class("caption")
        if css in ("error", "warning"):
            badge.add_css_class(css)
        badge.set_valign(Gtk.Align.CENTER)
        exp.add_suffix(badge)
        if loc:
            exp.add_row(self._detail("Onde", loc))
        if f.parameter:
            exp.add_row(self._detail("Parâmetro", f.parameter))
        if f.info:
            exp.add_row(self._detail("Detalhe", f.info))
        return exp

    def _summary(self, result: backend.ScanResult) -> str:
        counts = backend.counts_by_severity(result.findings)
        parts = [f"{counts[s]} {_sev(s)[0].lower()}"
                 for s in backend.SEVERITIES if counts.get(s)]
        return (f"{result.total} achado(s): " + " · ".join(parts)
                + f" · {result.elapsed_sec:.0f}s")

    # -- scan --
    def _on_scan(self, *_args) -> None:
        if self._running:
            self._cancel()
            return
        raw = self._entry.get_text()
        if not backend.validate_target(raw):
            self._set_results_info(
                "URL inválida. Use uma URL — ex.: https://exemplo.com.",
                "dialog-error-symbolic")
            return
        idx = self._combo.get_selected()
        profile_id = (self._profiles[idx].id
                      if 0 <= idx < len(self._profiles) else backend.DEFAULT_PROFILE)
        self._handle = backend.ScanProcess()
        self._running = True
        self._btn.set_label("Cancelar")
        self._btn.remove_css_class("suggested-action")
        self._btn.add_css_class("destructive-action")
        self._spinner.start()
        self._set_results_info(
            f"Escaneando {backend.normalize_target(raw)}… (o wapiti rastreia e "
            "testa o site; pode levar minutos).", "applications-internet-symbolic")
        threading.Thread(
            target=self._worker, args=(raw, profile_id, self._handle),
            daemon=True).start()

    def _cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self._btn.set_sensitive(False)

    def _worker(self, target, profile_id, handle) -> None:
        result = backend.run_scan(target, profile_id, handle=handle)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.ScanResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._btn.set_label("Escanear")
        self._btn.remove_css_class("destructive-action")
        self._btn.add_css_class("suggested-action")
        self._btn.set_sensitive(True)

        cancelled = bool(self._handle and self._handle.cancelled)
        self._handle = None
        if cancelled:
            self._export_btn.set_sensitive(False)
            self._set_results_info("Varredura cancelada.", "process-stop-symbolic")
            return False

        self._clear_results()
        self._results.set_description(None)

        if result.error:
            self._export_btn.set_sensitive(False)
            row = Adw.ActionRow()
            row.set_title("Não foi possível concluir a varredura")
            row.set_subtitle(result.error)
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add_result(row)
            return False

        self._last_result = result
        self._export_btn.set_sensitive(True)

        if not result.findings:
            self._results.set_description(f"Concluído em {result.elapsed_sec:.0f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhuma vulnerabilidade encontrada.")
            row.set_subtitle("Tente o escopo Completa (domínio inteiro).")
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add_result(row)
            return False

        self._results.set_description(
            self._summary(result) + ". Clique num achado para ver detalhes.")
        for f in result.findings:
            self._add_result(self._finding_row(f))
        saved = Adw.ActionRow()
        saved.set_title("Relatório salvo — veja na aba Histórico.")
        saved.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        self._add_result(saved)
        return False

    # -- exportar --
    def _on_export(self, _btn) -> None:
        if not self._last_result:
            return
        dialog = Gtk.FileDialog()
        safe = (self._last_result.target or "web").replace("/", "_").replace(":", "")
        dialog.set_initial_name(f"vigia-web-{safe}.txt")
        dialog.save(self.get_root(), None, self._on_export_done)

    def _on_export_done(self, dialog, result) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None or not self._last_result:
            return
        path = gfile.get_path()
        try:
            if path.endswith(".json") and self._last_result.raw:
                content = self._last_result.raw
            else:
                content = backend.result_to_text(self._last_result)
            Path(path).write_text(content, encoding="utf-8")
        except OSError as e:
            print(f"[web] export falhou: {e}", flush=True)


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
        self._group.set_title("Varreduras recentes")
        refresh = Gtk.Button(label="Atualizar")
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda _b: self._reload())
        self._group.set_header_suffix(refresh)
        self._page.add(self._group)
        self._rows: list[Gtk.Widget] = []
        self.connect("map", lambda _w: self._reload())
        self._reload()

    def _reload(self) -> None:
        for r in self._rows:
            self._group.remove(r)
        self._rows = []
        reports = backend.list_recent_reports()
        if not reports:
            row = Adw.ActionRow()
            row.set_title("Nenhuma varredura salva ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            n = len(rep.get("findings", []))
            row = Adw.ActionRow()
            row.set_title(rep.get("target", "?"))
            row.set_subtitle(f"{rep.get('started_at', '?')} · {n} achado(s)")
            row.add_prefix(Gtk.Image.new_from_icon_name("applications-internet-symbolic"))
            path = rep.get("_file")
            if path:
                row.set_activatable(True)
                row.add_suffix(
                    Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
                row.connect("activated", lambda _r, p=path: _open_path(p))
            self._group.add(row)
            self._rows.append(row)


# ============================================================
# Aba Sobre
# ============================================================


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()

    g = Adw.PreferencesGroup()
    g.set_title("Vigia Web Scanner")
    g.set_description(
        "Varredura de vulnerabilidades de aplicações web (wapiti). Rastreia o "
        "site e testa falhas estilo OWASP (XSS, SQLi, inclusão de arquivo…) "
        "contra um alvo autorizado. Complementa o Vuln Scanner no nível da "
        "aplicação. Relatórios salvos com permissão 0600.")
    integra = Adw.ActionRow()
    integra.set_title("Integra")
    integra.set_subtitle(
        "wapiti (CLI). Instale com:  pipx install wapiti3")
    integra.set_subtitle_lines(0)
    integra.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
    g.add(integra)
    reports = Adw.ActionRow()
    reports.set_title("Relatórios")
    reports.set_subtitle(str(backend.REPORTS_DIR) + " — clique para abrir")
    reports.set_subtitle_lines(0)
    reports.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
    reports.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
    reports.set_activatable(True)

    def _open_reports(_r):
        backend.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        _open_path(str(backend.REPORTS_DIR))

    reports.connect("activated", _open_reports)
    g.add(reports)
    page.add(g)

    g_prof = Adw.PreferencesGroup()
    g_prof.set_title("Perfis (escopo do rastreamento)")
    for p in backend.PROFILES:
        row = Adw.ActionRow()
        row.set_title(p.label)
        row.set_subtitle(p.description)
        row.set_subtitle_lines(0)
        row.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        g_prof.add(row)
    page.add(g_prof)

    g_legal = Adw.PreferencesGroup()
    g_legal.set_title("Uso responsável")
    legal = Adw.ActionRow()
    legal.set_title("Varredura ativa — só em alvos autorizados")
    legal.set_subtitle(
        "O wapiti envia requisições de ataque ao site (formulários, parâmetros). "
        "Faça só em aplicações próprias ou com autorização formal por escrito "
        "(Lei 12.737/2012).")
    legal.set_subtitle_lines(0)
    legal.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_legal.add(legal)
    page.add(g_legal)
    return page
