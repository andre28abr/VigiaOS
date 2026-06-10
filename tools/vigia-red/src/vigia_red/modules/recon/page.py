"""GUI do Vigia Recon — termo de uso + abas Investigar / Histórico / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell do VigiaRed via
`Module.impl`. Na 1ª vez exibe o TERMO DE USO (Lei 12.737/2012); só depois de
aceitar, mostra a ferramenta. A investigação roda em thread (não trava a UI) e
atualiza por `GLib.idle_add`. GTK só é importado aqui — `backend.py` é puro.
"""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ... import consent  # noqa: E402
from . import backend  # noqa: E402

_TERM_TEXT = (
    "O Vigia Recon faz <b>reconhecimento passivo</b> (OSINT): consulta apenas "
    "fontes públicas e <b>não toca nos servidores do alvo</b>. Ainda assim, use "
    "somente contra <b>domínios próprios</b> ou com <b>autorização formal por "
    "escrito</b>.\n\n"
    "Acesso não autorizado a dispositivos é crime no Brasil "
    "(<b>Lei 12.737/2012</b>). Você é o único responsável pelo uso desta "
    "ferramenta."
)


def build_content() -> Gtk.Widget:
    """Portão do termo de uso → ferramenta. Aceite fica gravado (vigia_red.consent)."""
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

    def _mount_tool() -> None:
        if stack.get_child_by_name("tool") is None:
            stack.add_named(_build_tool(), "tool")
        stack.set_visible_child_name("tool")

    if consent.is_accepted():
        _mount_tool()
    else:
        stack.add_named(_build_consent_gate(_mount_tool), "gate")
        stack.set_visible_child_name("gate")
    return stack


# ============================================================
# Portão: termo de uso
# ============================================================


def _build_consent_gate(on_accept) -> Gtk.Widget:
    status = Adw.StatusPage()
    status.set_icon_name("dialog-warning-symbolic")
    status.set_title("Antes de começar — termo de uso")

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    box.set_halign(Gtk.Align.CENTER)
    box.set_size_request(540, -1)

    notice = Gtk.Label()
    notice.set_markup(_TERM_TEXT)
    notice.set_wrap(True)
    notice.set_xalign(0)
    notice.set_max_width_chars(60)
    box.append(notice)

    check = Gtk.CheckButton()
    check_lbl = Gtk.Label(
        label="Li e concordo: só vou usar contra sistemas próprios ou com "
              "autorização formal por escrito."
    )
    check_lbl.set_wrap(True)
    check_lbl.set_xalign(0)
    check_lbl.set_max_width_chars(56)
    check.set_child(check_lbl)
    box.append(check)

    btn = Gtk.Button(label="Aceitar e continuar")
    btn.add_css_class("suggested-action")
    btn.add_css_class("pill")
    btn.set_halign(Gtk.Align.CENTER)
    btn.set_sensitive(False)
    check.connect("toggled", lambda c: btn.set_sensitive(c.get_active()))

    def _accept(_b):
        consent.accept()
        on_accept()

    btn.connect("clicked", _accept)
    box.append(btn)

    status.set_child(box)

    header = Adw.HeaderBar()
    header.set_title_widget(
        Adw.WindowTitle(title="Vigia Recon", subtitle="Reconhecimento & OSINT")
    )
    tv = Adw.ToolbarView()
    tv.add_top_bar(header)
    tv.set_content(status)
    return tv


# ============================================================
# Ferramenta (3 abas)
# ============================================================


def _build_tool() -> Gtk.Widget:
    stack = Adw.ViewStack()
    stack.add_titled_with_icon(
        _ReconView(), "recon", "Investigar", "system-search-symbolic")
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
        print(f"[recon] falha ao abrir {path}: {e}", flush=True)


# Categorias de resultado: (atributo, título, ícone)
_CATEGORIES = [
    ("emails", "E-mails", "mail-unread-symbolic"),
    ("hosts", "Subdomínios", "network-server-symbolic"),
    ("ips", "Endereços IP", "network-wired-symbolic"),
    ("urls", "URLs de interesse", "web-browser-symbolic"),
]


# ============================================================
# Aba Investigar
# ============================================================


class _ReconView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._running = False

        self._banner = Adw.Banner()
        self.append(self._banner)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self.append(page)

        # --- Alvo ---
        g_target = Adw.PreferencesGroup()
        g_target.set_title("Alvo autorizado")
        g_target.set_description(
            "Informe só o domínio (ex.: exemplo.com.br). Consulta fontes "
            "públicas (certificados, DNS, buscadores) — passivo, não toca no alvo."
        )
        self._entry = Adw.EntryRow()
        self._entry.set_title("Domínio do alvo")
        self._entry.add_prefix(Gtk.Image.new_from_icon_name("system-search-symbolic"))
        self._entry.connect("entry-activated", self._on_investigate)
        g_target.add(self._entry)
        page.add(g_target)

        # --- Ação ---
        g_action = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        self._spinner = Gtk.Spinner()
        box.append(self._spinner)
        self._btn = Gtk.Button(label="Investigar")
        self._btn.add_css_class("suggested-action")
        self._btn.add_css_class("pill")
        self._btn.connect("clicked", self._on_investigate)
        box.append(self._btn)
        g_action.add(box)
        page.add(g_action)

        # --- Resultados ---
        self._results = Adw.PreferencesGroup()
        self._results.set_title("Resultados")
        page.add(self._results)
        self._result_rows: list[Gtk.Widget] = []
        self._set_results_info("Nenhuma investigação ainda.",
                               "dialog-information-symbolic")

        self._refresh_banner()

    # -- estado / banner --
    def _refresh_banner(self) -> None:
        if not backend.theharvester_available():
            self._banner.set_title(
                "theHarvester não instalado — instale-o (veja a aba Sobre) "
                "para liberar a busca."
            )
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

    def _category_expander(self, items: list[str], title: str, icon: str,
                           cap: int = 100) -> Adw.ExpanderRow:
        exp = Adw.ExpanderRow()
        exp.set_title(title)
        n = len(items)
        exp.set_subtitle(f"{n} encontrado(s)")
        img = Gtk.Image.new_from_icon_name(icon)
        exp.add_prefix(img)
        if not items:
            exp.set_enable_expansion(False)
            return exp
        for value in items[:cap]:
            r = Adw.ActionRow()
            r.set_title(value)
            r.set_title_selectable(True)
            r.set_title_lines(0)
            exp.add_row(r)
        if n > cap:
            more = Adw.ActionRow()
            more.set_title(f"+ {n - cap} mais — veja o relatório completo (Histórico).")
            more.add_css_class("dim-label")
            exp.add_row(more)
        return exp

    # -- investigação --
    def _on_investigate(self, *_args) -> None:
        if self._running:
            return
        raw = self._entry.get_text()
        if not backend.validate_domain(raw):
            self._set_results_info(
                "Domínio inválido. Informe só o domínio, ex.: exemplo.com.br",
                "dialog-error-symbolic")
            return
        dom = backend.normalize_domain(raw)
        self._running = True
        self._btn.set_sensitive(False)
        self._spinner.start()
        self._set_results_info(
            f"Investigando {dom}… consultando fontes públicas (pode levar 1–2 min).",
            "system-search-symbolic")
        threading.Thread(target=self._worker, args=(dom,), daemon=True).start()

    def _worker(self, domain: str) -> None:
        result = backend.run_recon(domain)
        GLib.idle_add(self._apply, result)

    def _apply(self, result: backend.ReconResult) -> bool:
        self._running = False
        self._spinner.stop()
        self._btn.set_sensitive(True)
        self._clear_results()
        self._results.set_description(None)

        if result.error:
            row = Adw.ActionRow()
            row.set_title("Não foi possível concluir a busca")
            row.set_subtitle(result.error)
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            self._add_result(row)
            return False

        if result.total == 0:
            self._results.set_description(f"Concluído em {result.elapsed_sec:.0f}s.")
            row = Adw.ActionRow()
            row.set_title(f"Nenhum dado público encontrado para {result.domain}.")
            row.set_subtitle(
                "As fontes não retornaram nada. Confira o domínio (use a raiz, "
                "ex.: nmap.com) ou tente mais tarde.")
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._add_result(row)
            return False

        self._results.set_description(
            f"{len(result.emails)} e-mail(s) · {len(result.hosts)} subdomínio(s) · "
            f"{len(result.ips)} IP(s) · {len(result.urls)} URL(s) · "
            f"{result.elapsed_sec:.0f}s. Clique numa categoria para abrir."
        )
        for attr, title, icon in _CATEGORIES:
            items = getattr(result, attr)
            self._add_result(self._category_expander(items, title, icon))
        saved = Adw.ActionRow()
        saved.set_title("Relatório salvo — veja na aba Histórico.")
        saved.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        self._add_result(saved)
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
        self._group.set_title("Investigações recentes")
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
            row.set_title("Nenhuma investigação salva ainda.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for rep in reports:
            n = (len(rep.get("emails", [])) + len(rep.get("hosts", []))
                 + len(rep.get("ips", [])) + len(rep.get("urls", [])))
            row = Adw.ActionRow()
            row.set_title(rep.get("domain", "?"))
            row.set_subtitle(
                f"{rep.get('started_at', '?')} · {n} achado(s)")
            row.add_prefix(Gtk.Image.new_from_icon_name("system-search-symbolic"))
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
    g.set_title("Vigia Recon")
    g.set_description(
        "Reconhecimento passivo (OSINT) — mapeia a superfície externa de um "
        "alvo autorizado a partir de fontes públicas. Não toca nos servidores "
        "do alvo. Relatórios salvos localmente com permissão 0600."
    )
    integra = Adw.ActionRow()
    integra.set_title("Integra")
    integra.set_subtitle(
        "theHarvester (CLI). Instale com:  "
        "pipx install git+https://github.com/laramies/theHarvester.git")
    integra.set_subtitle_lines(0)
    integra.add_prefix(
        Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
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

    # Fontes consultadas
    g_src = Adw.PreferencesGroup()
    g_src.set_title("Fontes públicas consultadas")
    g_src.set_description("Padrão do produto — todas passivas e sem chave de API.")
    for s in backend.SOURCES:
        used = s.id in backend.DEFAULT_SOURCE_IDS
        row = Adw.ActionRow()
        row.set_title(s.label)
        row.set_subtitle(s.note)
        row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if used else "list-add-symbolic"))
        if not used:
            tag = Gtk.Label(label="opcional")
            tag.add_css_class("caption")
            tag.add_css_class("dim-label")
            tag.set_valign(Gtk.Align.CENTER)
            row.add_suffix(tag)
        g_src.add(row)
    page.add(g_src)

    # Legal
    g_legal = Adw.PreferencesGroup()
    g_legal.set_title("Uso responsável")
    legal = Adw.ActionRow()
    legal.set_title("Apenas alvos autorizados")
    legal.set_subtitle(
        "Sistemas próprios ou com autorização formal por escrito. "
        "Acesso não autorizado é crime (Lei 12.737/2012).")
    legal.set_subtitle_lines(0)
    legal.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
    g_legal.add(legal)

    revoke = Adw.ActionRow()
    revoke.set_title("Revogar aceite do termo")
    revoke.set_subtitle("Exibe o termo de novo na próxima vez que abrir o módulo.")
    revoke.add_prefix(Gtk.Image.new_from_icon_name("edit-undo-symbolic"))
    revoke.set_activatable(True)

    def _revoke(_r):
        consent.revoke()
        revoke.set_subtitle("Aceite revogado — reabra o Vigia Recon para ver o termo.")

    revoke.connect("activated", _revoke)
    g_legal.add(revoke)
    page.add(g_legal)
    return page
