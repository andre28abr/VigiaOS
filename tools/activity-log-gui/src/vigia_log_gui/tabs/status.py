"""Tab Status: info da ultima coleta + sources disponiveis."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .. import backend
from ..backend import ActivityBundle
from ._helpers import make_clamp


SOURCE_DESCS = {
    "audit": "Linux Audit (/var/log/audit/audit.log) — eventos do kernel/SELinux",
    "journal": "systemd-journald — logs do systemd e serviços",
    "journald": "systemd-journald — logs do systemd e serviços",
    "fail2ban": "fail2ban (/var/log/fail2ban.log) — bans automáticos por brute-force",
}


class StatusTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()

        # Hero
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)
        self._hero.set_margin_bottom(28)

        self._state_label = Gtk.Label(label="Verificando...")
        self._state_label.add_css_class("title-1")
        self._state_label.set_halign(Gtk.Align.CENTER)

        self._state_sub = Gtk.Label(label="")
        self._state_sub.add_css_class("title-4")
        self._state_sub.add_css_class("dim-label")
        self._state_sub.set_halign(Gtk.Align.CENTER)
        self._state_sub.set_wrap(True)
        self._state_sub.set_justify(Gtk.Justification.CENTER)
        self._state_sub.set_max_width_chars(56)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # Last collection
        self._last_group = Adw.PreferencesGroup()
        self._last_group.set_title("Última coleta")

        self._row_events = Adw.ActionRow(title="Eventos")
        self._row_events.add_css_class("property")
        self._lbl_events = Gtk.Label(label="—")
        self._lbl_events.add_css_class("monospace")
        self._row_events.add_suffix(self._lbl_events)
        self._last_group.add(self._row_events)

        self._row_susp = Adw.ActionRow(title="Suspicious")
        self._row_susp.add_css_class("property")
        self._lbl_susp = Gtk.Label(label="—")
        self._lbl_susp.add_css_class("monospace")
        self._lbl_susp.add_css_class("error")
        self._row_susp.add_suffix(self._lbl_susp)
        self._last_group.add(self._row_susp)

        self._row_inter = Adw.ActionRow(title="Interesting")
        self._row_inter.add_css_class("property")
        self._lbl_inter = Gtk.Label(label="—")
        self._lbl_inter.add_css_class("monospace")
        self._lbl_inter.add_css_class("warning")
        self._row_inter.add_suffix(self._lbl_inter)
        self._last_group.add(self._row_inter)

        self._row_routine = Adw.ActionRow(title="Routine")
        self._row_routine.add_css_class("property")
        self._lbl_routine = Gtk.Label(label="—")
        self._lbl_routine.add_css_class("monospace")
        self._lbl_routine.add_css_class("dim-label")
        self._row_routine.add_suffix(self._lbl_routine)
        self._last_group.add(self._row_routine)

        self._row_corr = Adw.ActionRow(title="Correlations")
        self._row_corr.add_css_class("property")
        self._lbl_corr = Gtk.Label(label="—")
        self._lbl_corr.add_css_class("monospace")
        self._row_corr.add_suffix(self._lbl_corr)
        self._last_group.add(self._row_corr)

        self._row_when = Adw.ActionRow(title="Gerado em")
        self._row_when.add_css_class("property")
        self._lbl_when = Gtk.Label(label="—")
        self._lbl_when.add_css_class("monospace")
        self._row_when.add_suffix(self._lbl_when)
        self._last_group.add(self._row_when)

        # Sources disponiveis
        self._sources_group = Adw.PreferencesGroup()
        self._sources_group.set_margin_top(24)
        self._sources_group.set_title("Fontes disponíveis")
        self._sources_group.set_description(
            "Sources detectadas neste sistema. Selecione no header quais coletar."
        )

        available = backend.detect_available_sources()
        for src_name in ("audit", "journald", "fail2ban"):
            row = Adw.ActionRow()
            row.set_title(src_name)
            row.set_subtitle(SOURCE_DESCS.get(src_name, ""))
            badge = Gtk.Label(
                label="Disponível" if src_name in available else "Faltando"
            )
            badge.add_css_class("monospace")
            badge.add_css_class("success" if src_name in available else "error")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)
            self._sources_group.add(row)

        # vigia-log info
        info_group = Adw.PreferencesGroup()
        info_group.set_margin_top(24)
        info_group.set_title("Engine")
        row_bin = Adw.ActionRow(title="vigia-log no PATH")
        row_bin.add_css_class("property")
        bin_lbl = Gtk.Label(
            label="Sim" if backend.vigia_log_installed() else "Não"
        )
        bin_lbl.add_css_class("monospace")
        bin_lbl.add_css_class("success" if backend.vigia_log_installed() else "error")
        row_bin.add_suffix(bin_lbl)
        info_group.add(row_bin)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(28)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(self._last_group)
        outer.append(self._sources_group)
        outer.append(info_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh(ActivityBundle())

    def refresh(self, bundle: ActivityBundle) -> None:
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        susp = sum(1 for e in bundle.events if e.severity == "suspicious")
        inter = sum(1 for e in bundle.events if e.severity == "interesting")
        rout = sum(1 for e in bundle.events if e.severity == "routine")

        if not bundle.has_data():
            self._state_label.set_label("Sem dados")
            self._state_label.add_css_class("dim-label")
            self._state_sub.set_label(
                "Clique 'Atualizar' no header para coletar eventos das fontes selecionadas."
            )
        elif susp > 0:
            self._state_label.set_label("Eventos suspeitos detectados")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                f"{susp} evento{'s' if susp > 1 else ''} suspicious."
                " Veja a aba Timeline com filtro Suspicious."
            )
        elif inter > 0:
            self._state_label.set_label("Atividade interessante")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                f"{inter} evento{'s' if inter > 1 else ''} interesting. Nada suspicious."
            )
        else:
            self._state_label.set_label("Atividade rotineira")
            self._state_label.add_css_class("success")
            self._state_sub.set_label("Nada fora do padrão no período coletado.")

        self._lbl_events.set_label(str(len(bundle.events)) if bundle.has_data() else "—")
        self._lbl_susp.set_label(str(susp) if bundle.has_data() else "—")
        self._lbl_inter.set_label(str(inter) if bundle.has_data() else "—")
        self._lbl_routine.set_label(str(rout) if bundle.has_data() else "—")
        self._lbl_corr.set_label(str(len(bundle.correlations)) if bundle.has_data() else "—")
        self._lbl_when.set_label(bundle.generated_at or "—")
