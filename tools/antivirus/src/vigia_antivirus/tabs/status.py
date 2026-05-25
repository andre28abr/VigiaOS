"""Tab Status: estado do ClamAV + ultimo scan."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp


class StatusTab(Adw.Bin):
    """Estado do ClamAV (instalado, daemon, base de dados, ultimo scan)."""

    def __init__(self) -> None:
        super().__init__()

        # Hero
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(32)
        self._hero.set_margin_bottom(20)

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

        # Action row
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_bottom(20)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.add_css_class("pill")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        # System info
        self._sys_group = Adw.PreferencesGroup()
        self._sys_group.set_title("Sistema")

        self._installed_row = Adw.ActionRow(title="ClamAV instalado")
        self._installed_row.add_css_class("property")
        self._installed_lbl = Gtk.Label(label="—")
        self._installed_lbl.add_css_class("monospace")
        self._installed_row.add_suffix(self._installed_lbl)
        self._sys_group.add(self._installed_row)

        self._daemon_row = Adw.ActionRow(title="Daemon (clamd)")
        self._daemon_row.add_css_class("property")
        self._daemon_row.set_subtitle("Acelera scans quando ativo (opcional)")
        self._daemon_lbl = Gtk.Label(label="—")
        self._daemon_lbl.add_css_class("monospace")
        self._daemon_row.add_suffix(self._daemon_lbl)
        self._sys_group.add(self._daemon_row)

        # Recent scans
        self._recent_group = Adw.PreferencesGroup()
        self._recent_group.set_title("Scans recentes")
        self._recent_group.set_description(
            "Historico em ~/.local/share/vigia-antivirus/ (permissoes 0600)"
        )
        self._recent_rows: list = []

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_margin_top(0)
        outer.set_margin_bottom(28)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(action_box)
        outer.append(self._sys_group)
        outer.append(self._recent_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        installed = backend.clamav_installed()
        daemon_up = backend.daemon_running() if installed else False
        info = backend.get_db_info() if installed else backend.DbInfo()
        recent = backend.list_recent_reports(limit=5)
        GLib.idle_add(self._apply, installed, daemon_up, info, recent)

    def _apply(self, installed: bool, daemon_up: bool, info, recent: list) -> bool:
        # System rows
        self._installed_lbl.set_label("Sim" if installed else "Nao")
        for cls in ("success", "error"):
            self._installed_lbl.remove_css_class(cls)
        self._installed_lbl.add_css_class("success" if installed else "error")

        self._daemon_lbl.set_label("Ativo" if daemon_up else "Inativo")
        for cls in ("success", "dim-label"):
            self._daemon_lbl.remove_css_class(cls)
        self._daemon_lbl.add_css_class("success" if daemon_up else "dim-label")

        # Hero
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if not installed:
            self._state_label.set_label("ClamAV nao instalado")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Instale via: rpm-ostree install clamav clamav-update && reboot"
            )
        else:
            age = backend.db_age_days(info)
            if age is None:
                self._state_label.set_label("ClamAV pronto")
                self._state_label.add_css_class("warning")
                self._state_sub.set_label(
                    "Base de assinaturas: idade desconhecida. "
                    "Va a 'Base de dados' e clique 'Atualizar agora'."
                )
            elif age > 7:
                self._state_label.set_label("Base desatualizada")
                self._state_label.add_css_class("warning")
                self._state_sub.set_label(
                    f"Ultimo update foi ha {age} dias. Atualize na aba 'Base de dados'."
                )
            elif age > 2:
                self._state_label.set_label("ClamAV pronto")
                self._state_label.add_css_class("success")
                self._state_sub.set_label(
                    f"Base atualizada ha {age} dia{'s' if age != 1 else ''}. "
                    f"Engine {info.engine_version or '?'}."
                )
            else:
                self._state_label.set_label("ClamAV pronto")
                self._state_label.add_css_class("success")
                self._state_sub.set_label(
                    f"Base atualizada hoje. Engine {info.engine_version or '?'}."
                )

        # Recent scans
        for r in self._recent_rows:
            self._recent_group.remove(r)
        self._recent_rows = []

        if not recent:
            row = Adw.ActionRow(title="Nenhum scan realizado ainda")
            row.set_subtitle("Va a aba 'Scan' para iniciar.")
            row.add_css_class("dim-label")
            self._recent_group.add(row)
            self._recent_rows.append(row)
            return False

        for r in recent:
            ts = r.get("started_at", "?")
            try:
                dt = datetime.fromisoformat(ts)
                ts_h = dt.strftime("%d/%m %H:%M")
            except (TypeError, ValueError):
                ts_h = ts
            inf = r.get("infected_files", 0)
            files = r.get("scanned_files", 0)
            target = r.get("target", "?")

            row = Adw.ActionRow(title=ts_h)
            sub = f"{target} · {files} arquivo{'s' if files != 1 else ''}"
            if inf > 0:
                sub += f" · {inf} infectado{'s' if inf != 1 else ''}"
            row.set_subtitle(sub)
            row.set_subtitle_lines(2)

            badge = Gtk.Label(label=str(inf) if inf > 0 else "limpo")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class("error" if inf > 0 else "success")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            self._recent_group.add(row)
            self._recent_rows.append(row)

        return False
