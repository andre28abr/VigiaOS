"""GUI do Vigia Intel — abas Verificar / IOCs / Sobre.

Exporta `build_content() -> Gtk.Widget`, embarcado pelo shell via `Module.impl`.
Offline-first: checa indicadores contra a base local e gerencia/importa IOCs.
GTK só é importado aqui.
"""

from __future__ import annotations

import json

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from . import backend  # noqa: E402

_TYPE_ICON = {
    "ip": "network-workgroup-symbolic",
    "domain": "web-browser-symbolic",
    "url": "insert-link-symbolic",
    "hash": "dialog-password-symbolic",
    "email": "mail-unread-symbolic",
    "other": "dialog-question-symbolic",
}


def build_content() -> Gtk.Widget:
    stack = Adw.ViewStack()
    check = _CheckView()
    iocs = _IocsView()
    check.set_iocs_view(iocs)
    stack.add_titled_with_icon(check, "check", "Verificar", "edit-find-symbolic")
    stack.add_titled_with_icon(iocs, "iocs", "IOCs", "view-list-symbolic")
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


# ============================================================
# Aba Verificar
# ============================================================


class _CheckView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for m in ("set_margin_top", "set_margin_bottom",
                  "set_margin_start", "set_margin_end"):
            getattr(self, m)(18)
        self._iocs_view: _IocsView | None = None

        lbl = Gtk.Label(
            label="Cole indicadores (um por linha): IPs, domínios, URLs, hashes "
                  "ou e-mails. O Vigia Intel diz quais já são conhecidos como "
                  "maliciosos na sua base local."
        )
        lbl.set_xalign(0)
        lbl.set_wrap(True)
        self.append(lbl)

        self._buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self._buf)
        tv.set_monospace(True)
        tv.set_top_margin(6)
        tv.set_bottom_margin(6)
        tv.set_left_margin(8)
        tv.set_right_margin(8)
        sw = Gtk.ScrolledWindow()
        sw.set_child(tv)
        sw.set_min_content_height(130)
        frame = Gtk.Frame()
        frame.set_child(sw)
        self.append(frame)

        btn = Gtk.Button(label="Verificar")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", self._on_check)
        self.append(btn)

        page = Adw.PreferencesPage()
        page.set_vexpand(True)
        self._results = Adw.PreferencesGroup()
        self._results.set_title("Resultado")
        page.add(self._results)
        self.append(page)
        self._rows: list[Gtk.Widget] = []
        self._set_empty("Cole indicadores acima e clique em Verificar.")

    def set_iocs_view(self, v: "_IocsView") -> None:
        self._iocs_view = v

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

    def _on_check(self, _btn: Gtk.Button) -> None:
        start, end = self._buf.get_bounds()
        text = self._buf.get_text(start, end, False)
        indicators = [ln.strip() for ln in text.splitlines() if ln.strip()]
        iocs = backend.load_iocs()
        self._clear()

        if not iocs:
            self._set_empty(
                "Sua base de IOCs está vazia. Vá na aba IOCs para adicionar ou "
                "importar indicadores antes de verificar.", "dialog-warning-symbolic")
            return
        if not indicators:
            self._set_empty("Cole pelo menos um indicador para verificar.")
            return

        matches = backend.check(indicators, iocs)
        self._results.set_description(
            f"{len(matches)} de {len(indicators)} indicador(es) casaram com a "
            f"base ({len(iocs)} IOCs). Os que não casaram não estão na base."
        )
        if not matches:
            row = Adw.ActionRow()
            row.set_title("Nenhum indicador casou — nenhum é conhecido na base.")
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._add(row)
            return
        for mt in matches:
            self._add(self._match_row(mt))

    def _match_row(self, mt: backend.Match) -> Adw.ExpanderRow:
        exp = Adw.ExpanderRow()
        exp.set_title(mt.indicator)
        exp.set_subtitle("⚠ Conhecido como malicioso na base")
        exp.set_subtitle_lines(0)
        img = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        img.add_css_class("warning")
        exp.add_prefix(img)
        pill = Gtk.Label(label=mt.ioc.source or "IOC")
        pill.add_css_class("caption")
        pill.add_css_class("warning")
        exp.add_suffix(pill)
        for title, value in (
            ("Tipo", mt.ioc.type), ("Valor", mt.ioc.value),
            ("Fonte", mt.ioc.source), ("Nota", mt.ioc.note or "—"),
        ):
            r = Adw.ActionRow()
            r.set_title(title)
            r.set_subtitle(value)
            r.set_subtitle_lines(0)
            r.add_css_class("property")
            exp.add_row(r)
        return exp


# ============================================================
# Aba IOCs
# ============================================================


class _IocsView(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._page = Adw.PreferencesPage()
        self._page.set_vexpand(True)
        self.append(self._page)

        # adicionar / importar
        g_add = Adw.PreferencesGroup()
        g_add.set_title("Adicionar à base")
        g_add.set_description(
            "O tipo é detectado automaticamente (IP, domínio, URL, hash, e-mail).")
        self._entry = Adw.EntryRow()
        self._entry.set_title("Indicador (IP, domínio, hash…)")
        add_btn = Gtk.Button(label="Adicionar")
        add_btn.add_css_class("suggested-action")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add)
        self._entry.add_suffix(add_btn)
        g_add.add(self._entry)

        import_row = Adw.ActionRow()
        import_row.set_title("Importar de arquivo")
        import_row.set_subtitle("Lista em texto, export OTX (.json) ou MISP (.json)")
        import_row.set_subtitle_lines(0)
        imp_btn = Gtk.Button(label="Importar")
        imp_btn.set_valign(Gtk.Align.CENTER)
        imp_btn.connect("clicked", self._on_import)
        import_row.add_suffix(imp_btn)
        import_row.set_activatable_widget(imp_btn)
        g_add.add(import_row)
        self._page.add(g_add)

        # lista
        self._group = Adw.PreferencesGroup()
        self._group.set_title("Base de IOCs")
        refresh = Gtk.Button(label="Atualizar")
        refresh.add_css_class("flat")
        refresh.connect("clicked", lambda _b: self.reload())
        self._group.set_header_suffix(refresh)
        self._page.add(self._group)
        self._rows: list[Gtk.Widget] = []
        self.reload()

    def reload(self) -> None:
        for r in self._rows:
            self._group.remove(r)
        self._rows = []
        iocs = backend.load_iocs()
        st = backend.stats(iocs)
        self._group.set_description(
            f"{st.get('total', 0)} IOCs · "
            + " · ".join(f"{k}:{v}" for k, v in st.items() if k != "total")
        )
        if not iocs:
            row = Adw.ActionRow()
            row.set_title("Base vazia. Adicione ou importe IOCs acima.")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self._group.add(row)
            self._rows.append(row)
            return
        for ioc in iocs[:300]:
            row = Adw.ActionRow()
            row.set_title(ioc.value)
            row.set_subtitle(f"{ioc.type} · {ioc.source}"
                             + (f" · {ioc.note}" if ioc.note else ""))
            row.set_subtitle_lines(0)
            row.add_prefix(Gtk.Image.new_from_icon_name(
                _TYPE_ICON.get(ioc.type, "dialog-question-symbolic")))
            rm = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            rm.add_css_class("flat")
            rm.set_valign(Gtk.Align.CENTER)
            rm.connect("clicked", self._on_remove, ioc.value)
            row.add_suffix(rm)
            self._group.add(row)
            self._rows.append(row)

    def _on_add(self, _btn: Gtk.Button) -> None:
        text = self._entry.get_text().strip()
        if not text:
            return
        t, v = backend.normalize(text)
        if v:
            backend.add_iocs([backend.IOC(type=t, value=v, source="manual")])
            self._entry.set_text("")
            self.reload()

    def _on_remove(self, _btn: Gtk.Button, value: str) -> None:
        backend.remove_ioc(value)
        self.reload()

    def _on_import(self, _btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Escolha a lista/export de IOCs")
        dialog.open(self.get_root(), None, self._on_import_chosen)

    def _on_import_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            f = dialog.open_finish(result)
        except GLib.Error:
            return
        if f is None or not f.get_path():
            return
        try:
            text = open(f.get_path(), encoding="utf-8", errors="replace").read()
        except OSError:
            return
        iocs: list[backend.IOC] = []
        try:
            data = json.loads(text)
            iocs = backend.parse_otx_pulse(data) or backend.parse_misp_event(data)
        except (json.JSONDecodeError, ValueError):
            iocs = []
        if not iocs:
            iocs = backend.import_plain(text, source="importado")
        backend.add_iocs(iocs)
        self.reload()


# ============================================================
# Aba Sobre
# ============================================================


def _build_about() -> Gtk.Widget:
    page = Adw.PreferencesPage()
    g = Adw.PreferencesGroup()
    g.set_title("Vigia Intel")
    g.set_description(
        "Inteligência de ameaças local. Mantém uma base de IOCs (indicadores de "
        "comprometimento — IPs, domínios, hashes, e-mails maliciosos) e verifica "
        "indicadores contra ela. Módulo de Threat Intelligence do VigiaBlue. "
        "Funciona offline — nada sai da máquina; base salva com permissão 0600."
    )
    g.add(_about_row(
        "Uso típico", "Pegue os IPs que o Vigia SIEM mostrou (força-bruta, bans) "
        "e verifique aqui se já são conhecidos como maliciosos."))
    g.add(_about_row(
        "Importar feeds", "Baixe um pulse do OTX ou um evento do MISP (.json) e "
        "importe — sem precisar de chave de API nem internet no momento da checagem."))
    page.add(g)
    return page


def _about_row(title: str, subtitle: str) -> Adw.ActionRow:
    r = Adw.ActionRow()
    r.set_title(title)
    r.set_subtitle(subtitle)
    r.set_subtitle_lines(0)
    r.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
    return r
