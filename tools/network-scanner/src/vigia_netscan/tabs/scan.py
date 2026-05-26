"""Tab Scan: escolhe target + perfil + roda nmap."""

from __future__ import annotations

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ..profiles import PROFILES, default_profile, get_profile
from ._helpers import make_clamp, show_error


# Presets de alvo comum
TARGET_PRESETS: list[tuple[str, str]] = [
    ("localhost", "127.0.0.1"),
    ("rede local /24", "192.168.1.0/24"),
    ("gateway tipico", "192.168.1.1"),
    ("scanme (lab)", "scanme.nmap.org"),
]


class ScanTab(Adw.Bin):
    """Escolhe target + perfil + roda nmap + mostra resultados."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._last_result: backend.ScanResult | None = None

        # Header
        header_lbl = Gtk.Label(label="Network scan")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Use apenas em redes que voce administra ou tem autorizacao "
                "explicita. Scan de redes sem permissao e' crime em varios "
                "paises (Lei Carolina Dieckmann no BR)."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # Target
        target_group = Adw.PreferencesGroup()
        target_group.set_title("Alvo")

        self._target_entry = Gtk.Entry()
        self._target_entry.set_text("192.168.1.0/24")
        self._target_entry.set_placeholder_text("IP, hostname ou CIDR (ex: 192.168.1.0/24)")
        self._target_entry.set_hexpand(True)

        target_row = Adw.ActionRow(title="Target")
        target_row.add_suffix(self._target_entry)
        target_group.add(target_row)

        # Preset chips
        chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chip_box.set_halign(Gtk.Align.START)
        chip_box.append(Gtk.Label(label="Atalhos:"))
        for label, val in TARGET_PRESETS:
            btn = Gtk.Button(label=label)
            btn.add_css_class("pill")
            btn.add_css_class("flat")
            btn.connect("clicked", lambda _b, v=val: self._target_entry.set_text(v))
            chip_box.append(btn)

        preset_row = Adw.ActionRow()
        preset_row.set_child(chip_box)
        preset_row.set_activatable(False)
        target_group.add(preset_row)

        # Profile
        profile_group = Adw.PreferencesGroup()
        profile_group.set_margin_top(24)
        profile_group.set_title("Perfil de scan")

        self._profile_combo = Gtk.DropDown.new_from_strings([p.name for p in PROFILES])
        self._profile_combo.set_selected(PROFILES.index(default_profile()))
        self._profile_combo.connect("notify::selected", lambda *_: self._on_profile_change())

        prof_row = Adw.ActionRow(title="Perfil")
        prof_row.add_suffix(self._profile_combo)
        profile_group.add(prof_row)

        self._profile_desc_label = Gtk.Label()
        self._profile_desc_label.set_wrap(True)
        self._profile_desc_label.set_xalign(0)
        self._profile_desc_label.add_css_class("dim-label")
        self._profile_desc_label.set_margin_start(12)
        self._profile_desc_label.set_margin_end(12)
        self._profile_desc_label.set_margin_top(4)
        self._profile_desc_label.set_margin_bottom(8)
        prof_desc_row = Adw.PreferencesRow()
        prof_desc_row.set_child(self._profile_desc_label)
        prof_desc_row.set_activatable(False)
        profile_group.add(prof_desc_row)

        # Run
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_top(12)
        action_box.set_margin_bottom(12)
        self._run_btn = Gtk.Button(label="Iniciar scan")
        self._run_btn.add_css_class("suggested-action")
        self._run_btn.connect("clicked", lambda _b: self._start_scan())
        action_box.append(self._run_btn)

        self._spinner = Gtk.Spinner()
        self._spinner.set_size_request(20, 20)
        action_box.append(self._spinner)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0)

        # Results
        self._results_group = Adw.PreferencesGroup()
        self._results_group.set_margin_top(24)
        self._results_group.set_title("Resultados")
        self._results_rows: list = []
        self._render_results()

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(24)
        outer.set_margin_bottom(32)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(target_group)
        outer.append(profile_group)
        outer.append(action_box)
        outer.append(self._status_label)
        outer.append(self._results_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self._on_profile_change()

    # ============================================================
    # Profile change handler
    # ============================================================

    def _on_profile_change(self) -> None:
        idx = self._profile_combo.get_selected()
        if idx < 0 or idx >= len(PROFILES):
            return
        p = PROFILES[idx]
        root_note = " · <b>Requer admin (pkexec)</b>" if p.needs_root else ""
        self._profile_desc_label.set_markup(
            f"{p.short_desc}\n"
            f"<i>velocidade:</i> {p.speed} · <i>intrusividade:</i> {p.intrusiveness}"
            f"{root_note}\n"
            f"<i>flags:</i> <tt>nmap {' '.join(p.args)}</tt>"
        )

    # ============================================================
    # Run scan
    # ============================================================

    def _start_scan(self) -> None:
        if self._running:
            return

        target = self._target_entry.get_text().strip()
        if not target:
            show_error(self, "Sem target", "Informe um IP, hostname ou CIDR.")
            return

        ok, err = backend.validate_target(target)
        if not ok:
            show_error(self, "Target invalido", err)
            return

        idx = self._profile_combo.get_selected()
        profile = PROFILES[idx]

        if not backend.nmap_installed():
            show_error(
                self,
                "nmap nao instalado",
                "Instale com: rpm-ostree install nmap && reboot",
            )
            return

        self._running = True
        self._run_btn.set_sensitive(False)
        self._target_entry.set_sensitive(False)
        self._profile_combo.set_sensitive(False)
        self._spinner.start()
        self._status_label.set_label(
            f"Escaneando {target} com perfil '{profile.name}'... "
            + ("Aguarde o dialog de senha." if profile.needs_root else "")
        )

        threading.Thread(
            target=self._scan_worker, args=(target, profile.id), daemon=True
        ).start()

    def _scan_worker(self, target: str, profile_id: str) -> None:
        profile = get_profile(profile_id)
        if profile is None:
            GLib.idle_add(self._on_done, backend.ScanResult(
                target=target, profile_id=profile_id, error="Perfil invalido."
            ))
            return
        result = backend.scan_blocking(target, profile, timeout=900)
        GLib.idle_add(self._on_done, result)

    def _on_done(self, result: backend.ScanResult) -> bool:
        self._running = False
        self._run_btn.set_sensitive(True)
        self._target_entry.set_sensitive(True)
        self._profile_combo.set_sensitive(True)
        self._spinner.stop()

        if result.error:
            self._status_label.set_label(f"Erro: {result.error}")
            return False

        n_hosts = len([h for h in result.hosts if h.status == "up"])
        n_open = sum(
            sum(1 for p in h.ports if p.state == "open")
            for h in result.hosts
        )
        self._status_label.set_label(
            f"Concluido em {result.elapsed_sec}s — "
            f"{n_hosts} host{'s' if n_hosts != 1 else ''} up, "
            f"{n_open} porta{'s' if n_open != 1 else ''} aberta{'s' if n_open != 1 else ''}. "
            "Historico salvo em ~/.local/share/vigia-netscan/."
        )

        self._last_result = result
        self._render_results()
        return False

    # ============================================================
    # Results render
    # ============================================================

    def _render_results(self) -> None:
        for r in self._results_rows:
            self._results_group.remove(r)
        self._results_rows = []

        if self._last_result is None or not self._last_result.hosts:
            row = Adw.ActionRow(title="Nenhum resultado")
            row.set_subtitle(
                "Execute um scan para popular esta lista."
                if self._last_result is None
                else "Nenhum host respondeu."
            )
            row.add_css_class("dim-label")
            self._results_group.add(row)
            self._results_rows.append(row)
            return

        for host in self._last_result.hosts:
            if host.status != "up":
                continue
            row = Adw.ExpanderRow()
            title = host.address or "?"
            if host.hostname:
                title = f"{host.hostname} ({host.address})"
            row.set_title(title)

            n_open = sum(1 for p in host.ports if p.state == "open")
            sub_bits = [f"{n_open} porta{'s' if n_open != 1 else ''} aberta{'s' if n_open != 1 else ''}"]
            if host.os_guess:
                sub_bits.append(f"OS: {host.os_guess}")
            row.set_subtitle(" · ".join(sub_bits))

            badge = Gtk.Label(label="UP")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class("success")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_prefix(badge)

            # Porta rows
            for p in host.ports:
                if p.state != "open":
                    continue
                port_row = Adw.ActionRow(title=f"{p.port}/{p.protocol}")
                bits = []
                if p.service:
                    bits.append(p.service)
                if p.product:
                    bits.append(p.product)
                if p.version:
                    bits.append(p.version)
                port_row.set_subtitle(" · ".join(bits) if bits else "—")
                port_row.add_css_class("property")
                row.add_row(port_row)

            if n_open == 0:
                no_row = Adw.ActionRow(title="(nenhuma porta aberta detectada)")
                no_row.add_css_class("dim-label")
                row.add_row(no_row)

            self._results_group.add(row)
            self._results_rows.append(row)
