"""GUI do Vigia YARA — abas Scan / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell do VigiaBlue via
`Module.impl`. O scan roda em thread (não trava a UI) e atualiza por
`GLib.idle_add`. Mesmo padrão dos scanners do VigiaHub (Antivírus/Rootkit).

GTK só é importado aqui (no caminho da GUI) — o `backend.py` continua puro.
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from vigia_common.platform import install_hint  # noqa: E402

from . import backend  # noqa: E402


def build_content() -> Gtk.Widget:
    """Conteúdo auto-contido do Vigia YARA (header próprio + abas)."""
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_ScanView(), "scan", "Scan", "system-search-symbolic")
    stack.add_titled_with_icon(
        _HistoryView(), "hist", "Histórico", "document-open-recent-symbolic"
    )
    stack.add_titled_with_icon(_build_about(), "sobre", "Sobre", "help-about-symbolic")

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
        print(f"[yara] falha ao abrir {path}: {e}", flush=True)


# severidade (do meta da regra) -> (rótulo, ícone, classe-css de cor)
_SEVERITY = {
    "teste": ("Teste", "dialog-information-symbolic", "accent"),
    "baixo": ("Baixo", "dialog-information-symbolic", "accent"),
    "suspeito": ("Suspeito", "dialog-warning-symbolic", "warning"),
    "medio": ("Médio", "dialog-warning-symbolic", "warning"),
    "alto": ("Alto", "dialog-error-symbolic", "error"),
    "critico": ("Crítico", "dialog-error-symbolic", "error"),
}


def _sev(severity: str) -> tuple[str, str, str]:
    return _SEVERITY.get(
        (severity or "").lower(), ("Alerta", "dialog-warning-symbolic", "warning")
    )


# ============================================================
# Aba Scan
# ============================================================


class _ScanView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._target: str | None = None
        self._scanning = False

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Alvo ---
        g_target = Adw.PreferencesGroup()
        g_target.set_title("Alvo")
        g_target.set_description("Pasta ou arquivo para examinar (scan recursivo).")
        self._target_row = Adw.ActionRow()
        self._target_row.set_title("Nenhum alvo selecionado")
        self._target_row.set_subtitle("Clique em Selecionar")
        self._target_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        pick = Gtk.Button(label="Selecionar")
        pick.set_valign(Gtk.Align.CENTER)
        pick.connect("clicked", self._on_pick)
        self._target_row.add_suffix(pick)
        g_target.add(self._target_row)
        page.add(g_target)

        # --- Regras ---
        g_rules = Adw.PreferencesGroup()
        g_rules.set_title("Regras")
        rules = backend.effective_rules()
        using_user = bool(backend.list_rules(backend.RULES_DIR))
        rules_row = Adw.ActionRow()
        rules_row.set_title(f"{len(rules)} conjunto(s) de regras")
        rules_row.set_subtitle(
            "Suas regras" if using_user else "Regras de partida (EICAR + heurísticas)"
        )
        rules_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
        open_rules = Gtk.Button(label="Pasta de regras")
        open_rules.set_valign(Gtk.Align.CENTER)
        open_rules.connect("clicked", self._on_open_rules)
        rules_row.add_suffix(open_rules)
        g_rules.add(rules_row)
        page.add(g_rules)

        # --- Ação (botão fora de card, padrão do projeto) ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._scan_btn = Gtk.Button(label="Escanear")
        self._scan_btn.add_css_class("suggested-action")
        self._scan_btn.add_css_class("pill")
        self._scan_btn.connect("clicked", self._on_scan)
        box.append(self._scan_btn)
        g_action.add(box)
        page.add(g_action)

        # --- Resultados (expanders por alerta) ---
        self._results = Adw.PreferencesGroup()
        self._results.set_title("Resultados")
        page.add(self._results)
        self._result_rows: list[Gtk.Widget] = []
        self._set_results_empty("Nenhum scan executado ainda.")

        self._refresh_banner()

    # -- estado --
    def _refresh_banner(self) -> None:
        if not backend.yara_available():
            self._banner.set_title(
                "yara não instalado. Instale via: " + install_hint("yara")
            )
            self._banner.set_revealed(True)
            self._scan_btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._scan_btn.set_sensitive(True)

    def _add_result(self, row: Gtk.Widget) -> None:
        self._results.add(row)
        self._result_rows.append(row)

    def _clear_results(self) -> None:
        for r in self._result_rows:
            self._results.remove(r)
        self._result_rows = []

    def _set_results_empty(self, text: str) -> None:
        self._clear_results()
        self._results.set_description(None)
        row = Adw.ActionRow()
        row.set_title(text)
        row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        self._add_result(row)

    def _detail(self, title: str, value: str) -> Adw.ActionRow:
        r = Adw.ActionRow()
        r.set_title(title)
        r.set_subtitle(value)
        r.set_subtitle_lines(0)
        r.add_css_class("property")
        return r

    def _match_row(self, m: backend.Match) -> Adw.ExpanderRow:
        label, icon, css = _sev(m.severity)
        exp = Adw.ExpanderRow()
        exp.set_title(Path(m.path).name or m.path)
        exp.set_subtitle(m.description or m.rule)
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
        # detalhes (abrem ao clicar no alerta)
        if m.description:
            exp.add_row(self._detail("O que é", m.description))
        exp.add_row(self._detail("Arquivo", m.path))
        tech = m.rule + (f"  ·  tags: {', '.join(m.tags)}" if m.tags else "")
        exp.add_row(self._detail("Regra (técnico)", tech))
        return exp

    def _add_raw(self, result: backend.ScanResult) -> None:
        raw = (result.raw_output or "").strip()
        if not raw:
            return
        exp = Adw.ExpanderRow()
        exp.set_title("Saída do yara")
        exp.set_subtitle("Resultado bruto da ferramenta")
        exp.add_prefix(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic"))
        lbl = Gtk.Label(label=raw)
        lbl.set_xalign(0)
        lbl.set_wrap(True)
        lbl.set_selectable(True)
        lbl.add_css_class("monospace")
        lbl.add_css_class("caption")
        lbl.set_margin_top(8)
        lbl.set_margin_bottom(8)
        lbl.set_margin_start(12)
        lbl.set_margin_end(12)
        holder = Gtk.ListBoxRow()
        holder.set_activatable(False)
        holder.set_child(lbl)
        exp.add_row(holder)
        self._add_result(exp)

    # -- pickers --
    def _on_pick(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha a pasta para escanear")
        dialog.select_folder(self.get_root(), None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return  # cancelado
        if folder is None:
            return
        self._target = folder.get_path()
        self._target_row.set_title(folder.get_basename() or self._target)
        self._target_row.set_subtitle(self._target)

    def _on_open_rules(self, _btn: Gtk.Button) -> None:
        backend.RULES_DIR.mkdir(parents=True, exist_ok=True)
        _open_path(str(backend.RULES_DIR))

    # -- scan --
    def _on_scan(self, _btn: Gtk.Button) -> None:
        if self._scanning:
            return
        if not self._target:
            self._set_results_empty("Selecione um alvo antes de escanear.")
            return
        self._scanning = True
        self._scan_btn.set_sensitive(False)
        self._spinner.start()
        self._set_results_empty("Escaneando…")
        target = self._target
        threading.Thread(target=self._worker, args=(target,), daemon=True).start()

    def _worker(self, target: str) -> None:
        result = backend.scan(target)
        backend.save_report(result)
        GLib.idle_add(self._apply_results, result)

    def _apply_results(self, result: backend.ScanResult) -> bool:
        self._scanning = False
        self._spinner.stop()
        self._scan_btn.set_sensitive(True)
        self._clear_results()
        self._results.set_description(None)

        if result.error:
            row = Adw.ActionRow()
            row.set_title(f"Erro: {result.error}")
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add_result(row)
            self._add_raw(result)
            return False

        n = len(result.matches)
        files = len({m.path for m in result.matches})
        if n == 0:
            self._results.set_description(
                f"Nada suspeito. {result.rules_count} conjunto(s) de regras · "
                f"{result.elapsed_sec:.1f}s."
            )
            row = Adw.ActionRow()
            row.set_title("Nenhum match — alvo limpo para as regras atuais.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add_result(row)
            self._add_raw(result)
            return False

        self._results.set_description(
            f"{n} alerta(s) em {files} arquivo(s) · {result.rules_count} conjunto(s) de regras · "
            f"{result.elapsed_sec:.1f}s. Clique num alerta para ver o que é."
        )
        for m in result.matches:
            self._add_result(self._match_row(m))
        self._add_raw(result)
        return False


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
        self._group.set_title("Scans recentes")
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
            row.set_title("Nenhum scan salvo ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            n = len(rep.get("matches", []))
            row = Adw.ActionRow()
            row.set_title(rep.get("target", "?"))
            row.set_subtitle(
                f"{rep.get('started_at', '?')} · {n} match(es) · "
                f"{rep.get('rules_count', 0)} regra(s)"
            )
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
    g.set_title("Vigia YARA")
    g.set_description(
        "Caça a malware por regras YARA (webshells, miners, ransomware, "
        "reverse shells). Módulo de Caça a Ameaças do VigiaBlue. Roda 100% "
        "local — nada sai da máquina; relatórios salvos com permissão 0600."
    )
    row = Adw.ActionRow()
    row.set_title("Integra")
    row.set_subtitle("yara (CLI)")
    row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
    g.add(row)
    rules_row = Adw.ActionRow()
    rules_row.set_title("Suas regras")
    rules_row.set_subtitle(str(backend.RULES_DIR))
    rules_row.set_subtitle_lines(0)
    rules_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
    g.add(rules_row)
    page.add(g)
    return page
