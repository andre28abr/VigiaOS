"""Tab Correlations: padroes cross-source detectados."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from ..backend import ActivityBundle, ActivityCorrelation
from ._helpers import escape_markup, make_clamp, severity_css, severity_label


CORRELATION_KIND_LABELS = {
    "fail2ban_burst": "fail2ban burst",
    "oom_kill": "OOM kill",
    "selinux_burst": "SELinux burst",
    "ssh_suspeito": "SSH suspeito",
}


class CorrelationsTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()

        # Header
        self._header_label = Gtk.Label(label="—")
        self._header_label.add_css_class("title-2")
        self._header_label.set_halign(Gtk.Align.START)
        self._header_label.set_margin_bottom(4)

        self._header_desc = Gtk.Label(
            label=(
                "Correlations são padrões detectados cross-source: ex. "
                "*fail2ban baniu IP X após 3 tentativas SSH* combina eventos do "
                "fail2ban + audit em uma única narrativa."
            )
        )
        self._header_desc.add_css_class("dim-label")
        self._header_desc.set_halign(Gtk.Align.START)
        self._header_desc.set_wrap(True)
        self._header_desc.set_xalign(0)
        self._header_desc.set_use_markup(False)
        self._header_desc.set_margin_bottom(24)

        # List
        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")

        self._empty_state = Adw.StatusPage(
            title="Sem correlations",
            description="Nenhum padrão cross-source detectado nos eventos atuais.",
            icon_name="dialog-information-symbolic",
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
        outer.append(self._stack)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

    def refresh(self, bundle: ActivityBundle) -> None:
        # Clear
        child = self._list.get_first_child()
        while child is not None:
            self._list.remove(child)
            child = self._list.get_first_child()

        corrs = bundle.correlations
        if not corrs:
            self._stack.set_visible_child_name("empty")
            self._header_label.set_label("—")
            return

        self._stack.set_visible_child_name("list")
        self._header_label.set_label(
            f"{len(corrs)} correlation{'s' if len(corrs) > 1 else ''}"
        )

        for c in corrs:
            self._list.append(self._build_row(c))

    def _build_row(self, c: ActivityCorrelation) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_title(escape_markup(c.summary))
        row.set_use_markup(True)
        row.set_title_lines(3)
        kind_lbl = CORRELATION_KIND_LABELS.get(c.kind, c.kind)
        row.set_subtitle(
            f"{c.timestamp} → {c.end} · {kind_lbl} · {c.contributing_count} eventos"
        )

        # Severity badge
        sev_badge = Gtk.Label(label=severity_label(c.severity))
        sev_badge.add_css_class("monospace")
        sev_badge.add_css_class("caption-heading")
        sev_badge.add_css_class(severity_css(c.severity))
        sev_badge.set_valign(Gtk.Align.CENTER)
        row.add_prefix(sev_badge)

        return row
