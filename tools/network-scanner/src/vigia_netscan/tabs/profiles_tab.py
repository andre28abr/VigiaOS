"""Tab Perfis: catalogo de perfis de scan."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..profiles import PROFILES
from ._helpers import make_clamp


_RISK_LABELS = {
    "baixo": ("dim-label", "baixo"),
    "medio": ("warning", "medio"),
    "alto": ("error", "alto"),
}

_SPEED_LABELS = {
    "rapido": ("success", "rapido"),
    "medio": ("warning", "medio"),
    "lento": ("dim-label", "lento"),
}


class ProfilesTab(Adw.Bin):
    """Catalogo dos perfis disponiveis, com descricao detalhada."""

    def __init__(self) -> None:
        super().__init__()

        header_lbl = Gtk.Label(label="Perfis de scan")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "Catalogo dos perfis disponiveis. Use a aba <i>Scan</i> "
                "para executar."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Profiles group
        group = Adw.PreferencesGroup()
        group.set_title("Disponiveis")

        for p in PROFILES:
            row = Adw.ExpanderRow()
            row.set_title(p.name)
            row.set_subtitle(p.short_desc)

            speed_cls, speed_lbl = _SPEED_LABELS.get(p.speed, ("dim-label", p.speed))
            risk_cls, risk_lbl = _RISK_LABELS.get(p.intrusiveness, ("dim-label", p.intrusiveness))

            badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            badges.set_valign(Gtk.Align.CENTER)

            sp = Gtk.Label(label=speed_lbl)
            sp.add_css_class("caption-heading")
            sp.add_css_class(speed_cls)
            badges.append(sp)

            sep = Gtk.Label(label="·")
            sep.add_css_class("dim-label")
            badges.append(sep)

            rl = Gtk.Label(label=risk_lbl)
            rl.add_css_class("caption-heading")
            rl.add_css_class(risk_cls)
            badges.append(rl)

            if p.needs_root:
                sep2 = Gtk.Label(label="·")
                sep2.add_css_class("dim-label")
                badges.append(sep2)
                ad = Gtk.Label(label="admin")
                ad.add_css_class("caption-heading")
                ad.add_css_class("warning")
                badges.append(ad)

            row.add_suffix(badges)

            # Descricao longa
            desc_row = Adw.ActionRow()
            lbl = Gtk.Label()
            lbl.set_markup(p.long_desc)
            lbl.set_wrap(True)
            lbl.set_xalign(0)
            lbl.set_margin_start(12)
            lbl.set_margin_end(12)
            lbl.set_margin_top(8)
            lbl.set_margin_bottom(8)
            desc_row.set_child(lbl)
            desc_row.set_activatable(False)
            row.add_row(desc_row)

            # Flags
            flag_row = Adw.ActionRow(title="Comando")
            flag_row.add_css_class("property")
            flag_lbl = Gtk.Label(label=f"nmap {' '.join(p.args)} <target>")
            flag_lbl.add_css_class("monospace")
            flag_lbl.add_css_class("caption")
            flag_row.add_suffix(flag_lbl)
            row.add_row(flag_row)

            group.add(row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)
