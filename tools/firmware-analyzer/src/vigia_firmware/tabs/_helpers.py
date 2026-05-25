"""Helpers compartilhados entre tabs."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402


CONTENT_MAX_WIDTH = 880
CONTENT_TIGHTENING = 720


def make_clamp(child: Gtk.Widget) -> Adw.Clamp:
    clamp = Adw.Clamp(
        maximum_size=CONTENT_MAX_WIDTH,
        tightening_threshold=CONTENT_TIGHTENING,
    )
    clamp.set_child(child)
    return clamp


def show_error(parent: Gtk.Widget, heading: str, message: str) -> None:
    win = parent.get_root()
    dlg = Adw.AlertDialog(heading=heading, body=message)
    dlg.add_response("ok", "OK")
    dlg.present(win)


def show_info(parent: Gtk.Widget, heading: str, message: str) -> None:
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
    """Helper para criar row com Entry + botao 'Escolher arquivo/pasta'.

    O caller passa o Entry para poder ler o valor depois.
    """
    btn = Gtk.Button.new_from_icon_name(
        "folder-open-symbolic" if folder_only else "document-open-symbolic"
    )
    btn.set_tooltip_text("Escolher pasta" if folder_only else "Escolher arquivo")
    btn.set_valign(Gtk.Align.CENTER)

    def on_clicked(_b: Gtk.Button) -> None:
        dlg = Gtk.FileDialog()
        dlg.set_title(title)
        callback = _on_selected_folder if folder_only else _on_selected_file
        if folder_only:
            dlg.select_folder(_root_of(btn), None, lambda d, r: callback(d, r, entry))
        else:
            dlg.open(_root_of(btn), None, lambda d, r: callback(d, r, entry))

    btn.connect("clicked", on_clicked)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    box.append(entry)
    box.append(btn)

    row = Adw.ActionRow(title=title)
    row.add_suffix(box)
    return row


def _root_of(widget: Gtk.Widget):
    return widget.get_root()


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
        pass


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
