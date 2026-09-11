"""GUI do Vigia Cracker — termo de uso + Auditar / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget` (embarcado pelo shell via `Module.impl`).
Passa pelo portão do termo (gate.build_gated). A auditoria (john/hashcat) roda em
thread, é cancelável e atualiza por `GLib.idle_add`. GTK só aqui.
"""

from __future__ import annotations

import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ... import gate  # noqa: E402
from . import backend  # noqa: E402

# Linhas Adw usam markup Pango por padrão: todo valor vindo de dados (caminho
# escolhido, saída do john/hashcat, senha achada, erro, histórico) passa por
# aqui no sink.
_esc = GLib.markup_escape_text


def build_content() -> Gtk.Widget:
    return gate.build_gated(_build_tool)


def _build_tool() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(
        _AuditView(), "audit", "Auditar", "dialog-password-symbolic")
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
        print(f"[cracker] falha ao abrir {path}: {e}", flush=True)


# ============================================================
# Aba Auditar
# ============================================================


class _AuditView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._handle: backend.ScanProcess | None = None
        self._last_result: backend.CrackResult | None = None
        self._hashfile: str = ""
        self._wordlist: str = ""

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Arquivo de hashes ---
        g_hash = Adw.PreferencesGroup()
        g_hash.set_title("Arquivo de hashes")
        g_hash.set_description(
            "Um arquivo que VOCÊ já possui (ex.: /etc/shadow do seu servidor, ou "
            "hashes exportados de um banco seu).")
        self._hash_row = Adw.ActionRow()
        self._hash_row.set_title("Nenhum arquivo escolhido")
        self._hash_row.add_prefix(
            Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        hash_btn = Gtk.Button(label="Escolher")
        hash_btn.add_css_class("flat")
        hash_btn.set_valign(Gtk.Align.CENTER)
        hash_btn.connect("clicked", self._on_pick_hashfile)
        self._hash_row.add_suffix(hash_btn)
        g_hash.add(self._hash_row)
        page.add(g_hash)

        # --- Wordlist ---
        g_wl = Adw.PreferencesGroup()
        g_wl.set_title("Wordlist")
        g_wl.set_description(
            "Lista de senhas candidatas (ex.: rockyou.txt). Uma senha por linha.")
        self._wl_row = Adw.ActionRow()
        self._wl_row.set_title("Nenhuma wordlist escolhida")
        self._wl_row.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        wl_btn = Gtk.Button(label="Escolher")
        wl_btn.add_css_class("flat")
        wl_btn.set_valign(Gtk.Align.CENTER)
        wl_btn.connect("clicked", self._on_pick_wordlist)
        self._wl_row.add_suffix(wl_btn)
        g_wl.add(self._wl_row)
        page.add(g_wl)

        # --- Opções ---
        g_opt = Adw.PreferencesGroup()
        g_opt.set_title("Opções")

        self._hash_types = backend.HASH_TYPES
        self._type_combo = Adw.ComboRow()
        self._type_combo.set_title("Tipo de hash")
        self._type_combo.add_prefix(Gtk.Image.new_from_icon_name("emblem-system-symbolic"))
        tmodel = Gtk.StringList()
        tdefault = 0
        for i, h in enumerate(self._hash_types):
            tmodel.append(h.label)
            if h.id == backend.DEFAULT_HASH_TYPE:
                tdefault = i
        self._type_combo.set_model(tmodel)
        self._type_combo.set_selected(tdefault)
        self._type_combo.connect("notify::selected", self._on_type_changed)
        g_opt.add(self._type_combo)
        self._on_type_changed(self._type_combo, None)

        self._engines = list(backend.ENGINES)
        self._engine_combo = Adw.ComboRow()
        self._engine_combo.set_title("Engine")
        self._engine_combo.add_prefix(
            Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
        emodel = Gtk.StringList()
        edefault = 0
        for i, e in enumerate(self._engines):
            avail = "" if backend.engine_available(e) else " (não instalado)"
            emodel.append(f"{e}{avail}")
            if e == backend.DEFAULT_ENGINE:
                edefault = i
        self._engine_combo.set_model(emodel)
        self._engine_combo.set_selected(edefault)
        g_opt.add(self._engine_combo)

        self._profiles = backend.PROFILES
        self._prof_combo = Adw.ComboRow()
        self._prof_combo.set_title("Perfil")
        self._prof_combo.add_prefix(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        pmodel = Gtk.StringList()
        pdefault = 0
        for i, p in enumerate(self._profiles):
            pmodel.append(p.label)
            if p.id == backend.DEFAULT_PROFILE:
                pdefault = i
        self._prof_combo.set_model(pmodel)
        self._prof_combo.set_selected(pdefault)
        self._prof_combo.connect("notify::selected", self._on_profile_changed)
        g_opt.add(self._prof_combo)
        page.add(g_opt)
        self._on_profile_changed(self._prof_combo, None)

        # --- Ação ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._btn = Gtk.Button(label="Auditar")
        self._btn.add_css_class("suggested-action")
        self._btn.add_css_class("pill")
        self._btn.connect("clicked", self._on_audit)
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
        self._results.set_title("Resultado")
        page.add(self._results)
        self._result_rows: list[Gtk.Widget] = []
        self._set_results_info("Nenhuma auditoria ainda.",
                               "dialog-information-symbolic")
        self._refresh_banner()

    # -- banner / estado --
    def _refresh_banner(self) -> None:
        if not backend.any_engine_available():
            self._banner.set_title(
                "Nenhuma engine instalada (john/hashcat) — veja a aba Sobre.")
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

    def _on_type_changed(self, combo: Adw.ComboRow, _param) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._hash_types):
            combo.set_subtitle(self._hash_types[idx].note or "")

    def _on_profile_changed(self, combo: Adw.ComboRow, _param) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._profiles):
            combo.set_subtitle(self._profiles[idx].description)

    # -- file pickers --
    def _on_pick_hashfile(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha o arquivo de hashes")
        dialog.open(self.get_root(), None, self._on_hashfile_chosen)

    def _on_hashfile_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            self._hashfile = f.get_path()
            self._hash_row.set_title(_esc(f.get_basename() or self._hashfile))
            self._hash_row.set_subtitle(_esc(self._hashfile))

    def _on_pick_wordlist(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha a wordlist")
        dialog.open(self.get_root(), None, self._on_wordlist_chosen)

    def _on_wordlist_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            self._wordlist = f.get_path()
            self._wl_row.set_title(_esc(f.get_basename() or self._wordlist))
            self._wl_row.set_subtitle(_esc(self._wordlist))

    # -- auditoria --
    def _on_audit(self, *_args) -> None:
        if self._running:
            self._cancel()
            return
        if not self._hashfile:
            self._set_results_info("Escolha um arquivo de hashes primeiro.",
                                   "dialog-error-symbolic")
            return
        if not self._wordlist:
            self._set_results_info("Escolha uma wordlist primeiro.",
                                   "dialog-error-symbolic")
            return
        ti = self._type_combo.get_selected()
        hash_type = (self._hash_types[ti].id
                     if 0 <= ti < len(self._hash_types) else backend.DEFAULT_HASH_TYPE)
        ei = self._engine_combo.get_selected()
        engine = (self._engines[ei]
                  if 0 <= ei < len(self._engines) else backend.DEFAULT_ENGINE)
        pi = self._prof_combo.get_selected()
        profile_id = (self._profiles[pi].id
                      if 0 <= pi < len(self._profiles) else backend.DEFAULT_PROFILE)

        self._handle = backend.ScanProcess()
        self._running = True
        self._btn.set_label("Cancelar")
        self._btn.remove_css_class("suggested-action")
        self._btn.add_css_class("destructive-action")
        self._spinner.start()
        self._export_btn.set_sensitive(False)
        self._set_results_info(
            f"Auditando {_esc(os.path.basename(self._hashfile))} com {_esc(engine)}… "
            "(pode levar de segundos a minutos).", "dialog-password-symbolic")
        threading.Thread(
            target=self._worker,
            args=(self._hashfile, self._wordlist, engine, hash_type, profile_id,
                  self._handle),
            daemon=True).start()

    def _cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self._btn.set_sensitive(False)

    def _worker(self, hashfile, wordlist, engine, hash_type, profile_id, handle) -> None:
        try:
            result = backend.run_crack(
                hashfile, wordlist, engine=engine, hash_type=hash_type,
                profile_id=profile_id, handle=handle)
        except Exception as e:  # pylint: disable=broad-except
            # Nunca deixa a thread morrer sem devolver o controle à UI.
            result = backend.CrackResult(
                hashfile=str(hashfile), error=f"Erro interno: {e}")
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.CrackResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._btn.set_label("Auditar")
        self._btn.remove_css_class("destructive-action")
        self._btn.add_css_class("suggested-action")
        self._btn.set_sensitive(True)

        cancelled = bool(self._handle and self._handle.cancelled)
        self._handle = None
        if cancelled:
            self._export_btn.set_sensitive(False)
            self._set_results_info("Auditoria cancelada.", "process-stop-symbolic")
            return False

        self._clear_results()
        self._results.set_description(None)

        if result.error:
            self._export_btn.set_sensitive(False)
            row = Adw.ActionRow()
            row.set_title("Não foi possível concluir a auditoria")
            row.set_subtitle(_esc(str(result.error)))
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add_result(row)
            return False

        self._last_result = result
        self._export_btn.set_sensitive(True)

        if not result.cracked:
            self._results.set_description(
                f"Concluído em {result.elapsed_sec:.0f}s.")
            row = Adw.ActionRow()
            row.set_title("Nenhuma senha caiu no dicionário (bom sinal).")
            row.set_subtitle(
                "Não prova que todas sejam fortes — tente uma wordlist maior ou "
                "o perfil com regras.")
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add_result(row)
            return False

        pct = result.weak_ratio * 100
        self._results.set_description(
            f"{result.cracked_count} de {result.total_hashes} senhas fracas "
            f"({pct:.0f}%). Troque estas já.")
        for c in result.cracked:
            row = Adw.ActionRow()
            # identificador e senha vêm da saída da ferramenta: escapados aqui.
            row.set_title(_esc(str(c.identifier)))
            row.set_subtitle(_esc(str(c.password)))
            row.set_subtitle_lines(0)
            row.set_subtitle_selectable(True)
            img = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            img.add_css_class("warning")
            row.add_prefix(img)
            self._add_result(row)
        saved = Adw.ActionRow()
        saved.set_title("Relatório salvo — veja na aba Histórico.")
        saved.set_subtitle(
            "O histórico guarda só o identificador do hash fraco (não a senha).")
        saved.set_subtitle_lines(0)
        saved.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        self._add_result(saved)
        return False

    # -- exportar --
    def _on_export(self, _btn: Gtk.Button) -> None:
        if not self._last_result:
            return
        dialog = Gtk.FileDialog()
        safe = os.path.basename(self._last_result.hashfile or "hashes")
        dialog.set_initial_name(f"vigia-cracker-{safe}.txt")
        dialog.save(self.get_root(), None, self._on_export_done)

    def _on_export_done(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None or not self._last_result:
            return
        path = gfile.get_path()
        if not path:  # destino sem caminho local (GVFS/sftp) — não há como gravar
            print("[cracker] export falhou: destino sem caminho local", flush=True)
            return
        try:
            content = backend.result_to_text(self._last_result)
            # Relatório é dado sensível (contém senhas): grava 0600 desde já.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.chmod(path, 0o600)  # se o arquivo já existia com outro modo
        except OSError as e:
            print(f"[cracker] export falhou: {e}", flush=True)


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
        self._group.set_title("Auditorias recentes")
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
            row.set_title("Nenhuma auditoria salva ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            hashfile = str(rep.get("hashfile", "?"))
            cracked = rep.get("cracked_count", 0)
            total = rep.get("total_hashes", 0)
            row = Adw.ActionRow()
            row.set_title(_esc(os.path.basename(hashfile) or hashfile))
            row.set_subtitle(
                f"{_esc(str(rep.get('started_at', '?')))} · "
                f"{_esc(str(cracked))} fraca(s) de {_esc(str(total))}")
            row.set_subtitle_lines(0)
            img = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
            row.add_prefix(img)
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
    g.set_title("Vigia Cracker")
    g.set_description(
        "Auditoria DEFENSIVA de robustez de senhas: dado um arquivo de hashes que "
        "VOCÊ já possui (ex.: /etc/shadow do seu servidor), testa quais caem num "
        "ataque de dicionário — para exigir a troca das fracas. É o que um time de "
        "segurança faz; não serve para descobrir a senha de outra pessoa. "
        "Relatórios 0600 guardam só o identificador do hash fraco.")
    integra = Adw.ActionRow()
    integra.set_title("Integra")
    integra.set_subtitle(
        "john (John the Ripper — CPU, sem setup) ou hashcat (GPU, mais rápido). "
        "Instale com:  sudo dnf install john  ·  sudo dnf install hashcat")
    integra.set_subtitle_lines(0)
    integra.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
    g.add(integra)
    reports = Adw.ActionRow()
    reports.set_title("Relatórios")
    reports.set_subtitle(_esc(str(backend.REPORTS_DIR)) + " — clique para abrir")
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
    g_prof.set_title("Perfis")
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
    legal.set_title("Só em hashes que são SEUS")
    legal.set_subtitle(
        "Audite apenas arquivos de hash de sistemas próprios ou com autorização "
        "formal. Testar hashes de terceiros para descobrir senhas alheias é crime "
        "(Lei 12.737/2012).")
    legal.set_subtitle_lines(0)
    legal.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_legal.add(legal)
    page.add(g_legal)
    return page
