"""GUI do Vigia Timeline — abas Linha do tempo / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell via `Module.impl`.
Abre um export json_line, ou gera/analisa via plaso, em thread → `GLib.idle_add`.
GTK só é importado aqui.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import backend  # noqa: E402

_MAX_DISPLAY = 600


def build_content() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(_TimelineView(), "tl", "Linha do tempo",
                               "x-office-calendar-symbolic")
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


class _TimelineView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        g = Adw.PreferencesGroup()
        g.set_title("Fonte da linha do tempo")
        g.set_description(
            "Abra um export pronto (json_line) — não precisa do plaso — ou gere "
            "uma timeline de uma pasta/arquivo (precisa do plaso, pode demorar).")

        self._spinner = Gtk.Spinner()

        open_row = Adw.ActionRow()
        open_row.set_title("Abrir export de timeline (json_line)")
        open_row.set_subtitle("Arquivo gerado pelo psort -o json_line")
        open_row.set_subtitle_lines(0)
        open_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
        ob = Gtk.Button(label="Abrir")
        ob.set_valign(Gtk.Align.CENTER)
        ob.connect("clicked", self._on_open_export)
        open_row.add_suffix(ob)
        g.add(open_row)

        storage_row = Adw.ActionRow()
        storage_row.set_title("Analisar um storage .plaso")
        storage_row.set_subtitle("Roda o psort sobre um .plaso existente")
        storage_row.set_subtitle_lines(0)
        storage_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        self._sb = Gtk.Button(label="Selecionar .plaso")
        self._sb.set_valign(Gtk.Align.CENTER)
        self._sb.connect("clicked", self._on_open_storage)
        storage_row.add_suffix(self._sb)
        g.add(storage_row)

        gen_row = Adw.ActionRow()
        gen_row.set_title("Gerar de uma pasta/arquivo")
        gen_row.set_subtitle("Roda log2timeline + psort (lento)")
        gen_row.set_subtitle_lines(0)
        gen_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        self._gb = Gtk.Button(label="Selecionar fonte")
        self._gb.set_valign(Gtk.Align.CENTER)
        self._gb.connect("clicked", self._on_generate)
        gen_row.add_suffix(self._gb)
        gen_row.add_suffix(self._spinner)
        g.add(gen_row)
        page.add(g)

        self._results = Adw.PreferencesGroup()
        self._results.set_title("Eventos")
        page.add(self._results)
        self._rows: list[Gtk.Widget] = []
        self._set_empty("Escolha uma fonte acima para ver a linha do tempo.")
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        avail = backend.plaso_available()
        if not avail:
            self._banner.set_title(
                "plaso não encontrado — você ainda pode abrir um export "
                "json_line. Veja a aba Sobre para instalar o plaso.")
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)
        self._sb.set_sensitive(backend.psort_bin() is not None)
        self._gb.set_sensitive(avail)

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
    def _on_open_export(self, _btn: Gtk.Button) -> None:
        d = Gtk.FileDialog()
        d.set_title("Escolha o export json_line")
        d.open(self.get_root(), None, self._chosen_export)

    def _chosen_export(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            path = f.get_path()
            self._start(lambda: backend.analyze_psort_file(path))

    def _on_open_storage(self, _btn: Gtk.Button) -> None:
        d = Gtk.FileDialog()
        d.set_title("Escolha o arquivo .plaso")
        d.open(self.get_root(), None, self._chosen_storage)

    def _chosen_storage(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            path = f.get_path()
            self._start(lambda: backend.analyze_storage(path))

    def _on_generate(self, _btn: Gtk.Button) -> None:
        d = Gtk.FileDialog()
        d.set_title("Escolha a pasta a analisar")
        d.select_folder(self.get_root(), None, self._chosen_source)

    def _chosen_source(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if folder and folder.get_path():
            path = folder.get_path()
            self._start(lambda: backend.run_timeline(path))

    # -- run --
    def _start(self, work) -> None:
        if self._running:
            return
        self._running = True
        self._gb.set_sensitive(False)
        self._sb.set_sensitive(False)
        self._spinner.start()
        self._set_empty("Construindo a linha do tempo (pode demorar)…")
        threading.Thread(target=self._worker, args=(work,), daemon=True).start()

    def _worker(self, work) -> None:
        result = work()
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.TimelineResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._refresh_banner()
        self._clear()
        self._results.set_description(None)

        if result.error:
            row = Adw.ActionRow()
            row.set_title("Não foi possível montar a linha do tempo")
            row.set_subtitle(result.error)
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add(row)
            return False

        if not result.events:
            self._results.set_description(
                f"Nenhum evento · {result.elapsed_sec:.1f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhum evento na fonte analisada.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._add(row)
            return False

        shown = result.events[:_MAX_DISPLAY]
        extra = result.total - len(shown)
        self._results.set_description(
            f"{result.total} evento(s) · {result.elapsed_sec:.1f}s."
            + (f" Mostrando os primeiros {_MAX_DISPLAY}." if extra > 0 else ""))
        for ev in shown:
            self._add(self._event_row(ev))
        return False

    def _event_row(self, ev: backend.Event) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(ev.timestamp or "(sem data)")
        row.set_subtitle(ev.message or ev.data_type or "—")
        row.set_subtitle_lines(0)
        row.add_prefix(Gtk.Image.new_from_icon_name("x-office-calendar-symbolic"))
        if ev.data_type:
            pill = Gtk.Label(label=ev.data_type)
            pill.add_css_class("caption")
            pill.add_css_class("dim-label")
            pill.set_valign(Gtk.Align.CENTER)
            row.add_suffix(pill)
        return row


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Vigia Timeline")
    g.set_description(
        "Super-timeline forense com o plaso. Reúne eventos de muitas fontes "
        "(arquivos, logs, registro) numa única linha do tempo ordenada, para "
        "reconstruir o que aconteceu e quando. Módulo de Forense do VigiaBlue. "
        "Roda 100% local.")
    g.add(_about_row(
        "Abrir export pronto",
        "Se você já tem um arquivo json_line (do psort), abra direto — não "
        "precisa do plaso instalado."))
    g.add(_about_row(
        "Instalar o plaso",
        "pipx install plaso  (fornece log2timeline.py e psort.py). Gerar uma "
        "timeline de uma pasta pode levar minutos."))
    page.add(g)
    return page


def _about_row(title: str, subtitle: str) -> Adw.ActionRow:
    r = Adw.ActionRow()
    r.set_title(title)
    r.set_subtitle(subtitle)
    r.set_subtitle_lines(0)
    r.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
    return r
