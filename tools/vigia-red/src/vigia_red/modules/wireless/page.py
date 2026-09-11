"""GUI do Vigia Wireless — termo de uso + Auditar / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget` (embarcado pelo shell via `Module.impl`).
Passa pelo portão do termo (gate.build_gated). O TESTE do handshake (aircrack-ng)
roda em thread, é cancelável e atualiza por `GLib.idle_add`. GTK só aqui.

O app só faz o TESTE de um `.cap` que você já capturou — não captura nada
sozinho. A captura (airodump-ng, modo monitor + root) é feita fora do app; a aba
Sobre documenta o passo a passo e monta os comandos de exemplo.
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
# escolhido, senha achada, BSSID digitado, erro, histórico) passa por aqui no sink.
_esc = GLib.markup_escape_text


def build_content() -> Gtk.Widget:
    return gate.build_gated(_build_tool)


def _build_tool() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(
        _AuditView(), "audit", "Auditar", "network-wireless-symbolic")
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
        print(f"[wireless] falha ao abrir {path}: {e}", flush=True)


# ============================================================
# Aba Auditar
# ============================================================


class _AuditView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._handle: backend.ScanProcess | None = None
        self._last_result: backend.AuditResult | None = None
        self._capture: str = ""
        self._wordlist: str = ""

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Captura ---
        g_cap = Adw.PreferencesGroup()
        g_cap.set_title("Captura (.cap) da SUA rede")
        g_cap.set_description(
            "Arquivo .cap/.pcap com o handshake WPA da sua própria rede. A captura "
            "é feita FORA do app (veja a aba Sobre).")
        self._cap_row = Adw.ActionRow()
        self._cap_row.set_title("Nenhuma captura escolhida")
        self._cap_row.add_prefix(
            Gtk.Image.new_from_icon_name("network-wireless-symbolic"))
        cap_btn = Gtk.Button(label="Escolher")
        cap_btn.add_css_class("flat")
        cap_btn.set_valign(Gtk.Align.CENTER)
        cap_btn.connect("clicked", self._on_pick_capture)
        self._cap_row.add_suffix(cap_btn)
        g_cap.add(self._cap_row)
        page.add(g_cap)

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
        self._bssid_row = Adw.EntryRow()
        self._bssid_row.set_title("BSSID (opcional) — AA:BB:CC:DD:EE:FF")
        self._bssid_row.add_prefix(
            Gtk.Image.new_from_icon_name("network-wireless-hotspot-symbolic"))
        g_opt.add(self._bssid_row)
        page.add(g_opt)

        # --- Ação ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._btn = Gtk.Button(label="Testar senha")
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
        self._set_results_info("Nenhum teste ainda.",
                               "dialog-information-symbolic")
        self._refresh_banner()

    # -- banner / estado --
    def _refresh_banner(self) -> None:
        if not backend.aircrack_available():
            self._banner.set_title(
                "aircrack-ng não instalado — veja a aba Sobre para instalar.")
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

    # -- file pickers --
    def _on_pick_capture(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha a captura (.cap) da sua rede")
        dialog.open(self.get_root(), None, self._on_capture_chosen)

    def _on_capture_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f and f.get_path():
            self._capture = f.get_path()
            self._cap_row.set_title(_esc(f.get_basename() or self._capture))
            self._cap_row.set_subtitle(_esc(self._capture))

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
        if not self._capture:
            self._set_results_info("Escolha uma captura (.cap) primeiro.",
                                   "dialog-error-symbolic")
            return
        if not self._wordlist:
            self._set_results_info("Escolha uma wordlist primeiro.",
                                   "dialog-error-symbolic")
            return
        bssid = (self._bssid_row.get_text() or "").strip()
        if bssid and not backend.validate_bssid(bssid):
            self._set_results_info(
                "BSSID inválido. Use o formato AA:BB:CC:DD:EE:FF (ou deixe vazio).",
                "dialog-error-symbolic")
            return

        self._handle = backend.ScanProcess()
        self._running = True
        self._btn.set_label("Cancelar")
        self._btn.remove_css_class("suggested-action")
        self._btn.add_css_class("destructive-action")
        self._spinner.start()
        self._export_btn.set_sensitive(False)
        self._set_results_info(
            f"Testando {_esc(os.path.basename(self._capture))} contra a wordlist… "
            "(pode levar de segundos a minutos).", "network-wireless-symbolic")
        threading.Thread(
            target=self._worker,
            args=(self._capture, self._wordlist, bssid, self._handle),
            daemon=True).start()

    def _cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self._btn.set_sensitive(False)

    def _worker(self, capture, wordlist, bssid, handle) -> None:
        try:
            result = backend.run_audit(
                capture, wordlist, bssid=bssid, handle=handle)
        except Exception as e:  # pylint: disable=broad-except
            # Nunca deixa a thread morrer sem devolver o controle à UI.
            result = backend.AuditResult(
                capture=str(capture), error=f"Erro interno: {e}")
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.AuditResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._btn.set_label("Testar senha")
        self._btn.remove_css_class("destructive-action")
        self._btn.add_css_class("suggested-action")
        self._btn.set_sensitive(True)

        cancelled = bool(self._handle and self._handle.cancelled)
        self._handle = None
        if cancelled:
            self._export_btn.set_sensitive(False)
            self._set_results_info("Teste cancelado.", "process-stop-symbolic")
            return False

        self._clear_results()
        self._results.set_description(None)

        if result.error:
            self._export_btn.set_sensitive(False)
            row = Adw.ActionRow()
            row.set_title("Não foi possível concluir o teste")
            row.set_subtitle(_esc(str(result.error)))
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add_result(row)
            return False

        self._last_result = result
        self._export_btn.set_sensitive(True)

        if result.found:
            self._results.set_description(
                f"Concluído em {result.elapsed_sec:.0f}s.")
            row = Adw.ActionRow()
            row.set_title("Senha FRACA — caiu no dicionário testado")
            # A senha vem da saída do aircrack: escapada aqui.
            row.set_subtitle(_esc(str(result.password)))
            row.set_subtitle_lines(0)
            row.set_subtitle_selectable(True)
            img = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            img.add_css_class("error")
            row.add_prefix(img)
            self._add_result(row)
            tip = Adw.ActionRow()
            tip.set_title("Troque a senha do seu Wi-Fi por uma frase longa e única.")
            tip.set_subtitle("Relatório salvo — veja na aba Histórico.")
            tip.set_subtitle_lines(0)
            tip.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            self._add_result(tip)
            return False

        self._results.set_description(f"Concluído em {result.elapsed_sec:.0f}s.")
        row = Adw.ActionRow()
        row.set_title("A senha resistiu ao dicionário testado")
        row.set_subtitle(
            "Bom sinal — mas não prova que seja inquebrável. "
            "Relatório salvo — veja na aba Histórico.")
        row.set_subtitle_lines(0)
        img = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        img.add_css_class("success")
        row.add_prefix(img)
        self._add_result(row)
        return False

    # -- exportar --
    def _on_export(self, _btn: Gtk.Button) -> None:
        if not self._last_result:
            return
        dialog = Gtk.FileDialog()
        safe = os.path.basename(self._last_result.capture or "wifi")
        dialog.set_initial_name(f"vigia-wireless-{safe}.txt")
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
            print("[wireless] export falhou: destino sem caminho local", flush=True)
            return
        try:
            content = backend.result_to_text(self._last_result)
            # Relatório é dado sensível (pode conter a senha): grava 0600 desde já.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.chmod(path, 0o600)  # se o arquivo já existia com outro modo
        except OSError as e:
            print(f"[wireless] export falhou: {e}", flush=True)


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
        self._group.set_title("Testes recentes")
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
            row.set_title("Nenhum teste salvo ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            capture = str(rep.get("capture", "?"))
            found = bool(rep.get("found", False))
            bssid = str(rep.get("bssid", "") or "")
            row = Adw.ActionRow()
            row.set_title(_esc(os.path.basename(capture) or capture))
            verdict = "senha FRACA" if found else "resistiu ao dicionário"
            sub = f"{_esc(str(rep.get('started_at', '?')))} · {verdict}"
            if bssid:
                sub += f" · {_esc(bssid)}"
            row.set_subtitle(sub)
            row.set_subtitle_lines(0)
            icon = "dialog-error-symbolic" if found else "network-wireless-symbolic"
            img = Gtk.Image.new_from_icon_name(icon)
            if found:
                img.add_css_class("error")
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
    g.set_title("Vigia Wireless")
    g.set_description(
        "Auditoria da SUA própria rede Wi-Fi: testa se a senha resiste a um ataque "
        "de dicionário sobre um handshake que você capturou. Responde 'minha senha "
        "aguenta?' — não serve para acessar rede alheia. O app faz só o TESTE do "
        ".cap; não captura sozinho. Relatórios 0600 (a senha não vai no histórico).")
    integra = Adw.ActionRow()
    integra.set_title("Integra")
    integra.set_subtitle(
        "aircrack-ng (suíte de auditoria Wi-Fi). Instale com:  "
        "sudo dnf install aircrack-ng")
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

    # --- Como capturar o handshake (fora do app) ---
    airodump = backend.build_airodump_cmd(
        "wlan0mon", "AA:BB:CC:DD:EE:FF", "6", "/root/teste/handshake")
    deauth = backend.build_aireplay_deauth_cmd(
        "wlan0mon", "AA:BB:CC:DD:EE:FF")

    g_cap = Adw.PreferencesGroup()
    g_cap.set_title("Como capturar o handshake (passo a passo)")
    g_cap.set_description(
        "A CAPTURA é feita FORA deste app e exige placa em modo monitor + root. "
        "O VigiaOS só faz o TESTE do .cap. Faça isto SÓ na SUA rede.")

    step1 = Adw.ActionRow()
    step1.set_title("1. Coloque a placa em modo monitor")
    step1.set_subtitle(_esc("sudo airmon-ng start wlan0   (cria wlan0mon)"))
    step1.set_subtitle_lines(0)
    step1.set_subtitle_selectable(True)
    step1.add_prefix(Gtk.Image.new_from_icon_name("emblem-system-symbolic"))
    g_cap.add(step1)

    step2 = Adw.ActionRow()
    step2.set_title("2. Capture o handshake da SUA rede")
    # comando montado pelo backend (dado): escapado aqui.
    step2.set_subtitle(_esc("sudo " + " ".join(airodump)))
    step2.set_subtitle_lines(0)
    step2.set_subtitle_selectable(True)
    step2.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-symbolic"))
    g_cap.add(step2)

    step3 = Adw.ActionRow()
    step3.set_title("3. (Opcional) Force um cliente SEU a reconectar")
    step3.set_subtitle(_esc("sudo " + " ".join(deauth))
                       + "  — derruba conexões; SÓ na sua rede.")
    step3.set_subtitle_lines(0)
    step3.set_subtitle_selectable(True)
    step3.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_cap.add(step3)

    step4 = Adw.ActionRow()
    step4.set_title("4. Traga o .cap gerado para a aba Auditar")
    step4.set_subtitle(
        "Aponte o arquivo /root/teste/handshake-01.cap e uma wordlist, e teste.")
    step4.set_subtitle_lines(0)
    step4.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
    g_cap.add(step4)
    page.add(g_cap)

    g_legal = Adw.PreferencesGroup()
    g_legal.set_title("Uso responsável")
    legal = Adw.ActionRow()
    legal.set_title("Só na SUA rede")
    legal.set_subtitle(
        "Capturar handshake e testar senha de rede alheia é acesso não autorizado "
        "— crime no Brasil (Lei 12.737/2012). Use apenas na sua própria rede ou "
        "com autorização formal por escrito.")
    legal.set_subtitle_lines(0)
    legal.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_legal.add(legal)
    page.add(g_legal)
    return page
