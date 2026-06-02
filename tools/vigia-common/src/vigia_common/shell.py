"""Shell de produto Vigia — launcher GTK4 reutilizável (rail + sidebar + conteúdo).

Os produtos do ecossistema (VigiaHub, VigiaRed, VigiaBlue, …) compartilham a
mesma casca visual: um rail à esquerda (Módulos / Instalador / Ajuda / Sobre),
uma sidebar com os módulos agrupados por categoria, e o conteúdo à direita.

Aqui mora SÓ a casca. Cada produto fornece:
  - `ProductMeta` (nome, app_id, versão, tagline, cor de destaque)
  - uma lista de `Module` (nome, categoria, ícone, descrição, o que vai integrar)

No esqueleto, cada módulo abre uma página "Planejado / Em breve" descrevendo o
que ele fará e quais ferramentas vai embarcar — os backends entram depois,
módulo a módulo. A parte de dados (`Module`/`ProductMeta`/agrupamento) é pura e
testável sem GTK; a parte gráfica só é importada quando o app realmente sobe.

Uso (no `__main__` do produto):

    from vigia_common.shell import ProductMeta, run_product
    from .registry import MODULES
    run_product(ProductMeta(...), MODULES)
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field

from .platform import install_hint, package_manager


# ============================================================
# Dados (puro — sem GTK, testável headless)
# ============================================================


@dataclass(frozen=True)
class Dependency:
    """Ferramenta externa que um módulo embarca (usada na página Instalador)."""

    label: str                       # "YARA", "Suricata", "Volatility 3"…
    checks: tuple[str, ...]          # binários; instalada se algum existe no PATH
    kind: str = "rpm"                # "rpm" | "pip" | "source"
    package: str = ""                # rpm: nome do pacote; pip: pacote pipx/pip
    install: str = ""                # comando literal (override; usado p/ "source")
    note: str = ""                   # observação opcional


@dataclass(frozen=True)
class Module:
    """Um módulo (futura ferramenta) de um produto Vigia."""

    id: str
    name: str
    category: str
    icon: str                      # icon-name do tema (symbolic)
    summary: str                   # 1 linha (sidebar)
    description: str = ""          # parágrafo (página do módulo)
    wraps: list[str] = field(default_factory=list)   # CLIs que vai embarcar
    features: list[str] = field(default_factory=list)  # recursos previstos
    status: str = "planejado"      # planejado | em-dev | pronto
    # Módulo Python que exporta build_content() -> Gtk.Widget. Quando definido,
    # o shell embarca a GUI real do módulo em vez da página "Em breve".
    impl: str | None = None
    # Ferramentas externas que o módulo precisa (página Instalador checa/instala).
    requires: tuple[Dependency, ...] = ()


@dataclass(frozen=True)
class ProductMeta:
    """Identidade de um produto do ecossistema Vigia."""

    key: str                       # "red", "blue", ...
    name: str                      # "VigiaRed"
    app_id: str                    # "br.com.vigia.Red"
    version: str
    tagline: str
    accent: str                    # cor de destaque hex (#rrggbb)
    audience: str = ""             # público-alvo (1 linha)
    legal_notice: str = ""         # aviso ético/legal (ex: VigiaRed)


# Ordem e rótulos das categorias são definidos por produto (cada registry traz
# o seu CATEGORIES). Helper de agrupamento respeitando a ordem informada:
def modules_by_category(
    modules: list[Module], order: list[str]
) -> dict[str, list[Module]]:
    """Agrupa módulos por categoria, na ordem de `order`."""
    grouped: dict[str, list[Module]] = {}
    for m in modules:
        grouped.setdefault(m.category, []).append(m)
    return {c: grouped[c] for c in order if c in grouped}


STATUS_LABEL = {
    "planejado": "Planejado",
    "em-dev": "Em desenvolvimento",
    "pronto": "Pronto",
}
STATUS_PILL = {
    "planejado": "🔜 Planejado",
    "em-dev": "🚧 Em desenvolvimento",
    "pronto": "🟢 Pronto",
}


def count_by_status(modules: list[Module]) -> dict[str, int]:
    """Quantos módulos em cada status (usado no Instalador / Sobre)."""
    out: dict[str, int] = {}
    for m in modules:
        out[m.status] = out.get(m.status, 0) + 1
    return out


def dep_installed(dep: Dependency) -> bool:
    """True se algum dos binários da dependência está no PATH."""
    return any(shutil.which(b) for b in dep.checks)


def dep_command(dep: Dependency) -> str:
    """Comando de instalação conforme o tipo + a plataforma (rpm-ostree/dnf/pipx)."""
    if dep.install:
        return dep.install
    if dep.kind == "pip":
        return f"pipx install {dep.package}"
    return install_hint(dep.package)


def product_dependencies(
    modules: list[Module],
) -> list[tuple[Dependency, list[str]]]:
    """Dependências únicas do produto + quais módulos usam cada uma (ordem estável)."""
    order: list[str] = []
    deps: dict[str, Dependency] = {}
    users: dict[str, list[str]] = {}
    for m in modules:
        for d in m.requires:
            if d.label not in deps:
                deps[d.label] = d
                users[d.label] = []
                order.append(d.label)
            users[d.label].append(m.name)
    return [(deps[k], users[k]) for k in order]


# ============================================================
# GUI (importa GTK só quando chamado)
# ============================================================


def run_product(meta: ProductMeta, modules: list[Module],
                categories: dict[str, str], order: list[str]) -> int:
    """Sobe o app GTK do produto. Retorna o exit code."""
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gio, Gtk

    accent = meta.accent

    # ---------- helpers de UI ----------

    def _img(icon: str, size: int) -> Gtk.Widget:
        """Ícone do módulo: SVG colorido (padrão Hub) se for arquivo; senão
        cai no icon-name do tema."""
        if icon and icon.endswith(".svg") and os.path.isfile(icon):
            im = Gtk.Image.new_from_file(icon)
            im.set_pixel_size(size)
            return im
        return Gtk.Image.new_from_icon_name(
            icon or "application-x-executable-symbolic"
        )

    def _open_uri(uri: str) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except Exception as e:  # noqa: BLE001 — link não pode derrubar o app
            print(f"[{meta.key}] falha ao abrir {uri}: {e}", flush=True)

    def _module_page(mod: Module) -> Gtk.Widget:
        """Conteúdo de um módulo.

        Se `mod.impl` aponta para um módulo Python com `build_content()`, embarca
        a GUI real (auto-contida, com header próprio). Senão, mostra a página
        'Planejado / Em breve'. Falha de import cai no placeholder (não derruba).
        """
        if mod.impl:
            try:
                import importlib
                widget = importlib.import_module(mod.impl).build_content()
                return widget
            except Exception as e:  # noqa: BLE001 — módulo quebrado não derruba o app
                print(f"[{meta.key}] falha ao carregar {mod.id} ({mod.impl}): {e}",
                      flush=True)

        page = Adw.PreferencesPage()

        head = Adw.PreferencesGroup()
        head.set_title(mod.name)
        head.set_description(mod.description or mod.summary)
        status_row = Adw.ActionRow()
        status_row.set_title(STATUS_PILL.get(mod.status, mod.status))
        status_row.set_subtitle(
            "Este módulo ainda não foi implementado — o esqueleto já reserva "
            "o lugar dele no produto."
        )
        status_row.add_prefix(_img(mod.icon, 40))
        head.add(status_row)
        page.add(head)

        if mod.features:
            g = Adw.PreferencesGroup()
            g.set_title("Recursos previstos")
            for f in mod.features:
                r = Adw.ActionRow()
                r.set_title(f)
                r.set_subtitle_lines(0)
                r.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
                g.add(r)
            page.add(g)

        if mod.wraps:
            g = Adw.PreferencesGroup()
            g.set_title("Vai integrar")
            g.set_description("Ferramentas open source que este módulo embarca.")
            for w in mod.wraps:
                r = Adw.ActionRow()
                r.set_title(w)
                r.add_prefix(
                    Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
                )
                g.add(r)
            page.add(g)

        return _content_with_header(mod.name, page)

    def _content_with_header(title: str, child: Gtk.Widget) -> Gtk.Widget:
        """Embrulha um widget num ToolbarView com HeaderBar (título + controles)."""
        tv = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_title_widget(Adw.WindowTitle(title=title, subtitle=meta.name))
        tv.add_top_bar(hb)
        tv.set_content(child)
        return tv

    def _placeholder(icon: str, title: str, desc: str) -> Gtk.Widget:
        sp = Adw.StatusPage()
        sp.set_icon_name(icon)
        sp.set_title(title)
        sp.set_description(desc)
        return sp

    def _installer_page() -> Gtk.Widget:
        """Mesmo padrão do Hub: módulos agrupados por categoria, cada um como
        ExpanderRow (ícone + resumo + descrição em markdown), com o status da
        sua dependência externa (instalada? como instalar) dobrado no corpo."""
        from .markdown import md_to_pango

        grouped = modules_by_category(modules, order)
        page = Adw.PreferencesPage()

        intro = Adw.PreferencesGroup()
        intro.set_title("Instalador")
        n_ext = sum(1 for m in modules if m.requires)
        intro.set_description(
            f"Os {len(modules)} módulos do {meta.name}, por categoria. {n_ext} "
            "embarcam uma ferramenta externa — cada um mostra se ela está "
            "instalada e o comando para instalar "
            f"(plataforma: {package_manager()}). "
            "Dica: install/blue-deps.sh instala tudo de uma vez."
        )
        refresh = Gtk.Button(label="Reverificar")
        refresh.add_css_class("flat")
        refresh.set_valign(Gtk.Align.CENTER)
        intro.set_header_suffix(refresh)
        page.add(intro)

        def _dep_block(mod: Module) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            hdr = Gtk.Label(label="Dependência")
            hdr.add_css_class("caption-heading")
            hdr.set_xalign(0)
            hdr.set_margin_top(6)
            box.append(hdr)
            if not mod.requires:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                ic = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                ic.add_css_class("success")
                row.append(ic)
                t = Gtk.Label(
                    label="Não precisa de ferramenta externa — roda direto.")
                t.set_wrap(True)
                t.set_xalign(0)
                t.set_hexpand(True)
                row.append(t)
                box.append(row)
                return box
            for dep in mod.requires:
                ok = dep_installed(dep)
                line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                ic = Gtk.Image.new_from_icon_name(
                    "emblem-ok-symbolic" if ok else "dialog-warning-symbolic")
                ic.add_css_class("success" if ok else "warning")
                ic.set_valign(Gtk.Align.START)
                line.append(ic)
                lbl = Gtk.Label(
                    label=f"{dep.label} — "
                    + ("instalado" if ok else "não encontrado"))
                lbl.set_wrap(True)
                lbl.set_xalign(0)
                lbl.set_hexpand(True)
                line.append(lbl)
                box.append(line)
                if not ok:
                    cmd = dep_command(dep)
                    crow = Gtk.Box(
                        orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                    crow.set_margin_start(28)
                    cl = Gtk.Label(label=cmd)
                    cl.add_css_class("monospace")
                    cl.add_css_class("caption")
                    cl.set_wrap(True)
                    cl.set_xalign(0)
                    cl.set_hexpand(True)
                    cl.set_selectable(True)
                    crow.append(cl)
                    cp = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
                    cp.add_css_class("flat")
                    cp.set_valign(Gtk.Align.CENTER)
                    cp.set_tooltip_text("Copiar comando")
                    cp.connect(
                        "clicked",
                        lambda _b, c=cmd, w=cp: w.get_clipboard().set(c))
                    crow.append(cp)
                    box.append(crow)
                    if dep.note:
                        nl = Gtk.Label(label=dep.note)
                        nl.add_css_class("caption")
                        nl.add_css_class("dim-label")
                        nl.set_wrap(True)
                        nl.set_xalign(0)
                        nl.set_margin_start(28)
                        box.append(nl)
            return box

        def _module_expander(mod: Module) -> Adw.ExpanderRow:
            exp = Adw.ExpanderRow()
            exp.set_title(mod.name)
            exp.set_subtitle(mod.summary)
            exp.set_subtitle_lines(0)
            exp.add_prefix(_img(mod.icon, 36))
            if mod.requires:
                ok_all = all(dep_installed(d) for d in mod.requires)
                pill = Gtk.Label(label="Pronto" if ok_all else "Falta instalar")
                pill.add_css_class("caption")
                pill.add_css_class("success" if ok_all else "warning")
                pill.set_valign(Gtk.Align.CENTER)
                exp.add_suffix(pill)

            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            body.set_margin_top(12)
            body.set_margin_bottom(12)
            body.set_margin_start(16)
            body.set_margin_end(16)
            if mod.description:
                d = Gtk.Label()
                d.set_markup(md_to_pango(mod.description))
                d.set_wrap(True)
                d.set_xalign(0)
                d.set_selectable(True)
                body.append(d)
            body.append(_dep_block(mod))

            wrapper = Adw.PreferencesRow()
            wrapper.set_activatable(False)
            wrapper.set_child(body)
            exp.add_row(wrapper)
            return exp

        cat_groups: list[Gtk.Widget] = []

        def _build_groups(*_a):
            for grp in cat_groups:
                page.remove(grp)
            cat_groups.clear()
            for cat, mods in grouped.items():
                grp = Adw.PreferencesGroup()
                grp.set_title(categories.get(cat, cat))
                for mod in mods:
                    grp.add(_module_expander(mod))
                page.add(grp)
                cat_groups.append(grp)

        refresh.connect("clicked", _build_groups)
        _build_groups()
        return _content_with_header("Instalador", page)

    def _help_page() -> Gtk.Widget:
        sp = _placeholder(
            "help-browser-symbolic",
            "Ajuda",
            "Manuais leigos e técnicos (Markdown, renderizados in-app) chegam "
            "junto com cada módulo — mesmo formato do Vigia Hub.",
        )
        return _content_with_header("Ajuda", sp)

    def _about_page() -> Gtk.Widget:
        page = Adw.PreferencesPage()

        prod = Adw.PreferencesGroup()
        prod.set_title(f"Sobre o {meta.name}")
        prod.set_description(meta.tagline)
        ver = Adw.ActionRow()
        ver.set_title(meta.name)
        ver.set_subtitle(f"Versão {meta.version} · esqueleto (módulos em breve)")
        ver.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-symbolic"))
        prod.add(ver)
        if meta.audience:
            aud = Adw.ActionRow()
            aud.set_title("Para quem é")
            aud.set_subtitle(meta.audience)
            aud.set_subtitle_lines(0)
            aud.add_prefix(Gtk.Image.new_from_icon_name("system-users-symbolic"))
            prod.add(aud)
        eco = Adw.ActionRow()
        eco.set_title("Ecossistema VigiaOS")
        eco.set_subtitle("Parte da família Vigia · VigiaHub / VigiaRed / VigiaBlue")
        eco.set_subtitle_lines(0)
        eco.add_prefix(Gtk.Image.new_from_icon_name("view-grid-symbolic"))
        eco.set_activatable(True)
        eco.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
        eco.connect("activated", lambda _r: _open_uri("https://github.com/andre28abr/VigiaOS"))
        prod.add(eco)
        page.add(prod)

        if meta.legal_notice:
            warn = Adw.PreferencesGroup()
            warn.set_title("Aviso legal")
            warn.set_description(meta.legal_notice)
            page.add(warn)

        author = Adw.PreferencesGroup()
        author.set_title("Autor")
        author.set_description(
            "André Augusto Azarias De Souza — DPO / Compliance & GRC · "
            "Privacy Engineering."
        )
        ln = Adw.ActionRow()
        ln.set_title("LinkedIn")
        ln.set_subtitle("linkedin.com/in/andreaugusto-azariasdesouza")
        ln.add_prefix(Gtk.Image.new_from_icon_name("applications-internet-symbolic"))
        ln.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
        ln.set_activatable(True)
        ln.connect("activated", lambda _r: _open_uri(
            "https://linkedin.com/in/andreaugusto-azariasdesouza"))
        author.add(ln)
        gh = Adw.ActionRow()
        gh.set_title("GitHub")
        gh.set_subtitle("github.com/andre28abr")
        gh.add_prefix(Gtk.Image.new_from_icon_name("applications-internet-symbolic"))
        gh.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
        gh.set_activatable(True)
        gh.connect("activated", lambda _r: _open_uri("https://github.com/andre28abr"))
        author.add(gh)
        page.add(author)

        return _content_with_header("Sobre", page)

    # ---------- janela ----------

    class ProductWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app)
            self.set_title(meta.name)
            self.set_default_size(1340, 820)   # mesmo tamanho do Vigia Hub

            self._content_bin = Adw.Bin()
            self._grouped = modules_by_category(modules, order)

            # ViewStack das 4 áreas (módulos / instalador / ajuda / sobre)
            self._stack = Adw.ViewStack()
            self._stack.add_named(self._build_modules_area(), "modulos")
            self._stack.add_named(_installer_page(), "instalador")
            self._stack.add_named(_help_page(), "ajuda")
            self._stack.add_named(_about_page(), "sobre")

            rail = self._build_rail()

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.append(rail)
            sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            box.append(sep)
            self._stack.set_hexpand(True)
            box.append(self._stack)
            self.set_content(box)

            # seleciona o 1º módulo na sidebar — dispara row-selected, que mostra
            # o conteúdo e acende a linha. Fallback: set direto se algo falhar.
            if self._first_mod_row is not None:
                self._sidebar.select_row(self._first_mod_row)
            elif modules:
                self._show_module(modules[0])

        # -- rail --
        def _build_rail(self) -> Gtk.Widget:
            rail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            rail.add_css_class("vigia-rail")
            rail.set_size_request(96, -1)
            rail.set_margin_top(10)
            rail.set_margin_bottom(10)

            title = Gtk.Label(label=meta.name)
            title.add_css_class("caption-heading")  # pequeno, igual o Vigia Hub
            title.set_margin_bottom(8)
            title.set_wrap(True)
            title.set_justify(Gtk.Justification.CENTER)
            rail.append(title)

            entries = [
                ("modulos", "Módulos", "view-grid-symbolic"),
                ("instalador", "Instalador", "system-software-install-symbolic"),
                ("ajuda", "Ajuda", "help-browser-symbolic"),
                ("sobre", "Sobre", "help-about-symbolic"),
            ]
            group_btn = None
            for name, label, icon in entries:
                btn = Gtk.ToggleButton()
                btn.add_css_class("flat")
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                inner.set_margin_top(6)
                inner.set_margin_bottom(6)
                inner.append(Gtk.Image.new_from_icon_name(icon))
                lbl = Gtk.Label(label=label)
                lbl.add_css_class("caption")
                inner.append(lbl)
                btn.set_child(inner)
                if group_btn is None:
                    group_btn = btn
                    btn.set_active(True)
                else:
                    btn.set_group(group_btn)
                btn.connect(
                    "toggled",
                    lambda b, n=name: b.get_active() and self._stack.set_visible_child_name(n),
                )
                rail.append(btn)
            return rail

        # -- área de módulos: sidebar + conteúdo --
        def _build_modules_area(self) -> Gtk.Widget:
            sidebar = Gtk.ListBox()
            sidebar.add_css_class("navigation-sidebar")
            sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
            # row-selected (não row-activated): ActionRow não é activatable por
            # padrão, então row-activated nunca dispara. Selecionar = clicar.
            sidebar.connect("row-selected", self._on_row_selected)
            self._first_mod_row: Gtk.ListBoxRow | None = None

            for cat, mods in self._grouped.items():
                header = Gtk.Label(label=categories.get(cat, cat).upper())
                header.add_css_class("dim-label")
                header.add_css_class("caption-heading")
                header.set_xalign(0)
                header.set_margin_top(14)
                header.set_margin_start(12)
                header.set_margin_bottom(4)
                hrow = Gtk.ListBoxRow()
                hrow.set_selectable(False)
                hrow.set_activatable(False)
                hrow.set_child(header)
                sidebar.append(hrow)

                for mod in mods:
                    row = Adw.ActionRow()
                    row.set_title(mod.name)
                    row.set_subtitle(mod.summary)
                    row.add_prefix(_img(mod.icon, 28))
                    pill = Gtk.Label(label=STATUS_LABEL.get(mod.status, ""))
                    pill.add_css_class("caption")
                    pill.add_css_class("dim-label")
                    row.add_suffix(pill)
                    row.set_activatable(True)
                    row._vigia_module = mod  # type: ignore[attr-defined]
                    sidebar.append(row)
                    if self._first_mod_row is None:
                        self._first_mod_row = row

            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_child(sidebar)

            self._sidebar = sidebar

            # Coluna do meio com header "Ferramentas" (igual o Vigia Hub).
            # Sem botões de janela aqui — o X fica no header do conteúdo.
            sidebar_tv = Adw.ToolbarView()
            sb_header = Adw.HeaderBar()
            sb_header.set_show_start_title_buttons(False)
            sb_header.set_show_end_title_buttons(False)
            sb_header.set_title_widget(
                Adw.WindowTitle(title="Ferramentas", subtitle="")
            )
            sidebar_tv.add_top_bar(sb_header)
            sidebar_tv.set_content(scroller)
            sidebar_tv.set_size_request(300, -1)

            split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            split.append(sidebar_tv)
            split.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            self._content_bin.set_hexpand(True)
            split.append(self._content_bin)
            return split

        def _on_row_selected(self, _lb: Gtk.ListBox, row) -> None:
            if row is None:          # deseleção
                return
            mod = getattr(row, "_vigia_module", None)
            if mod is not None:
                self._content_bin.set_child(_module_page(mod))

        def _show_module(self, mod: Module) -> None:
            self._content_bin.set_child(_module_page(mod))

    # ---------- app ----------

    class ProductApp(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id=meta.app_id,
                flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            )

        def do_activate(self) -> None:
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
            self._install_css()
            win = self.get_active_window() or ProductWindow(self)
            win.present()

        def _install_css(self) -> None:
            css = (
                ".vigia-rail { background: alpha(@window_bg_color, 0.6); }"
                ".vigia-rail togglebutton:checked { color: " + accent + "; }"
            ).encode()
            provider = Gtk.CssProvider()
            provider.load_from_data(css)
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

    import sys

    return ProductApp().run(sys.argv)
