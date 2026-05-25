"""Janela principal — master-detail (sidebar + content).

Sidebar: lista de tools com icone pequeno + nome + status dot.
Content: painel direito que pode estar em 2 modos:

- **Detail** (fallback): hero icon + descricao + features + botao
  "Abrir externamente". Usado quando a tool nao e' embarcavel OU nao
  esta instalada.

- **Embedded**: a tool inteira embarcada (header da tool + content).
  Construida via lazy `build_content()` do modulo declarado em
  `ToolEntry.embedded_module`. Cache: depois de construida, fica viva
  no stack para nao reinicializar a cada clique.

Usa Adw.NavigationSplitView (libadwaita 1.4+).
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
from .registry import TOOLS, ToolEntry


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


class VigiaHubWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Suite")
        self.set_default_size(1280, 800)  # mais espaco para embedded content

        # Cache de widgets embarcados: tool.id -> Gtk.Widget vivo no stack
        self._embedded_widgets: dict[str, Gtk.Widget] = {}

        # ============= Sidebar ============= #
        sidebar_page = self._build_sidebar()

        # ============= Content Stack ============= #
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_transition_duration(180)

        # Pre-constroi detail pages (rapido — so labels + botao)
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

        # Toolbar sem header — tools embarcadas trazem o proprio header,
        # e detail pages nao precisam de header (sao informacionais).
        content_toolbar = Adw.ToolbarView()
        content_toolbar.set_content(self._content_stack)
        content_page = Adw.NavigationPage(
            title="Vigia Suite",
            child=content_toolbar,
        )
        content_page.set_tag("content")

        # ============= Split view ============= #
        split = Adw.NavigationSplitView()
        split.set_sidebar(sidebar_page)
        split.set_content(content_page)
        split.set_sidebar_width_fraction(0.26)
        split.set_min_sidebar_width(260)
        split.set_max_sidebar_width(340)
        self.set_content(split)

        # Seleciona primeira tool automaticamente
        if TOOLS:
            first_row = self._sidebar_list.get_row_at_index(0)
            if first_row is not None:
                self._sidebar_list.select_row(first_row)
                self._show_tool(TOOLS[0])

    # ========================================================================
    # Sidebar
    # ========================================================================

    def _build_sidebar(self) -> Adw.NavigationPage:
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(title="Vigia Suite", subtitle="Toolkit")
        header.set_title_widget(title)

        self._sidebar_list = Gtk.ListBox()
        self._sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._sidebar_list.add_css_class("navigation-sidebar")
        self._sidebar_list.connect("row-selected", self._on_sidebar_selected)

        for tool in TOOLS:
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
        icon.set_pixel_size(40)
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
        self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None
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
        """Decide entre embed vs detail page e mostra."""
        if tool.is_embeddable():
            try:
                widget = self._get_or_build_embedded(tool)
                self._content_stack.set_visible_child(widget)
                return
            except Exception as e:  # pylint: disable=broad-except
                err = "".join(traceback.format_exception_only(type(e), e)).strip()
                err_name = self._error_name(tool.id)
                # Se ja existir error page anterior, remove pra atualizar mensagem
                existing = self._content_stack.get_child_by_name(err_name)
                if existing is not None:
                    self._content_stack.remove(existing)
                self._content_stack.add_named(
                    self._build_error_page(tool, err),
                    err_name,
                )
                self._content_stack.set_visible_child_name(err_name)
                return

        # Fallback: detail page (com botao Abrir externamente)
        self._content_stack.set_visible_child_name(self._detail_name(tool.id))

    def _get_or_build_embedded(self, tool: ToolEntry) -> Gtk.Widget:
        """Lazy build do widget embedado, com cache."""
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
        """Pagina informacional + botao Abrir externamente (quando aplicavel)."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp(maximum_size=720, tightening_threshold=600)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(32)
        box.set_margin_bottom(32)
        box.set_margin_start(32)
        box.set_margin_end(32)

        # Hero
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

        # Status pill
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

        # Botao Abrir externamente (so quando NAO e' embeddable — caso futuro:
        # tools em terminal/TUI). Tools embeddable nao precisam de botao —
        # quando selecionadas, a UI propria carrega.
        if not tool.is_embeddable():
            btn = Gtk.Button(label="Abrir externamente")
            btn.add_css_class("suggested-action" if available else "flat")
            btn.add_css_class("pill")
            btn.set_halign(Gtk.Align.CENTER)
            btn.set_margin_top(8)
            btn.set_margin_bottom(16)
            btn.set_sensitive(available)
            if not available:
                btn.set_label("Nao instalada")
            btn.connect("clicked", lambda _b, t=tool: self._on_launch(t))
            box.append(btn)

        # Long description
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

        # Features
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
    # Launch externo (fallback para tools nao-embeddable)
    # ========================================================================

    def _on_launch(self, tool: ToolEntry) -> None:
        try:
            self._launch_tool(tool)
        except Exception as e:
            self._show_error(tool, str(e))

    def _launch_tool(self, tool: ToolEntry) -> None:
        cmd = list(tool.exec_cmd)
        if tool.needs_root:
            # Politica do projeto: privilege escalation grafica via pkexec
            # (NUNCA sudo, que requer TTY-prompt). Ver feedback-pkexec-not-sudo.
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
