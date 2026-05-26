"""Helper para renderizar sub-bar de WRAPPED_PACKAGES.

Padrao Vigia: cada tool tem WRAPPED_PACKAGES = ["pkg1", "pkg2"]. A janela
mostra uma sub-bar abaixo do header com "Wrapper de: <pkg1> <pkg2>".
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


def make_wrapped_packages_bar(packages: list[str]) -> Gtk.Widget:
    """Cria a sub-bar do header com nome dos pacotes wrapped.

    Uso tipico em window.py:
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        if WRAPPED_PACKAGES:
            toolbar.add_top_bar(make_wrapped_packages_bar(WRAPPED_PACKAGES))
    """
    bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    bar.set_margin_start(12)
    bar.set_margin_end(12)
    bar.set_margin_top(4)
    bar.set_margin_bottom(4)

    intro = Gtk.Label(label="Wrapper de:")
    intro.add_css_class("caption")
    intro.add_css_class("dim-label")
    bar.append(intro)

    for pkg in packages:
        pill = Gtk.Label(label=pkg)
        pill.add_css_class("monospace")
        pill.add_css_class("caption")
        pill.add_css_class("dim-label")
        bar.append(pill)

    return bar
