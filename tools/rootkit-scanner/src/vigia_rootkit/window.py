"""Janela principal — 4 tabs (chkrootkit, rkhunter, Historico, Sobre).

v0.1.5: removida sub-bar 'Wrapper de:' (pkg badges). Em VM fullscreen
com Rootkit Scanner embedded no Hub, essa barra estava esticando a
janela lateralmente. User identificou no screenshot.

Por que so no Rootkit e nao em outras tools? Investigacao pendente —
provavelmente combinacao de fatores (talvez ordem de inicializacao do
ToolbarView, ou interacao com o ViewStack do Hub). Pra eliminar a
duvida, remover.

Nome dos pacotes wrapped (chkrootkit + rkhunter) ja eh evidente
no titulo da tool e na aba Sobre.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .tabs import AboutTab, ChkrootkitTab, HistoryTab, RkhunterTab


def build_content() -> Gtk.Widget:
    chk_tab = ChkrootkitTab()
    rkh_tab = RkhunterTab()
    history_tab = HistoryTab()
    about_tab = AboutTab()

    stack = Adw.ViewStack()
    stack.add_titled_with_icon(chk_tab, "chkrootkit", "chkrootkit", "edit-find-symbolic")
    stack.add_titled_with_icon(rkh_tab, "rkhunter", "Rootkit Hunter", "system-search-symbolic")
    stack.add_titled_with_icon(history_tab, "history", "Historico", "document-open-recent-symbolic")
    stack.add_titled_with_icon(about_tab, "about", "Sobre", "help-about-symbolic")

    # Refresh on activation — pra Historico atualizar quando volta na tab
    def _on_visible_child_changed(stk, _pspec):
        visible_name = stk.get_visible_child_name()
        tab_map = {
            "chkrootkit": chk_tab,
            "rkhunter": rkh_tab,
            "history": history_tab,
        }
        tab = tab_map.get(visible_name)
        if tab is not None and hasattr(tab, "refresh"):
            try:
                tab.refresh()
            except Exception:  # pylint: disable=broad-except
                pass

    stack.connect("notify::visible-child", _on_visible_child_changed)

    switcher = Adw.ViewSwitcher()
    switcher.set_stack(stack)
    switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)

    header = Adw.HeaderBar()
    header.set_title_widget(switcher)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    # v0.1.5: removida sub-bar 'Wrapper de:' (causa de expansao lateral)
    toolbar.set_content(stack)
    return toolbar


class VigiaRootkitWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("Rootkit Scanner")
        self.set_default_size(900, 720)
        self.set_content(build_content())
