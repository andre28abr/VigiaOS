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
    """Comando de instalação conforme o tipo da dependência (dnf ou pipx)."""
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


# ============================================================
# Helper GTK compartilhado (alarga clamps) — usado pelo shell E pelo Hub
# ============================================================


def widen_clamps(widget, max_width: int = 1100, tightening: int = 900):
    """Percorre a árvore e alarga todo Adw.Clamp/ClampScrollable (inclui o
    interno do PreferencesPage) para max_width/tightening. Retorna o widget
    (encadeável). O import de gi é lazy — mantém o módulo importável headless.

    Reusado pelo VigiaOS (janela do Hub) para dar aos módulos embarcados do
    Blue/Red a mesma largura de conteúdo que eles tinham rodando sob o shell.
    """
    import gi

    gi.require_version("Adw", "1")
    from gi.repository import Adw

    clamp_types = tuple(
        t for t in (getattr(Adw, "Clamp", None),
                    getattr(Adw, "ClampScrollable", None))
        if t is not None
    )
    stack = [widget]
    while stack:
        w = stack.pop()
        if clamp_types and isinstance(w, clamp_types):
            w.set_maximum_size(max_width)
            w.set_tightening_threshold(tightening)
        child = w.get_first_child()
        while child is not None:
            stack.append(child)
            child = child.get_next_sibling()
    return widget


def run_product(meta: ProductMeta, modules: list[Module],
                categories: dict[str, str], order: list[str]) -> int:
    """Sobe o app GTK do produto. Retorna o exit code."""
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gdk, Gio, GLib, Gtk
    from .notifications_bell import NotificationsBell
    from .notices import module_dep_notifications

    # Largura do conteúdo — padrão único do ecossistema (Adw.Clamp 1100 / aperto
    # 900), igual em todas as tools e nos três produtos. O trabalho mora em
    # widen_clamps() (escopo de módulo); o alias local mantém os call sites curtos.
    def _widen_clamps(widget: Gtk.Widget) -> Gtk.Widget:
        return widen_clamps(widget)

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
                return _widen_clamps(widget)
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
        tv.set_content(_widen_clamps(child))
        return tv

    def _placeholder(icon: str, title: str, desc: str) -> Gtk.Widget:
        sp = Adw.StatusPage()
        sp.set_icon_name(icon)
        sp.set_title(title)
        sp.set_description(desc)
        return sp

    def _installer_page() -> Gtk.Widget:
        """Área "Atualizações": abas no topo (ViewSwitcher) — **Atualizações · Sobre**.
        Verifica e aplica updates do sistema e dos programas instalados
        (pelo painel ou pelo terminal)."""

        # ---------- aba Atualizações (reusa a UpdatesTab do Hub) ----------
        def _updates_tab() -> Gtk.Widget:
            try:
                from vigia_installer.tabs.updates import UpdatesTab
                return UpdatesTab()
            except Exception as e:  # noqa: BLE001 — opcional; cai num aviso
                print(f"[{meta.key}] aba Atualizações indisponível: {e}",
                      flush=True)
                return _placeholder(
                    "software-update-available-symbolic",
                    "Atualizações",
                    "O verificador de atualizações não está disponível aqui.")

        # ---------- aba Sobre (manual didático, padrão do Hub) ----------
        def _about_installer_tab() -> Gtk.Widget:
            pm = GLib.markup_escape_text(package_manager())
            _name = GLib.markup_escape_text(meta.name)
            sections = [
                ("O que faz",
                 "Esta área mantém o sistema e os programas instalados <b>em "
                 "dia</b>. Ela <b>verifica</b> se há atualizações e deixa você "
                 "<b>aplicar</b> — pelo painel (um clique) ou copiando o comando "
                 "pro terminal, do seu jeito."),
                ("Como usar",
                 "<b>Aba Atualizações</b>:\n"
                 "1. Ao abrir, checa automaticamente se há atualizações "
                 "(sistema e programas da suíte)\n"
                 "2. <b>Atualizar agora</b> aplica tudo pelo painel "
                 "(pede a senha de admin uma vez)\n"
                 "3. Ou copie o comando e rode no <b>terminal</b>, se preferir\n"
                 "4. O que será atualizado aparece separado: <i>Sistema</i> vs "
                 "<i>Programas da suíte Vigia</i>"),
                ("Sistema e programas",
                 "A atualização cobre <b>os dois</b>:\n"
                 "- <b>Sistema</b>: pacotes do Fedora (kernel, libs, apps)\n"
                 "- <b>Programas da suíte</b>: as ferramentas que o Vigia usa "
                 "(lynis, clamav, suricata, …)\n\n"
                 f"Tudo via <tt>{pm}</tt> — o gerenciador de pacotes do "
                 "Fedora Workstation."),
                ("Conceitos importantes",
                 "<b>Sem reboot</b>: o <tt>dnf</tt> aplica na hora. Atualizar "
                 "<b>não liga serviço</b> nem muda configuração — é seguro.\n\n"
                 "Pra <i>instalar</i> uma dependência que falta num módulo (a "
                 "bolinha vermelha na lista de Módulos), rode o instalador "
                 "completo no terminal: <tt>./install/bootstrap.sh</tt>."),
                ("Saiba mais",
                 f"- Produto: <b>{_name}</b>\n"
                 "- Instalador completo: <tt>install/bootstrap.sh</tt>\n"
                 "- Repositório: https://github.com/andre28abr/VigiaOS"),
            ]
            page = Adw.PreferencesPage()
            for stitle, content in sections:
                group = Adw.PreferencesGroup()
                group.set_title(stitle)
                lbl = Gtk.Label()
                lbl.set_markup(content)
                lbl.set_wrap(True)
                lbl.set_xalign(0)
                lbl.set_selectable(True)
                lbl.set_margin_start(12)
                lbl.set_margin_end(12)
                lbl.set_margin_top(12)
                lbl.set_margin_bottom(12)
                row = Adw.PreferencesRow()
                row.set_child(lbl)
                row.set_activatable(False)
                group.add(row)
                page.add(group)
            return _widen_clamps(page)

        # ---------- sub-barra "Wrapper de:" (mesma do Hub) ----------
        def _wrapper_bar() -> Gtk.Widget:
            # Igual o Hub (WRAPPED_PACKAGES): mostra a ferramenta principal que
            # o instalador embrulha — aqui, o gerenciador de pacotes que a aba
            # Atualizações usa (o dnf, no Fedora Workstation).
            bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            bar.set_margin_start(12)
            bar.set_margin_end(12)
            bar.set_margin_top(4)
            bar.set_margin_bottom(4)
            intro = Gtk.Label(label="Wrapper de:")
            intro.add_css_class("caption")
            intro.add_css_class("dim-label")
            bar.append(intro)
            pill = Gtk.Label(label=package_manager())
            pill.add_css_class("monospace")
            pill.add_css_class("caption")
            pill.add_css_class("dim-label")
            bar.append(pill)
            return bar

        # ---------- monta ViewStack + ViewSwitcher (igual o Hub) ----------
        stack = Adw.ViewStack()
        stack.add_titled_with_icon(
            _updates_tab(), "atualizacoes", "Atualizações",
            "software-update-available-symbolic")
        stack.add_titled_with_icon(
            _about_installer_tab(), "sobre", "Sobre", "help-about-symbolic")

        switcher = Adw.ViewSwitcher()
        switcher.set_stack(stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

        header = Adw.HeaderBar()
        header.set_title_widget(switcher)

        tv = Adw.ToolbarView()
        tv.add_top_bar(header)
        tv.add_top_bar(_wrapper_bar())
        tv.set_content(stack)
        return tv

    def _config_page() -> Gtk.Widget:
        sp = _placeholder(
            "preferences-system-symbolic",
            "Configurações",
            f"As preferências do {meta.name} (tema, atalhos, comportamento) "
            "chegam aqui. Em breve.",
        )
        return _content_with_header("Configurações", sp)

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
            "DPO / Encarregado de Dados com mais de 18 anos em gestão "
            "administrativa, compliance, governança da informação e proteção "
            "de dados (LGPD); formação dupla em Direito (Anhanguera) e Análise "
            "e Desenvolvimento de Sistemas (Mackenzie). Conduziu o VigiaOS como "
            "product owner técnico — traduzindo exigências regulatórias, "
            "hardening e auditoria numa suíte funcional."
        )
        name_row = Adw.ActionRow()
        name_row.set_title("André Augusto Azarias De Souza")
        name_row.set_subtitle("DPO · Compliance & GRC · Privacy Engineering")
        name_row.set_subtitle_lines(0)
        name_row.add_prefix(
            Gtk.Image.new_from_icon_name("avatar-default-symbolic")
        )
        author.add(name_row)
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
            self._stack.add_named(_config_page(), "config")
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

        # -- rail (mesmo padrão do Vigia Hub: ListBox navigation-sidebar) --
        def _build_rail(self) -> Gtk.Widget:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            box.set_size_request(74, -1)

            header_lbl = Gtk.Label(label=meta.name)
            header_lbl.add_css_class("caption-heading")
            header_lbl.add_css_class("dim-label")
            header_lbl.set_wrap(True)
            header_lbl.set_justify(Gtk.Justification.CENTER)
            header_lbl.set_margin_top(16)
            header_lbl.set_margin_bottom(20)
            box.append(header_lbl)

            nav = Gtk.ListBox()
            nav.set_selection_mode(Gtk.SelectionMode.SINGLE)
            nav.add_css_class("navigation-sidebar")
            entries = [
                ("modulos", "Módulos", "view-grid-symbolic"),
                ("instalador", "Atualizações", "software-update-available-symbolic"),
                ("config", "Configurações", "preferences-system-symbolic"),
                ("ajuda", "Ajuda", "help-browser-symbolic"),
                ("sobre", "Sobre", "help-about-symbolic"),
            ]
            first = None
            for name, label, icon_name in entries:
                row = Gtk.ListBoxRow()
                row._stack_name = name  # type: ignore[attr-defined]
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                inner.set_margin_top(10)
                inner.set_margin_bottom(10)
                inner.set_margin_start(6)
                inner.set_margin_end(6)
                icon = Gtk.Image.new_from_icon_name(icon_name)
                icon.set_pixel_size(22)            # igual o Vigia Hub
                icon.set_halign(Gtk.Align.CENTER)
                inner.append(icon)
                lbl = Gtk.Label(label=label)
                lbl.add_css_class("caption")
                lbl.set_halign(Gtk.Align.CENTER)
                lbl.set_wrap(True)
                lbl.set_justify(Gtk.Justification.CENTER)
                inner.append(lbl)
                row.set_child(inner)
                nav.append(row)
                if first is None:
                    first = row
            nav.connect("row-selected", self._on_rail_selected)
            box.append(nav)
            spacer = Gtk.Box()
            spacer.set_vexpand(True)
            box.append(spacer)
            # Sininho de notificações no rodapé (mesmo padrão do Hub):
            # módulos cuja ferramenta externa não está instalada.
            items = [
                (m.name, [d.label for d in m.requires if not dep_installed(d)])
                for m in modules if m.requires
            ]
            bell = NotificationsBell()
            bell.set_halign(Gtk.Align.CENTER)
            bell.set_margin_bottom(14)
            bell.set_notifications(module_dep_notifications(items))
            box.append(bell)
            if first is not None:
                nav.select_row(first)
            return box

        def _on_rail_selected(self, _lb, row) -> None:
            if row is None:
                return
            name = getattr(row, "_stack_name", None)
            if name:
                self._stack.set_visible_child_name(name)

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
                    # Bolinha de disponibilidade (igual o Hub): verde = todas as
                    # dependências instaladas (módulo pronto); vermelho = falta.
                    ok_all = (not mod.requires) or all(
                        dep_installed(d) for d in mod.requires)
                    dot = Gtk.Label(label="●")
                    dot.add_css_class("caption")
                    dot.add_css_class("success" if ok_all else "error")
                    dot.set_valign(Gtk.Align.CENTER)
                    dot.set_tooltip_text(
                        "Pronto — dependências instaladas" if ok_all
                        else "Falta instalar dependência(s)")
                    row.add_suffix(dot)
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
            sidebar_tv.add_css_class("vigia-sidebar")   # tom mais claro (igual Hub)
            sb_header = Adw.HeaderBar()
            sb_header.add_css_class("flat")             # transparente sobre a sidebar
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
                # sidebar de Ferramentas no mesmo tom do Vigia Hub (split-view).
                ".vigia-sidebar { background-color: @sidebar_bg_color; }"
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
