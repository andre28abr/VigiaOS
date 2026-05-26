"""Tab Biblioteca: lista de relatorios HTML ja gerados."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import backend, renderer
from ._helpers import make_clamp, show_error


class LibraryTab(Adw.Bin):
    """Lista os HTMLs em ~/.local/share/vigia-reports/ com botoes Abrir/Excluir."""

    def __init__(self) -> None:
        super().__init__()

        # Header
        self._header_label = Gtk.Label(label="—")
        self._header_label.add_css_class("title-2")
        self._header_label.set_halign(Gtk.Align.START)
        self._header_label.set_margin_bottom(4)

        self._header_desc = Gtk.Label(label="")
        self._header_desc.add_css_class("dim-label")
        self._header_desc.set_halign(Gtk.Align.START)
        self._header_desc.set_wrap(True)
        self._header_desc.set_xalign(0)
        self._header_desc.set_margin_bottom(24)

        # Toolbar com botao "Abrir pasta" + "Atualizar"
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_bottom(12)

        open_dir_btn = Gtk.Button(label="Abrir pasta")
        open_dir_btn.connect("clicked", self._on_open_dir_clicked)
        toolbar.append(open_dir_btn)

        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Atualizar lista")
        refresh_btn.connect("clicked", lambda _b: self.refresh())
        toolbar.append(refresh_btn)

        # Listbox
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        self._empty_state = Adw.StatusPage(
            title="Sem relatorios",
            description="Use a aba 'Gerar' para criar o primeiro. Eles aparecem aqui.",
            icon_name="document-symbolic",
        )
        self._empty_state.set_vexpand(True)

        self._stack = Gtk.Stack()
        self._stack.add_named(self._list, "list")
        self._stack.add_named(self._empty_state, "empty")

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(self._header_label)
        outer.append(self._header_desc)
        outer.append(toolbar)
        outer.append(self._stack)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    # ============================================================
    # API
    # ============================================================

    def refresh(self) -> None:
        # Clear list
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        reports_dir = backend.REPORTS_DIR
        if not reports_dir.is_dir():
            self._header_label.set_label("Sem relatorios")
            self._header_desc.set_label(f"Pasta nao existe ainda: {reports_dir}")
            self._stack.set_visible_child_name("empty")
            return

        files = sorted(
            reports_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not files:
            self._header_label.set_label("Sem relatorios")
            self._header_desc.set_label(f"Pasta: {reports_dir}")
            self._stack.set_visible_child_name("empty")
            return

        self._header_label.set_label(
            f"{len(files)} {'relatorio' if len(files) == 1 else 'relatorios'}"
        )
        self._header_desc.set_label(f"Pasta: {reports_dir}")
        self._stack.set_visible_child_name("list")

        for path in files:
            self._list.append(self._build_row(path))

    # ============================================================
    # Internal
    # ============================================================

    def _build_row(self, path: Path) -> Adw.ActionRow:
        # Extrai template id do nome (formato: <template>-<timestamp>.html)
        stem = path.stem
        parts = stem.rsplit("-", 2)
        if len(parts) >= 3:
            template_id = parts[0]
        else:
            template_id = stem

        name = renderer.get_template_name(template_id)
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        size_kb = max(1, path.stat().st_size // 1024)

        row = Adw.ActionRow(title=name)
        row.set_subtitle(
            f"{mtime.strftime('%Y-%m-%d %H:%M:%S')} · {size_kb} KB · {path.name}"
        )

        open_btn = Gtk.Button(label="Abrir")
        open_btn.add_css_class("flat")
        open_btn.set_valign(Gtk.Align.CENTER)
        open_btn.connect("clicked", self._on_open_clicked, path)
        row.add_suffix(open_btn)

        delete_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.set_tooltip_text("Excluir")
        delete_btn.connect("clicked", self._on_delete_clicked, path)
        row.add_suffix(delete_btn)

        return row

    def _on_open_clicked(self, _btn: Gtk.Button, path: Path) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(f"file://{path}", None)
        except Exception:
            try:
                subprocess.Popen(["xdg-open", str(path)])
            except Exception as e:
                show_error(self, "Falha ao abrir", str(e))

    def _on_open_dir_clicked(self, _btn: Gtk.Button) -> None:
        reports_dir = backend.ensure_reports_dir()
        try:
            Gio.AppInfo.launch_default_for_uri(f"file://{reports_dir}", None)
        except Exception:
            try:
                subprocess.Popen(["xdg-open", str(reports_dir)])
            except Exception as e:
                show_error(self, "Falha ao abrir", str(e))

    def _on_delete_clicked(self, _btn: Gtk.Button, path: Path) -> None:
        dlg = Adw.AlertDialog(
            heading="Excluir relatorio?",
            body=f"{path.name}\n\nEsta acao nao pode ser desfeita.",
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("delete", "Excluir")
        dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_delete_response, path)
        dlg.present(self.get_root())

    def _on_delete_response(self, _dlg, response: str, path: Path) -> None:
        if response == "delete":
            try:
                path.unlink()
                self.refresh()
            except OSError as e:
                show_error(self, "Falha ao excluir", str(e))
