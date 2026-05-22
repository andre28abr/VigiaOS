"""Janela principal do Vigia Hub.

Layout: grid responsivo de cards (FlowBox), 1-3 colunas conforme largura.
Cada card mostra icone grande, nome, descricao, status (instalado/nao),
botao Abrir. Search bar no topo filtra cards.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .registry import TOOLS, ToolEntry


# Lista de emuladores de terminal em ordem de preferencia + args de comando.
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


class ToolCard(Gtk.Box):
    """Card visual de uma ferramenta. Subclass de Gtk.Box."""

    def __init__(
        self,
        tool: ToolEntry,
        on_launch: Callable[[ToolEntry], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add_css_class("card")
        self.set_size_request(260, -1)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        # Pad interno do card
        pad = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        pad.set_margin_top(20)
        pad.set_margin_bottom(20)
        pad.set_margin_start(20)
        pad.set_margin_end(20)
        self.append(pad)

        # Icon
        if tool.icon_path.is_file():
            icon = Gtk.Image.new_from_file(str(tool.icon_path))
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)
        pad.append(icon)

        # Nome
        name = Gtk.Label(label=tool.name)
        name.add_css_class("title-3")
        name.set_halign(Gtk.Align.CENTER)
        pad.append(name)

        # Descricao (texto justificado, limitado a 40 chars de largura)
        desc = Gtk.Label(label=tool.description)
        desc.add_css_class("dim-label")
        desc.add_css_class("caption")
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_xalign(0.5)
        desc.set_max_width_chars(36)
        desc.set_vexpand(True)
        pad.append(desc)

        # Status indicator
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status_box.set_halign(Gtk.Align.CENTER)
        available = tool.is_available()
        dot = Gtk.Label(label="●")
        dot.add_css_class("success" if available else "error")
        status_box.append(dot)
        status_lbl = Gtk.Label(label="Disponivel" if available else "Nao instalada")
        status_lbl.add_css_class("dim-label")
        status_lbl.add_css_class("caption")
        status_box.append(status_lbl)
        pad.append(status_box)

        # Botao Abrir
        btn = Gtk.Button(label="Abrir")
        btn.add_css_class("suggested-action" if available else "flat")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_sensitive(available)
        if not available:
            btn.set_label("Nao instalada")
        btn.connect("clicked", lambda _b, t=tool: on_launch(t))
        pad.append(btn)

        # Texto para busca (nome + descricao em lowercase)
        self.search_text = (tool.name + " " + tool.description).lower()


class VigiaHubWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Suite")
        self.set_default_size(960, 720)

        # ============= Header ============= #
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(
            title="Vigia Suite",
            subtitle="Toolkit de seguranca para Fedora Atomic",
        )
        header.set_title_widget(title)

        # ============= Conteudo ============= #
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        # Search bar
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(
            "Filtrar ferramentas (ex: log, firewall, selinux, network)"
        )
        self._search.connect("search-changed", lambda _e: self._flowbox.invalidate_filter())
        content.append(self._search)

        # Stats label
        n_avail = sum(1 for t in TOOLS if t.is_available())
        stats = Gtk.Label()
        stats.set_xalign(0)
        stats.add_css_class("dim-label")
        stats.set_text(
            f"{n_avail} de {len(TOOLS)} ferramentas disponiveis. "
            "Clique em 'Abrir' para lancar."
        )
        content.append(stats)

        # FlowBox de cards
        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_max_children_per_line(3)
        self._flowbox.set_min_children_per_line(1)
        self._flowbox.set_homogeneous(True)
        self._flowbox.set_row_spacing(8)
        self._flowbox.set_column_spacing(8)
        self._flowbox.set_filter_func(self._filter_card)

        for tool in TOOLS:
            card = ToolCard(tool, self._on_launch)
            self._flowbox.insert(card, -1)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._flowbox)
        content.append(scrolled)

        # Toolbar root
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(content)
        self.set_content(toolbar)

    # ========================================================================
    # Filter & launch
    # ========================================================================

    def _filter_card(self, child: Gtk.FlowBoxChild) -> bool:
        query = self._search.get_text().lower().strip()
        if not query:
            return True
        card = child.get_child()
        text = getattr(card, "search_text", "")
        return query in text

    def _on_launch(self, tool: ToolEntry) -> None:
        try:
            self._launch_tool(tool)
        except Exception as e:
            self._show_error(tool, str(e))

    def _launch_tool(self, tool: ToolEntry) -> None:
        cmd = list(tool.exec_cmd)
        if tool.needs_root:
            cmd = ["sudo"] + cmd
        if tool.needs_terminal:
            found = find_terminal()
            if found is None:
                raise RuntimeError(
                    "Nenhum terminal encontrado (procurei: "
                    + ", ".join(b for b, _ in TERMINAL_CANDIDATES)
                    + "). Instale 'gnome-console' ou similar."
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
