"""GUI do Vigia Memory — abas Análise / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell via `Module.impl`.
Roda um plugin do Volatility sobre um dump, em thread → `GLib.idle_add`. GTK só
é importado aqui.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import backend  # noqa: E402

_MAX_DISPLAY = 400


def build_content() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_AnalyzeView(), "an", "Análise", "media-flash-symbolic")
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


class _AnalyzeView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._dump: str | None = None
        self._plugins = backend.plugins()

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        g = Adw.PreferencesGroup()
        g.set_title("Dump de memória")
        g.set_description(
            "Aponte um arquivo de dump de RAM (capturado antes, ex.: com AVML ou "
            "LiME). O Vigia Memory analisa — não captura a memória.")
        self._dump_row = Adw.ActionRow()
        self._dump_row.set_title("Nenhum dump selecionado")
        self._dump_row.set_subtitle("Clique em Selecionar")
        self._dump_row.set_subtitle_lines(0)
        self._dump_row.add_prefix(Gtk.Image.new_from_icon_name("media-flash-symbolic"))
        pick = Gtk.Button(label="Selecionar")
        pick.set_valign(Gtk.Align.CENTER)
        pick.connect("clicked", self._on_pick)
        self._dump_row.add_suffix(pick)
        g.add(self._dump_row)
        page.add(g)

        g_plug = Adw.PreferencesGroup()
        g_plug.set_title("O que analisar")
        self._combo = Adw.ComboRow()
        self._combo.set_title("Plugin")
        self._combo.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
        model = Gtk.StringList()
        for p in self._plugins:
            model.append(f"{p.label} ({p.os})")
        self._combo.set_model(model)
        self._combo.set_selected(0)
        self._combo.connect("notify::selected", self._on_plugin_changed)
        g_plug.add(self._combo)
        page.add(g_plug)
        self._on_plugin_changed(self._combo, None)

        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._run_btn = Gtk.Button(label="Analisar")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.add_css_class("pill")
        self._run_btn.connect("clicked", self._on_run)
        box.append(self._run_btn)
        g_action.add(box)
        page.add(g_action)

        self._results = Adw.PreferencesGroup()
        self._results.set_title("Resultado")
        page.add(self._results)
        self._rows: list[Gtk.Widget] = []
        self._set_empty("Selecione um dump e um plugin, e clique em Analisar.")
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        if not backend.vol_available():
            self._banner.set_title(
                "Volatility 3 não encontrado — veja a aba Sobre para instalar.")
            self._banner.set_revealed(True)
            self._run_btn.set_sensitive(False)
        else:
            self._banner.set_revealed(False)
            self._run_btn.set_sensitive(True)

    def _on_plugin_changed(self, combo: Adw.ComboRow, _p) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._plugins):
            self._combo.set_subtitle(self._plugins[idx].description)

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

    def _on_pick(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha o dump de memória")
        dialog.open(self.get_root(), None, self._on_dump_chosen)

    def _on_dump_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            self._dump = f.get_path()
            self._dump_row.set_title(f.get_basename() or self._dump)
            self._dump_row.set_subtitle(self._dump)

    def _on_run(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        if not self._dump:
            self._set_empty("Selecione um dump antes de analisar.")
            return
        idx = self._combo.get_selected()
        if not (0 <= idx < len(self._plugins)):
            return
        plugin = self._plugins[idx].id
        self._running = True
        self._run_btn.set_sensitive(False)
        self._spinner.start()
        self._set_empty("Analisando o dump (pode demorar)…")
        threading.Thread(target=self._worker, args=(self._dump, plugin),
                         daemon=True).start()

    def _worker(self, dump: str, plugin: str) -> None:
        result = backend.run_plugin(dump, plugin)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.MemResult) -> bool:
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

        if not result.rows:
            self._results.set_description(
                f"Sem resultados para este plugin · {result.elapsed_sec:.1f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhuma linha retornada.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._add(row)
            return False

        shown = result.rows[:_MAX_DISPLAY]
        extra = len(result.rows) - len(shown)
        self._results.set_description(
            f"{len(result.rows)} linha(s) · {result.elapsed_sec:.1f}s."
            + (f" Mostrando as primeiras {_MAX_DISPLAY}." if extra > 0 else "")
            + " Clique numa linha para ver os campos.")
        for r in shown:
            self._add(self._row_widget(result.columns, r))
        return False

    def _row_widget(self, columns: list[str], row: dict) -> Adw.ExpanderRow:
        exp = Adw.ExpanderRow()
        exp.set_title(backend.row_summary(columns, row))
        exp.set_subtitle_lines(0)
        for c in columns:
            v = row.get(c)
            if v in (None, ""):
                continue
            r = Adw.ActionRow()
            r.set_title(c)
            r.set_subtitle(str(v))
            r.set_subtitle_lines(0)
            r.add_css_class("property")
            exp.add_row(r)
        return exp


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Vigia Memory")
    g.set_description(
        "Forense de dumps de memória RAM com o Volatility 3. Analisa um dump "
        "capturado para listar processos, conexões, comandos e código injetado. "
        "Módulo de Forense do VigiaBlue. Roda 100% local.")
    row = Adw.ActionRow()
    row.set_title("Instalar o Volatility 3")
    row.set_subtitle("pipx install volatility3  (ou)  pip install --user volatility3")
    row.set_subtitle_lines(0)
    row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
    g.add(row)
    cap = Adw.ActionRow()
    cap.set_title("Como capturar um dump")
    cap.set_subtitle("Linux: AVML ou LiME (exigem root). O Vigia Memory analisa "
                     "o dump — ele não captura a RAM.")
    cap.set_subtitle_lines(0)
    cap.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
    g.add(cap)
    page.add(g)
    return page
