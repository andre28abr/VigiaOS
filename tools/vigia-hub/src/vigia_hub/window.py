"""Janela principal do Vigia Hub.

Layout: lista de ferramentas registradas em registry.TOOLS, cada uma com
icone, nome, descricao e botao 'Abrir'. Click no botao spawna a ferramenta
via subprocess (com terminal/sudo wrappers conforme necessario).
"""

from __future__ import annotations

import shutil
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .registry import TOOLS, ToolEntry

# Lista de terminais conhecidos em ordem de preferencia. Cada entry e' uma
# tupla (binary_name, args_para_passar_comando_apos).
#
# kgx / gnome-console e ptyxis sao os defaults modernos do GNOME.
# Convencao do "--" para separar args do terminal vs comando: a maioria suporta.
TERMINAL_CANDIDATES = [
    ("kgx", ["--"]),               # GNOME Console
    ("ptyxis", ["--"]),            # Prompt/Ptyxis
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xterm", ["-e"]),
    ("alacritty", ["-e"]),
]


def find_terminal() -> tuple[str, list[str]] | None:
    """Retorna o primeiro terminal disponivel + args para passar comando."""
    for binary, args in TERMINAL_CANDIDATES:
        if shutil.which(binary):
            return binary, args
    return None


class VigiaHubWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Vigia Suite")
        self.set_default_size(720, 560)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._build_header())
        toolbar.set_content(self._build_content())
        self.set_content(toolbar)

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        title = Adw.WindowTitle(
            title="Vigia Suite",
            subtitle="Toolkit de seguranca para Fedora Atomic",
        )
        header.set_title_widget(title)
        return header

    def _build_content(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        group.set_title("Ferramentas instaladas")
        group.set_description(
            f"{sum(1 for t in TOOLS if t.is_available())}/{len(TOOLS)} disponiveis"
        )

        for tool in TOOLS:
            row = self._build_tool_row(tool)
            group.add(row)

        page.add(group)
        return page

    def _build_tool_row(self, tool: ToolEntry) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(tool.name)
        row.set_subtitle(tool.description)

        # Icon
        icon = Gtk.Image.new_from_icon_name(tool.icon)
        icon.set_pixel_size(48)
        row.add_prefix(icon)

        # Botao "Abrir"
        btn = Gtk.Button(label="Abrir")
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_valign(Gtk.Align.CENTER)

        if not tool.is_available():
            btn.set_sensitive(False)
            btn.set_label("Nao instalado")
            row.set_subtitle(
                f"{tool.description}\n\n"
                f"[Binario nao encontrado no PATH. Veja README do {tool.id}.]"
            )
        else:
            btn.connect("clicked", lambda _b, t=tool: self._on_launch(t))

        row.add_suffix(btn)
        row.set_activatable_widget(btn)
        return row

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
                    "Nenhum emulador de terminal encontrado (procurei: "
                    + ", ".join(b for b, _ in TERMINAL_CANDIDATES)
                    + "). Instale 'gnome-console' ou similar."
                )
            term_binary, term_args = found
            cmd = [term_binary] + term_args + cmd

        # Spawn nao-bloqueante (Popen sem .wait). Hub fica responsivo.
        subprocess.Popen(cmd)

    def _show_error(self, tool: ToolEntry, message: str) -> None:
        dlg = Adw.AlertDialog(
            heading=f"Falha ao abrir '{tool.name}'",
            body=message,
        )
        dlg.add_response("ok", "OK")
        dlg.present(self)
