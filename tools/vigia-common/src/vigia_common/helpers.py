"""Helpers de UI compartilhados entre as tools do VigiaOS.

API estavel — modificacoes devem ser retro-compativeis.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import CONTENT_MAX_WIDTH, CONTENT_TIGHTENING


def make_clamp(
    child: Gtk.Widget,
    maximum_size: int = CONTENT_MAX_WIDTH,
    tightening_threshold: int = CONTENT_TIGHTENING,
) -> Adw.Clamp:
    """Wrappa widget em Adw.Clamp com defaults da Vigia.

    Args:
        child: widget filho
        maximum_size: largura maxima do clamp em px (default 820)
        tightening_threshold: largura onde comeca a apertar (default 640)
    """
    clamp = Adw.Clamp(
        maximum_size=maximum_size,
        tightening_threshold=tightening_threshold,
    )
    clamp.set_child(child)
    return clamp


def show_error(parent: Gtk.Widget, heading: str, message: str) -> None:
    """Adw.AlertDialog modal de erro com botao OK."""
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)


def show_info(parent: Gtk.Widget, heading: str, message: str) -> None:
    """Adw.AlertDialog modal informativo com botao OK."""
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)


def make_file_picker_row(
    title: str,
    entry: Gtk.Entry,
    *,
    folder_only: bool = False,
) -> Adw.ActionRow:
    """Cria row com Entry + botao 'Escolher arquivo/pasta'.

    O caller passa o Entry para poder ler o valor depois. Clicar no
    botao abre Gtk.FileDialog e popula o entry com o path escolhido.

    Args:
        title: label do row (ex: 'Arquivo')
        entry: Gtk.Entry pre-criado (caller controla placeholder, texto)
        folder_only: se True, escolhe pasta; se False, escolhe arquivo
    """
    btn = Gtk.Button.new_from_icon_name(
        "folder-open-symbolic" if folder_only else "document-open-symbolic"
    )
    btn.set_tooltip_text("Escolher pasta" if folder_only else "Escolher arquivo")
    btn.set_valign(Gtk.Align.CENTER)

    def on_clicked(_b: Gtk.Button) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title(title)
        if folder_only:
            dlg.select_folder(
                btn.get_root(), None,
                lambda d, r: _on_selected_folder(d, r, entry),
            )
        else:
            dlg.open(
                btn.get_root(), None,
                lambda d, r: _on_selected_file(d, r, entry),
            )

    btn.connect("clicked", on_clicked)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    box.append(entry)
    box.append(btn)

    row = Adw.ActionRow(title=title)
    row.add_suffix(box)
    return row


def _on_selected_file(
    dialog: Gtk.FileDialog,
    result: Gio.AsyncResult,
    entry: Gtk.Entry,
) -> None:
    try:
        f = dialog.open_finish(result)
        if f:
            entry.set_text(f.get_path() or "")
    except GLib.Error:
        pass  # user cancelou


def _on_selected_folder(
    dialog: Gtk.FileDialog,
    result: Gio.AsyncResult,
    entry: Gtk.Entry,
) -> None:
    try:
        f = dialog.select_folder_finish(result)
        if f:
            entry.set_text(f.get_path() or "")
    except GLib.Error:
        pass


def copy_to_clipboard(widget: Gtk.Widget, text: str) -> None:
    """Copia texto para clipboard via Gdk.Display do widget."""
    display = widget.get_display()
    if display is None:
        return
    clipboard = display.get_clipboard()
    clipboard.set(text)
