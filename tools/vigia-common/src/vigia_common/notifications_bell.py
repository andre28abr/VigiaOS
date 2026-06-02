"""Sininho de notificações do rail (botão + bolinha vermelha + popover).

Reutilizado pelo Vigia Hub e pelos produtos (Blue/Red, via shell). Fica no
rodapé da coluna fina da esquerda. A **bolinha vermelha** usa o mesmo padrão
do dot de status da coluna do meio (um `Label("●")` com classe de cor), só que
vermelho (`error`). Clicar abre um popover (mini menu) listando as notificações.

Uso:

    bell = NotificationsBell()
    bell.set_notifications([Notification("Título", "Detalhe", "ícone")])

`set_notifications([])` esconde a bolinha e mostra "Sem notificações".
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .notices import Notification


class NotificationsBell(Gtk.MenuButton):
    """Botão-sininho com bolinha vermelha + popover listando notificações."""

    def __init__(self, empty_text: str = "Sem notificações no momento.") -> None:
        super().__init__()
        self.add_css_class("flat")
        self._empty_text = empty_text
        self._notifications: list[Notification] = []

        # Conteúdo do botão: sino + bolinha vermelha (overlay no canto).
        overlay = Gtk.Overlay()
        bell = Gtk.Image.new_from_icon_name(
            "preferences-system-notifications-symbolic")
        bell.set_pixel_size(20)
        overlay.set_child(bell)

        self._dot = Gtk.Label(label="●")
        self._dot.add_css_class("error")   # vermelho (mesmo padrão do verde)
        self._dot.add_css_class("caption")
        self._dot.set_halign(Gtk.Align.END)
        self._dot.set_valign(Gtk.Align.START)
        self._dot.set_visible(False)
        overlay.add_overlay(self._dot)
        self.set_child(overlay)

        # Popover (mini menu ao lado).
        self._popover = Gtk.Popover()
        self._popover.set_position(Gtk.PositionType.RIGHT)
        self.set_popover(self._popover)

        self.set_notifications([])

    # ------------------------------------------------------------------

    def set_notifications(self, notifications) -> None:
        """Atualiza a bolinha + reconstrói o popover."""
        self._notifications = list(notifications)
        n = len(self._notifications)
        self._dot.set_visible(n > 0)
        self.set_tooltip_text(
            f"{n} notificação(ões)" if n else "Notificações")
        self._rebuild()

    def _rebuild(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_size_request(300, -1)

        header = Gtk.Label(label="Notificações")
        header.add_css_class("heading")
        header.set_xalign(0)
        box.append(header)

        if not self._notifications:
            empty = Gtk.Label(label=self._empty_text)
            empty.add_css_class("dim-label")
            empty.set_wrap(True)
            empty.set_xalign(0)
            box.append(empty)
        else:
            lst = Gtk.ListBox()
            lst.add_css_class("boxed-list")
            lst.set_selection_mode(Gtk.SelectionMode.NONE)
            for note in self._notifications:
                row = Adw.ActionRow()
                row.set_title(note.title)
                if note.subtitle:
                    row.set_subtitle(note.subtitle)
                    row.set_subtitle_lines(0)
                row.add_prefix(Gtk.Image.new_from_icon_name(note.icon))
                lst.append(row)
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(
                Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(360)
            scrolled.set_propagate_natural_height(True)
            scrolled.set_child(lst)
            box.append(scrolled)

        self._popover.set_child(box)
