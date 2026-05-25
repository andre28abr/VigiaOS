"""Tab Base de dados: info da base + freshclam update."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


class DatabaseTab(Adw.Bin):
    """Mostra info da base de assinaturas + botao atualizar (freshclam)."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False

        # Header
        header_lbl = Gtk.Label(label="Base de assinaturas")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(4)

        header_desc = Gtk.Label(
            label=(
                "A base de dados contem as assinaturas de malware conhecido. "
                "Atualize periodicamente — recomendado pelo menos 1x por semana."
            )
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Info group
        self._info_group = Adw.PreferencesGroup()
        self._info_group.set_title("Estado atual")

        self._engine_row = Adw.ActionRow(title="Engine ClamAV")
        self._engine_row.add_css_class("property")
        self._engine_lbl = Gtk.Label(label="—")
        self._engine_lbl.add_css_class("monospace")
        self._engine_row.add_suffix(self._engine_lbl)
        self._info_group.add(self._engine_row)

        self._db_row = Adw.ActionRow(title="Versao da base")
        self._db_row.add_css_class("property")
        self._db_lbl = Gtk.Label(label="—")
        self._db_lbl.add_css_class("monospace")
        self._db_row.add_suffix(self._db_lbl)
        self._info_group.add(self._db_row)

        self._update_row = Adw.ActionRow(title="Ultimo update")
        self._update_row.add_css_class("property")
        self._update_lbl = Gtk.Label(label="—")
        self._update_lbl.add_css_class("monospace")
        self._update_row.add_suffix(self._update_lbl)
        self._info_group.add(self._update_row)

        self._age_row = Adw.ActionRow(title="Idade da base")
        self._age_row.add_css_class("property")
        self._age_lbl = Gtk.Label(label="—")
        self._age_lbl.add_css_class("monospace")
        self._age_row.add_suffix(self._age_lbl)
        self._info_group.add(self._age_row)

        self._dir_row = Adw.ActionRow(title="Diretorio da base")
        self._dir_row.add_css_class("property")
        self._dir_lbl = Gtk.Label(label="—")
        self._dir_lbl.add_css_class("monospace")
        self._dir_lbl.add_css_class("caption")
        self._dir_row.add_suffix(self._dir_lbl)
        self._info_group.add(self._dir_row)

        # Action
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_top(20)
        action_box.set_margin_bottom(16)

        self._update_btn = Gtk.Button(label="Atualizar base agora")
        self._update_btn.add_css_class("suggested-action")
        self._update_btn.add_css_class("pill")
        self._update_btn.connect("clicked", lambda _b: self._do_update())
        action_box.append(self._update_btn)

        self._refresh_btn = Gtk.Button(label="Recarregar info")
        self._refresh_btn.add_css_class("pill")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        # Status
        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_halign(Gtk.Align.CENTER)
        self._status_label.set_wrap(True)
        self._status_label.set_xalign(0.5)

        # Hint group
        hint_group = Adw.PreferencesGroup()
        hint_group.set_title("Comandos manuais (referencia)")
        for cmd, desc in [
            ("freshclam", "Atualiza base. Roda como root."),
            ("clamscan --version", "Imprime versao e data da base."),
            ("clamscan -r ~/", "Escaneia o home recursivamente."),
            ("systemctl status clamav-freshclam", "Status do timer de update."),
        ]:
            row = Adw.ActionRow(title=cmd)
            row.set_subtitle(desc)
            row.add_css_class("property")
            hint_group.add(row)

        # Layout
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(header_lbl)
        outer.append(header_desc)
        outer.append(self._info_group)
        outer.append(action_box)
        outer.append(self._status_label)
        outer.append(hint_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(outer))
        self.set_child(scrolled)

        self.refresh()

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        info = backend.get_db_info()
        age = backend.db_age_days(info)
        GLib.idle_add(self._apply, info, age)

    def _apply(self, info, age) -> bool:
        self._engine_lbl.set_label(info.engine_version or "?")
        self._db_lbl.set_label(info.db_version or "?")
        self._update_lbl.set_label(info.last_update or "?")
        self._dir_lbl.set_label(info.db_dir or "?")

        for cls in ("success", "warning", "error", "dim-label"):
            self._age_lbl.remove_css_class(cls)

        if age is None:
            self._age_lbl.set_label("desconhecido")
            self._age_lbl.add_css_class("dim-label")
        elif age > 14:
            self._age_lbl.set_label(f"{age} dias")
            self._age_lbl.add_css_class("error")
        elif age > 7:
            self._age_lbl.set_label(f"{age} dias")
            self._age_lbl.add_css_class("warning")
        elif age > 1:
            self._age_lbl.set_label(f"{age} dias")
            self._age_lbl.add_css_class("success")
        else:
            self._age_lbl.set_label("hoje" if age == 0 else "1 dia")
            self._age_lbl.add_css_class("success")

        return False

    # ============================================================
    # Update DB
    # ============================================================

    def _do_update(self) -> None:
        if self._running:
            return
        self._running = True
        self._update_btn.set_sensitive(False)
        self._refresh_btn.set_sensitive(False)
        self._status_label.set_label(
            "Atualizando... isso pode demorar 30-90s. "
            "Aguarde o dialog de senha admin."
        )
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        ok, err = backend.update_db_blocking()
        GLib.idle_add(self._on_update_done, ok, err)

    def _on_update_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._update_btn.set_sensitive(True)
        self._refresh_btn.set_sensitive(True)

        if not ok:
            self._status_label.set_label("")
            show_error(self, "Falha ao atualizar", err)
            return False

        self._status_label.set_label(
            f"Atualizada em {datetime.now().strftime('%d/%m %H:%M')}."
        )
        show_info(
            self,
            "Base atualizada",
            "Base de assinaturas ClamAV foi atualizada com sucesso.",
        )
        self.refresh()
        return False
