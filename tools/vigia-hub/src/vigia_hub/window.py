"""Janela principal do Hub — 3 painéis:

  [nav fina] | [sidebar tools] | [content]
   ~70px       ~280px            flex

A NAV FINA (esquerda) tem 4 modos selecionaveis:
  - 'tools'      — vista padrao master-detail das tools registradas
  - 'installer'  — Tool Installer em fullscreen (movido pra ca em v0.5)
  - 'settings'   — configuracoes globais do Hub (em breve)
  - 'help'       — manuais (em breve)

Em modo 'tools', a SIDEBAR central lista tools agrupadas por
categoria (Monitoramento / Privacidade / Defesa / Relatorios).

O CONTENT (direita) muda conforme:
  - modo != tools           -> ocupa toda area de tools+content
  - modo tools + tool       -> widget embarcado da tool
  - modo tools + indispon.  -> detail page com botao Abrir externamente
"""

from __future__ import annotations

import importlib
import shutil
import subprocess
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .markdown import md_to_pango
from .registry import (
    CATEGORY_LABELS,
    TOOLS,
    ToolEntry,
    tools_by_category,
)


# Lista de emuladores de terminal em ordem de preferencia.
TERMINAL_CANDIDATES = [
    ("kgx", ["--"]),
    ("ptyxis", ["--"]),
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xterm", ["-e"]),
    ("alacritty", ["-e"]),
]


def find_terminal() -> tuple[str, list[str]] | None:
    for binary, args in TERMINAL_CANDIDATES:
        if shutil.which(binary):
            return binary, args
    return None


# Modos da nav lateral
NAV_MODES = [
    ("tools", "Tools", "view-grid-symbolic"),
    ("installer", "Instalador", "package-x-generic-symbolic"),
    ("settings", "Config.", "preferences-system-symbolic"),
    ("help", "Ajuda", "help-browser-symbolic"),
]


class VigiaHubWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Suite")
        self.set_default_size(1340, 820)

        # Cache de widgets embarcados (tools): tool.id -> Gtk.Widget
        self._embedded_widgets: dict[str, Gtk.Widget] = {}
        # Caches de paginas de modo (installer, settings, help)
        self._mode_pages: dict[str, Gtk.Widget] = {}

        # ============= Nav fina (esquerda) ============= #
        nav_box = self._build_nav_bar()

        # ============= Modo Tools (master-detail) ============= #
        self._tools_view = self._build_tools_view()

        # ============= Main stack (alterna entre modos) ============= #
        self._main_stack = Gtk.Stack()
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.set_transition_duration(150)
        self._main_stack.set_hexpand(True)
        self._main_stack.add_named(self._tools_view, "tools")
        # installer/settings/help: lazy — criados na primeira selecao

        # ============= Layout final ============= #
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.append(nav_box)
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        outer.append(sep)
        outer.append(self._main_stack)
        self.set_content(outer)

        # Seleciona "tools" por default
        first_row = self._nav_list.get_row_at_index(0)
        if first_row is not None:
            self._nav_list.select_row(first_row)

        # Seleciona primeira tool dentro do modo tools
        if TOOLS:
            first_tool_row = self._sidebar_list.get_row_at_index(0)
            # Pula headers (rows nao-tools)
            while first_tool_row is not None and not getattr(first_tool_row, "_tool_id", None):
                idx = first_tool_row.get_index()
                first_tool_row = self._sidebar_list.get_row_at_index(idx + 1)
            if first_tool_row is not None:
                self._sidebar_list.select_row(first_tool_row)
                tool = self._tool_by_id(getattr(first_tool_row, "_tool_id"))
                if tool is not None:
                    self._show_tool(tool)

    # ========================================================================
    # Nav bar (4 icones)
    # ========================================================================

    def _build_nav_bar(self) -> Gtk.Widget:
        """Barra fina vertical com 4 botoes-icone."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_size_request(74, -1)

        # Header do hub (logo discreto)
        header_lbl = Gtk.Label(label="VIGIA")
        header_lbl.add_css_class("caption-heading")
        header_lbl.add_css_class("dim-label")
        header_lbl.set_margin_top(16)
        header_lbl.set_margin_bottom(20)
        box.append(header_lbl)

        # ListBox dos modos
        self._nav_list = Gtk.ListBox()
        self._nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._nav_list.add_css_class("navigation-sidebar")
        self._nav_list.connect("row-selected", self._on_nav_selected)

        for mode_id, label, icon_name in NAV_MODES:
            row = Gtk.ListBoxRow()
            row._mode_id = mode_id  # type: ignore[attr-defined]
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.set_margin_top(10)
            inner.set_margin_bottom(10)
            inner.set_margin_start(6)
            inner.set_margin_end(6)

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(22)
            icon.set_halign(Gtk.Align.CENTER)
            inner.append(icon)

            lbl = Gtk.Label(label=label)
            lbl.add_css_class("caption")
            lbl.set_halign(Gtk.Align.CENTER)
            inner.append(lbl)

            row.set_child(inner)
            self._nav_list.append(row)

        box.append(self._nav_list)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        box.append(spacer)

        return box

    def _on_nav_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            return
        mode_id = getattr(row, "_mode_id", None)
        if not mode_id:
            return

        if mode_id == "tools":
            self._main_stack.set_visible_child_name("tools")
            return

        # Lazy build pages
        if mode_id not in self._mode_pages:
            try:
                page = self._build_mode_page(mode_id)
            except Exception as e:  # pylint: disable=broad-except
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                page = Adw.StatusPage(
                    title=f"Falha ao carregar '{mode_id}'",
                    description=err,
                    icon_name="dialog-error-symbolic",
                )
            self._mode_pages[mode_id] = page
            self._main_stack.add_named(page, mode_id)

        self._main_stack.set_visible_child_name(mode_id)

    def _build_mode_page(self, mode_id: str) -> Gtk.Widget:
        """Constroi a pagina de um modo (installer/settings/help)."""
        if mode_id == "installer":
            # Importa o Tool Installer e usa build_content() fullscreen
            module = importlib.import_module("vigia_installer.window")
            builder = getattr(module, "build_content", None)
            if not callable(builder):
                raise RuntimeError("vigia_installer.window.build_content() faltando")
            return builder()
        if mode_id == "settings":
            return Adw.StatusPage(
                title="Configuracoes",
                description=(
                    "Settings globais do Hub: tema, autostart, notificacoes. "
                    "Em construcao — sera adicionado em proxima versao."
                ),
                icon_name="preferences-system-symbolic",
            )
        if mode_id == "help":
            return Adw.StatusPage(
                title="Manuais",
                description=(
                    "Manuais detalhados de cada tool. Cada tool tambem tem aba "
                    "'Sobre' interna com informacoes especificas. Esta pagina "
                    "consolida tudo num so lugar — em construcao."
                ),
                icon_name="help-browser-symbolic",
            )
        raise ValueError(f"Modo desconhecido: {mode_id}")

    # ========================================================================
    # Tools view (master-detail com categorias)
    # ========================================================================

    def _build_tools_view(self) -> Gtk.Widget:
        """Adw.NavigationSplitView: sidebar com categorias + content stack."""
        sidebar_page = self._build_sidebar()

        # Content stack
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_transition_duration(180)

        for tool in TOOLS:
            detail = self._build_detail_page(tool)
            self._content_stack.add_named(detail, self._detail_name(tool.id))

        if not TOOLS:
            self._content_stack.add_named(
                Adw.StatusPage(
                    title="Sem ferramentas registradas",
                    description="Adicione entradas em registry.py.",
                    icon_name="dialog-information-symbolic",
                ),
                "_empty_",
            )

        content_toolbar = Adw.ToolbarView()
        content_toolbar.set_content(self._content_stack)
        content_page = Adw.NavigationPage(
            title="Vigia Suite",
            child=content_toolbar,
        )
        content_page.set_tag("content")

        split = Adw.NavigationSplitView()
        split.set_sidebar(sidebar_page)
        split.set_content(content_page)
        split.set_sidebar_width_fraction(0.28)
        split.set_min_sidebar_width(280)
        split.set_max_sidebar_width(360)
        return split

    def _build_sidebar(self) -> Adw.NavigationPage:
        """Sidebar com tools agrupadas por categoria."""
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Vigia Suite", subtitle="Toolkit")
        header.set_title_widget(title)

        self._sidebar_list = Gtk.ListBox()
        self._sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar_list.add_css_class("navigation-sidebar")
        self._sidebar_list.connect("row-selected", self._on_sidebar_selected)

        # Adiciona rows agrupadas por categoria, com headers separadores
        grouped = tools_by_category(TOOLS)
        for cat, tools_in_cat in grouped.items():
            # Header row (nao selecionavel)
            header_row = Gtk.ListBoxRow()
            header_row.set_selectable(False)
            header_row.set_activatable(False)
            header_row.add_css_class("dim-label")
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            hbox.set_margin_top(14)
            hbox.set_margin_bottom(4)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hlbl = Gtk.Label(label=CATEGORY_LABELS.get(cat, cat).upper())
            hlbl.add_css_class("caption-heading")
            hlbl.set_xalign(0)
            hlbl.set_hexpand(True)
            hbox.append(hlbl)
            header_row.set_child(hbox)
            self._sidebar_list.append(header_row)

            for tool in tools_in_cat:
                row = self._build_sidebar_row(tool)
                self._sidebar_list.append(row)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self._sidebar_list)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scrolled)

        page = Adw.NavigationPage(title="Vigia Suite", child=toolbar)
        page.set_tag("sidebar")
        return page

    def _build_sidebar_row(self, tool: ToolEntry) -> Gtk.ListBoxRow:
        row = Adw.ActionRow()
        row.set_title(tool.name)
        row.set_subtitle(tool.description)
        row.set_use_markup(False)
        row.set_subtitle_lines(2)

        if tool.icon_path.is_file():
            icon = Gtk.Image.new_from_file(str(tool.icon_path))
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        icon.set_pixel_size(36)
        row.add_prefix(icon)

        available = tool.is_available()
        dot = Gtk.Label(label="●")
        dot.add_css_class("success" if available else "error")
        dot.add_css_class("caption")
        dot.set_valign(Gtk.Align.CENTER)
        row.add_suffix(dot)

        row._tool_id = tool.id  # type: ignore[attr-defined]
        return row

    def _on_sidebar_selected(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
    ) -> None:
        if row is None:
            return
        tool_id = getattr(row, "_tool_id", None)
        if not tool_id:
            return
        tool = self._tool_by_id(tool_id)
        if tool is not None:
            self._show_tool(tool)

    def _tool_by_id(self, tool_id: str) -> ToolEntry | None:
        for t in TOOLS:
            if t.id == tool_id:
                return t
        return None

    # ========================================================================
    # Show tool (embed lazy ou fallback detail)
    # ========================================================================

    def _show_tool(self, tool: ToolEntry) -> None:
        if tool.is_embeddable():
            try:
                widget = self._get_or_build_embedded(tool)
                self._content_stack.set_visible_child(widget)
                return
            except Exception as e:  # pylint: disable=broad-except
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                err_name = self._error_name(tool.id)
                existing = self._content_stack.get_child_by_name(err_name)
                if existing is not None:
                    self._content_stack.remove(existing)
                self._content_stack.add_named(
                    self._build_error_page(tool, err),
                    err_name,
                )
                self._content_stack.set_visible_child_name(err_name)
                return

        self._content_stack.set_visible_child_name(self._detail_name(tool.id))

    def _get_or_build_embedded(self, tool: ToolEntry) -> Gtk.Widget:
        if tool.id in self._embedded_widgets:
            return self._embedded_widgets[tool.id]

        if tool.embedded_module is None:
            raise RuntimeError("tool nao tem embedded_module")

        module = importlib.import_module(tool.embedded_module)
        builder = getattr(module, "build_content", None)
        if not callable(builder):
            raise RuntimeError(
                f"{tool.embedded_module}.build_content() nao encontrado"
            )

        widget = builder()
        self._content_stack.add_named(widget, self._embedded_name(tool.id))
        self._embedded_widgets[tool.id] = widget
        return widget

    @staticmethod
    def _detail_name(tool_id: str) -> str:
        return f"detail::{tool_id}"

    @staticmethod
    def _embedded_name(tool_id: str) -> str:
        return f"embedded::{tool_id}"

    @staticmethod
    def _error_name(tool_id: str) -> str:
        return f"error::{tool_id}"

    # ========================================================================
    # Detail page (fallback)
    # ========================================================================

    def _build_detail_page(self, tool: ToolEntry) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=720, tightening_threshold=600)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(32)
        box.set_margin_end(32)

        if tool.icon_path.is_file():
            icon = Gtk.Image.new_from_file(str(tool.icon_path))
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        icon.set_pixel_size(128)
        icon.set_halign(Gtk.Align.CENTER)
        box.append(icon)

        name = Gtk.Label(label=tool.name)
        name.add_css_class("title-1")
        name.set_halign(Gtk.Align.CENTER)
        box.append(name)

        subtitle = Gtk.Label(label=tool.description)
        subtitle.add_css_class("title-4")
        subtitle.add_css_class("dim-label")
        subtitle.set_halign(Gtk.Align.CENTER)
        subtitle.set_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        subtitle.set_max_width_chars(48)
        box.append(subtitle)

        # Wrapped packages (badges) — mostra dependencias originais
        if tool.wrapped_packages:
            pkg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            pkg_box.set_halign(Gtk.Align.CENTER)
            pkg_lbl = Gtk.Label(label="Wrapper de:")
            pkg_lbl.add_css_class("dim-label")
            pkg_lbl.add_css_class("caption")
            pkg_box.append(pkg_lbl)
            for p in tool.wrapped_packages:
                pill = Gtk.Label(label=p)
                pill.add_css_class("monospace")
                pill.add_css_class("caption")
                pkg_box.append(pill)
            box.append(pkg_box)

        available = tool.is_available()
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_halign(Gtk.Align.CENTER)
        dot = Gtk.Label(label="●")
        dot.add_css_class("success" if available else "error")
        status_box.append(dot)
        status_lbl = Gtk.Label(
            label="Disponivel" if available else "Nao instalada"
        )
        status_lbl.add_css_class("dim-label")
        status_box.append(status_lbl)
        box.append(status_box)

        if not tool.is_embeddable():
            btn = Gtk.Button(label="Abrir externamente")
            btn.add_css_class("suggested-action" if available else "flat")
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_margin_top(8)
            btn.set_margin_bottom(16)
            btn.set_sensitive(available)
            if not available:
                btn.set_label("Nao instalada")
            btn.connect("clicked", lambda _b, t=tool: self._on_launch(t))
            box.append(btn)

        if tool.long_description:
            desc_group = Adw.PreferencesGroup()
            desc_group.set_title("Sobre")
            desc_label = Gtk.Label()
            desc_label.set_markup(md_to_pango(tool.long_description))
            desc_label.set_wrap(True)
            desc_label.set_xalign(0)
            desc_label.set_selectable(True)
            desc_label.set_margin_start(12)
            desc_label.set_margin_end(12)
            desc_label.set_margin_top(12)
            desc_label.set_margin_bottom(12)
            container_row = Adw.PreferencesRow()
            container_row.set_child(desc_label)
            container_row.set_activatable(False)
            desc_group.add(container_row)
            box.append(desc_group)

        if tool.features:
            feat_group = Adw.PreferencesGroup()
            feat_group.set_title("Principais features")
            for feature in tool.features:
                row = Adw.ActionRow()
                row.set_title(md_to_pango(feature))
                row.set_use_markup(True)
                bullet = Gtk.Label(label="•")
                bullet.add_css_class("accent")
                row.add_prefix(bullet)
                feat_group.add(row)
            box.append(feat_group)

        clamp.set_child(box)
        scrolled.set_child(clamp)
        return scrolled

    def _build_error_page(self, tool: ToolEntry, error: str) -> Gtk.Widget:
        page = Adw.StatusPage(
            title=f"Falha ao carregar '{tool.name}'",
            description=(
                f"{error}\n\nVerifique se o pacote esta instalado:\n"
                f"pip install --user -e tools/{tool.id}/"
            ),
            icon_name="dialog-error-symbolic",
        )
        return page

    # ========================================================================
    # Launch externo (fallback)
    # ========================================================================

    def _on_launch(self, tool: ToolEntry) -> None:
        try:
            self._launch_tool(tool)
        except Exception as e:
            self._show_error(tool, str(e))

    def _launch_tool(self, tool: ToolEntry) -> None:
        cmd = list(tool.exec_cmd)
        if tool.needs_root:
            cmd = ["pkexec"] + cmd
        if tool.needs_terminal:
            found = find_terminal()
            if found is None:
                raise RuntimeError(
                    "Nenhum terminal encontrado (procurei: "
                    + ", ".join(b for b, _ in TERMINAL_CANDIDATES)
                    + "). Instale 'gnome-console'."
                )
            term_binary, term_args = found
            cmd = [term_binary] + term_args + cmd
        subprocess.Popen(cmd)

    def _show_error(self, tool: ToolEntry, message: str) -> None:
        dlg = Adw.AlertDialog(
            heading=f"Falha ao abrir '{tool.name}'",
            body=message,
        )
        dlg.add_response("ok", "OK")
        dlg.present(self)
