"""GUI do Vigia Network Scanner — termo de uso + Varredura / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget` (embarcado pelo shell via `Module.impl`).
Passa pelo portão do termo (gate.build_gated). A varredura roda em thread e
atualiza por `GLib.idle_add`. GTK só aqui — `backend.py` é puro.
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ... import gate, handoff  # noqa: E402
from . import backend  # noqa: E402


def build_content() -> Gtk.Widget:
    return gate.build_gated(_build_tool)


def _build_tool() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(
        _ScanView(), "scan", "Varredura", "network-wired-symbolic")
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
        print(f"[netscan] falha ao abrir {path}: {e}", flush=True)


# ============================================================
# Aba Varredura
# ============================================================


class _ScanView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False
        self._last_result: backend.ScanResult | None = None
        self.connect("map", lambda *_a: self._consume_handoff())

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Alvo ---
        g_target = Adw.PreferencesGroup()
        g_target.set_title("Alvo autorizado")
        g_target.set_description(
            "Domínio, IP ou faixa (ex.: exemplo.com.br, 192.168.0.10, "
            "192.168.0.0/24). Varredura ATIVA: conecta nas portas do alvo — "
            "use só com autorização.")
        self._entry = Adw.EntryRow()
        self._entry.set_title("Domínio / IP / faixa")
        self._entry.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        self._entry.connect("entry-activated", self._on_scan)
        g_target.add(self._entry)
        page.add(g_target)

        # --- Perfil ---
        g_prof = Adw.PreferencesGroup()
        g_prof.set_title("Perfil")
        self._profiles = backend.PROFILES
        self._combo = Adw.ComboRow()
        self._combo.set_title("Profundidade")
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

        # --- Opções (portas + scripts) ---
        g_opt = Adw.PreferencesGroup()
        g_opt.set_title("Opções")
        self._ports = Adw.EntryRow()
        self._ports.set_title("Portas (opcional) — ex.: 80,443,8000-8100")
        self._ports.add_prefix(Gtk.Image.new_from_icon_name("network-transmit-receive-symbolic"))
        g_opt.add(self._ports)

        self._scripts = backend.SCRIPTS
        self._script_combo = Adw.ComboRow()
        self._script_combo.set_title("Scripts NSE")
        self._script_combo.add_prefix(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        smodel = Gtk.StringList()
        for s in self._scripts:
            smodel.append(s.label)
        self._script_combo.set_model(smodel)
        self._script_combo.set_selected(0)
        self._script_combo.connect("notify::selected", self._on_script_changed)
        g_opt.add(self._script_combo)
        page.add(g_opt)
        self._on_script_changed(self._script_combo, None)

        # --- Modo admin ---
        g_admin = Adw.PreferencesGroup()
        g_admin.set_title("Modo admin")
        self._admin_row = Adw.SwitchRow()
        self._admin_row.set_title("Liberar SYN / UDP / detecção de SO")
        self._admin_row.set_subtitle(
            "Usa pkexec (pede senha a cada varredura). Sem isso, scan TCP comum "
            "sem root. Necessário para os perfis marcados “admin”.")
        self._admin_row.add_prefix(Gtk.Image.new_from_icon_name("security-medium-symbolic"))
        g_admin.add(self._admin_row)
        page.add(g_admin)

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
        self._results.set_title("Resultados")
        page.add(self._results)
        self._result_rows: list[Gtk.Widget] = []
        self._set_results_info("Nenhuma varredura ainda.",
                               "dialog-information-symbolic")
        self._refresh_banner()

    # -- banner / estado --
    def _refresh_banner(self) -> None:
        if not backend.nmap_available():
            self._banner.set_title(
                "nmap não instalado. Instale com:  sudo dnf install nmap")
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

    def _on_script_changed(self, combo: Adw.ComboRow, _param) -> None:
        idx = combo.get_selected()
        if 0 <= idx < len(self._scripts):
            combo.set_subtitle(self._scripts[idx].description)

    @staticmethod
    def _port_widget(p: backend.Port) -> Gtk.Widget:
        parts = []
        if p.service:
            parts.append(p.service)
        extra = " ".join(x for x in (p.product, p.version) if x)
        if extra:
            parts.append(extra)
        subtitle = " · ".join(parts) or "aberta"
        icon = "network-transmit-receive-symbolic"
        if p.scripts:
            row = Adw.ExpanderRow()
            row.set_title(f"Porta {p.port}/{p.proto.upper()}")
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            for s in p.scripts:
                sr = Adw.ActionRow()
                sr.set_title(s)
                sr.set_title_lines(0)
                sr.set_title_selectable(True)
                sr.add_css_class("monospace")
                sr.add_css_class("caption")
                row.add_row(sr)
            return row
        row = Adw.ActionRow()
        row.set_title(f"Porta {p.port}/{p.proto.upper()}")
        row.set_subtitle(subtitle)
        row.set_subtitle_lines(0)
        row.set_title_selectable(True)
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        return row

    def _host_expander(self, host: backend.Host, single: bool) -> Adw.ExpanderRow:
        exp = Adw.ExpanderRow()
        exp.set_title(host.hostname or host.address)
        n = len(host.ports)
        sub = f"{n} porta(s) aberta(s)"
        if host.hostname and host.address:
            sub = f"{host.address} · {sub}"
        if host.os:
            sub += f" · SO: {host.os}"
        exp.set_subtitle(sub)
        exp.set_subtitle_lines(0)
        exp.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        exp.set_expanded(single or n <= 8)
        for p in host.ports:
            exp.add_row(self._port_widget(p))
        return exp

    # -- scan --
    def _on_scan(self, *_args) -> None:
        if self._running:
            return
        raw = self._entry.get_text()
        if not backend.validate_target(raw):
            self._set_results_info(
                "Alvo inválido. Use domínio, IP ou faixa (ex.: 192.168.0.0/24).",
                "dialog-error-symbolic")
            return
        idx = self._combo.get_selected()
        profile_id = (self._profiles[idx].id
                      if 0 <= idx < len(self._profiles) else backend.DEFAULT_PROFILE)
        sidx = self._script_combo.get_selected()
        scripts = (self._scripts[sidx].value
                   if 0 <= sidx < len(self._scripts) else "")
        ports = self._ports.get_text().strip()
        elevated = self._admin_row.get_active()

        self._running = True
        self._btn.set_sensitive(False)
        self._spinner.start()
        self._set_results_info(
            f"Escaneando {backend.normalize_target(raw)}… (pode levar de "
            "segundos a minutos, conforme o perfil).", "network-wired-symbolic")
        threading.Thread(
            target=self._worker,
            args=(raw, profile_id, elevated, ports, scripts), daemon=True).start()

    def _worker(self, target, profile_id, elevated, ports, scripts) -> None:
        result = backend.run_scan(
            target, profile_id, elevated=elevated, ports=ports, scripts=scripts)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.ScanResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._btn.set_sensitive(True)
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
        hosts_with_ports = [h for h in result.hosts if h.ports]

        # Ping sweep / descoberta: hosts vivos sem varrer portas.
        if not hosts_with_ports and result.hosts:
            self._results.set_description(
                f"{len(result.hosts)} host(s) vivo(s) · {result.elapsed_sec:.0f}s.")
            for h in result.hosts:
                row = Adw.ActionRow()
                row.set_title(h.hostname or h.address)
                if h.hostname and h.address:
                    row.set_subtitle(h.address)
                row.set_title_selectable(True)
                row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
                self._add_result(row)
            return False

        if not hosts_with_ports:
            self._results.set_description(f"Concluído em {result.elapsed_sec:.0f}s.")
            row = Adw.ActionRow()
            row.set_title(f"Nenhuma porta aberta encontrada em {result.target}.")
            row.set_subtitle(
                "O alvo pode estar protegido por firewall, ou tente o perfil "
                "Completa (todas as portas).")
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic"))
            self._add_result(row)
            return False

        single = len(hosts_with_ports) == 1
        self._results.set_description(
            f"{len(hosts_with_ports)} host(s) · {result.open_ports} porta(s) "
            f"aberta(s) · {result.elapsed_sec:.0f}s. Clique num host para abrir.")
        for h in hosts_with_ports:
            self._add_result(self._host_expander(h, single))
        saved = Adw.ActionRow()
        saved.set_title("Relatório salvo — veja na aba Histórico.")
        saved.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        self._add_result(saved)
        return False

    # -- handoff (Recon → Scanner) --
    def _consume_handoff(self) -> None:
        target = handoff.take_scan_target()
        if target:
            self._entry.set_text(target)

    # -- exportar (.txt legível ou .xml cru do nmap) --
    def _on_export(self, _btn: Gtk.Button) -> None:
        if not self._last_result:
            return
        dialog = Gtk.FileDialog()
        safe = (self._last_result.target or "scan").replace("/", "_")
        dialog.set_initial_name(f"vigia-scan-{safe}.txt")
        dialog.save(self.get_root(), None, self._on_export_done)

    def _on_export_done(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        if gfile is None or not self._last_result:
            return
        path = gfile.get_path()
        try:
            if path.endswith(".xml") and self._last_result.raw_xml:
                content = self._last_result.raw_xml
            else:
                content = backend.result_to_text(self._last_result)
            Path(path).write_text(content, encoding="utf-8")
        except OSError as e:
            print(f"[netscan] export falhou: {e}", flush=True)


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
            ports = sum(len(h.get("ports", [])) for h in rep.get("hosts", []))
            row = Adw.ActionRow()
            row.set_title(rep.get("target", "?"))
            row.set_subtitle(
                f"{rep.get('started_at', '?')} · {ports} porta(s) aberta(s)")
            row.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
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
    g.set_title("Vigia Network Scanner")
    g.set_description(
        "Reconhecimento ATIVO: descobre portas abertas, serviços/versões e (no "
        "modo admin) o Sistema Operacional de um alvo autorizado, via nmap. "
        "Complementa o Vigia Recon (passivo). Relatórios salvos com permissão 0600.")
    integra = Adw.ActionRow()
    integra.set_title("Integra")
    integra.set_subtitle("nmap (CLI). Instale com:  sudo dnf install nmap")
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
    g_prof.set_title("Perfis de varredura")
    for p in backend.PROFILES:
        row = Adw.ActionRow()
        row.set_title(p.label)
        row.set_subtitle(p.description)
        row.set_subtitle_lines(0)
        row.add_prefix(Gtk.Image.new_from_icon_name(
            "security-medium-symbolic" if p.needs_root else "view-list-symbolic"))
        g_prof.add(row)
    page.add(g_prof)

    g_legal = Adw.PreferencesGroup()
    g_legal.set_title("Uso responsável")
    legal = Adw.ActionRow()
    legal.set_title("Varredura ativa — só em alvos autorizados")
    legal.set_subtitle(
        "Diferente do Recon (passivo), o Scanner conecta nas portas do alvo. "
        "Faça só em sistemas próprios ou com autorização formal por escrito "
        "(Lei 12.737/2012).")
    legal.set_subtitle_lines(0)
    legal.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_legal.add(legal)
    page.add(g_legal)
    return page
