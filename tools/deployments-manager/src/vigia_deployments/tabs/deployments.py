"""Tab Deployments — lista + rollback + pin/unpin + labels + notas.

Cada deployment vira um Adw.ExpanderRow dentro de Adw.PreferencesGroup.
Header: badge STATUS + label custom + checksum/timestamp.
Expandido: editar label + notas multilinha + lista de pacotes layered + acoes.
"""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend, state
from ._helpers import make_clamp, show_error, show_info


class DeploymentsTab(Adw.Bin):
    """Lista de deployments em PreferencesPage."""

    def __init__(self, on_changed: Callable[[], None] | None = None) -> None:
        super().__init__()
        self._destroyed = False
        self._running = False
        self._on_changed = on_changed
        self._deployment_rows: list = []

        # Banner pra erros (rpm-ostree nao disponivel)
        self._banner = Adw.Banner()
        self._banner.set_revealed(False)

        # Header
        header_lbl = Gtk.Label(label="Deployments rpm-ostree")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label()
        header_desc.set_markup(
            "Cada <b>deployment</b> e um estado imutavel do sistema. "
            "Aparecem no menu do <b>GRUB</b> ao bootar. Sao criados "
            "automaticamente em cada <tt>rpm-ostree install</tt> ou "
            "<tt>upgrade</tt>.\n\n"
            "Voce pode <b>reverter</b> pro anterior, <b>pinnar</b> "
            "(protege do cleanup), ou adicionar <b>label/notas</b> "
            "pra documentar."
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Action bar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_margin_bottom(16)

        refresh_btn = Gtk.Button(label="Atualizar")
        refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(refresh_btn)

        # PreferencesGroup pra lista
        self._list_group = Adw.PreferencesGroup()
        self._list_group.set_title("Deployments")

        # Layout
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(28)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(action_box)
        inner.append(self._list_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._banner)
        outer.append(scrolled)
        self.set_child(outer)

        self.connect("destroy", self._on_destroy)
        self.refresh()

    def _on_destroy(self, *_a) -> None:
        self._destroyed = True

    # ============================================================
    # Refresh
    # ============================================================

    def refresh(self) -> None:
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self) -> None:
        try:
            available = backend.rpmostree_available()
            deployments = backend.get_deployments() if available else []
        except Exception as e:  # pylint: disable=broad-except
            print(f"[deployments] refresh falhou: {e}", flush=True)
            available, deployments = False, []
        GLib.idle_add(self._apply, available, deployments)

    def _apply(self, available: bool, deployments: list[backend.Deployment]) -> bool:
        if self._destroyed:
            return False

        # Banner
        if not available:
            self._banner.set_title(
                "rpm-ostree nao encontrado. Esta tool requer Fedora Atomic "
                "(Silverblue, Kinoite, Bluefin, Bazzite)."
            )
            self._banner.set_revealed(True)
        else:
            self._banner.set_revealed(False)

        # Limpa rows antigos
        for r in self._deployment_rows:
            self._list_group.remove(r)
        self._deployment_rows = []

        if not deployments:
            row = Adw.ActionRow(title="Nenhum deployment encontrado")
            row.set_subtitle("Sistema nao atomic ou erro ao consultar rpm-ostree.")
            row.add_css_class("dim-label")
            self._list_group.add(row)
            self._deployment_rows.append(row)
            return False

        for d in deployments:
            row = self._build_deployment_row(d)
            self._list_group.add(row)
            self._deployment_rows.append(row)

        return False

    # ============================================================
    # Build row pra cada deployment
    # ============================================================

    def _build_deployment_row(self, d: backend.Deployment) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow()

        # Title: label custom OU base_commit
        custom_label = state.get_label(d.checksum)
        if custom_label:
            row.set_title(custom_label)
            row.set_subtitle(f"{d.base_commit} · {d.timestamp_str}")
        else:
            row.set_title(f"Deployment {d.base_commit}")
            row.set_subtitle(d.timestamp_str)

        # Badge de status no prefix
        badge = self._make_status_badge(d)
        row.add_prefix(badge)

        # === Detalhes (expandidos) ===

        # Versao + origin
        info_row = Adw.ActionRow(title="Versao")
        info_row.add_css_class("property")
        info_lbl = Gtk.Label(label=d.version or "(sem versao)")
        info_lbl.add_css_class("monospace")
        info_lbl.add_css_class("caption")
        info_row.add_suffix(info_lbl)
        row.add_row(info_row)

        origin_row = Adw.ActionRow(title="Origem")
        origin_row.add_css_class("property")
        origin_lbl = Gtk.Label(label=d.origin or "(desconhecida)")
        origin_lbl.add_css_class("monospace")
        origin_lbl.add_css_class("caption")
        origin_lbl.set_max_width_chars(40)
        origin_lbl.set_ellipsize(3)  # PangoEllipsizeMode.END
        origin_row.add_suffix(origin_lbl)
        row.add_row(origin_row)

        checksum_row = Adw.ActionRow(title="Commit SHA-256")
        checksum_row.add_css_class("property")
        checksum_lbl = Gtk.Label(label=d.checksum[:16] + "..." if len(d.checksum) > 16 else d.checksum)
        checksum_lbl.add_css_class("monospace")
        checksum_lbl.add_css_class("caption")
        checksum_lbl.set_selectable(True)
        checksum_row.add_suffix(checksum_lbl)
        row.add_row(checksum_row)

        # Label customizado (editavel)
        label_row = Adw.ActionRow(title="Label customizado")
        label_row.set_subtitle("Apelido pra identificar este deployment")
        label_entry = Gtk.Entry()
        label_entry.set_text(custom_label)
        label_entry.set_placeholder_text("ex: Pre instalacao do dnscrypt")
        label_entry.set_valign(Gtk.Align.CENTER)
        label_entry.set_hexpand(False)
        label_entry.set_width_chars(28)
        label_entry.connect("activate", self._on_label_changed, d.checksum, label_entry)

        label_save = Gtk.Button(label="Salvar")
        label_save.set_valign(Gtk.Align.CENTER)
        label_save.add_css_class("suggested-action")
        label_save.connect("clicked", lambda _b: self._on_label_changed(None, d.checksum, label_entry))

        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label_box.set_valign(Gtk.Align.CENTER)
        label_box.append(label_entry)
        label_box.append(label_save)
        label_row.add_suffix(label_box)
        row.add_row(label_row)

        # Notas multilinha (editavel)
        notes_row = Adw.ActionRow()
        notes_row.set_activatable(False)
        notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        notes_box.set_margin_start(8)
        notes_box.set_margin_end(8)
        notes_box.set_margin_top(8)
        notes_box.set_margin_bottom(8)

        notes_lbl = Gtk.Label(label="Notas (LGPD/audit)")
        notes_lbl.add_css_class("heading")
        notes_lbl.set_halign(Gtk.Align.START)
        notes_box.append(notes_lbl)

        notes_view = Gtk.TextView()
        notes_view.set_top_margin(6)
        notes_view.set_bottom_margin(6)
        notes_view.set_left_margin(6)
        notes_view.set_right_margin(6)
        notes_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        notes_view.add_css_class("card")
        notes_view.get_buffer().set_text(state.get_notes(d.checksum), -1)

        notes_scrolled = Gtk.ScrolledWindow()
        notes_scrolled.set_min_content_height(80)
        notes_scrolled.set_max_content_height(140)
        notes_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        notes_scrolled.set_child(notes_view)
        notes_box.append(notes_scrolled)

        notes_save = Gtk.Button(label="Salvar notas")
        notes_save.add_css_class("suggested-action")
        notes_save.set_halign(Gtk.Align.END)
        notes_save.connect("clicked", lambda _b: self._on_notes_save(d.checksum, notes_view))
        notes_box.append(notes_save)

        notes_row.set_child(notes_box)
        row.add_row(notes_row)

        # Pacotes layered (so se houver)
        if d.layered_packages:
            pkg_row = Adw.ActionRow(title=f"Pacotes layered ({len(d.layered_packages)})")
            pkg_row.add_css_class("property")
            pkg_lbl = Gtk.Label(label=", ".join(d.layered_packages[:10]) + ("..." if len(d.layered_packages) > 10 else ""))
            pkg_lbl.add_css_class("monospace")
            pkg_lbl.add_css_class("caption")
            pkg_lbl.add_css_class("dim-label")
            pkg_lbl.set_wrap(True)
            pkg_lbl.set_max_width_chars(40)
            pkg_lbl.set_xalign(1)
            pkg_row.add_suffix(pkg_lbl)
            row.add_row(pkg_row)

        # Acoes (botoes)
        actions_row = Adw.ActionRow()
        actions_row.set_activatable(False)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_halign(Gtk.Align.START)
        actions_box.set_margin_start(8)
        actions_box.set_margin_top(8)
        actions_box.set_margin_bottom(8)

        # Pin/Unpin
        if d.pinned:
            pin_btn = Gtk.Button(label="Despinnar")
            pin_btn.connect("clicked", lambda _b: self._do_unpin(d.index))
        else:
            pin_btn = Gtk.Button(label="Pinnar")
            pin_btn.add_css_class("suggested-action")
            pin_btn.connect("clicked", lambda _b: self._do_pin(d.index))
        actions_box.append(pin_btn)

        # Rollback (apenas se nao for booted)
        if not d.booted:
            rollback_btn = Gtk.Button(label="Reverter pra este (rollback)")
            rollback_btn.add_css_class("destructive-action")
            rollback_btn.connect("clicked", lambda _b: self._do_rollback(d))
            actions_box.append(rollback_btn)

        actions_row.set_child(actions_box)
        row.add_row(actions_row)

        return row

    def _make_status_badge(self, d: backend.Deployment) -> Gtk.Widget:
        """Badge colorido de status no prefix."""
        if d.booted:
            text = "ATIVO"
            css_class = "success"
        elif d.staged:
            text = "STAGED"
            css_class = "warning"
        elif d.pinned:
            text = "PIN"
            css_class = "accent"
        else:
            text = "ROLLBACK"
            css_class = "dim-label"

        lbl = Gtk.Label(label=text)
        lbl.add_css_class("caption")
        lbl.add_css_class(css_class)
        lbl.set_valign(Gtk.Align.CENTER)
        return lbl

    # ============================================================
    # Acoes
    # ============================================================

    def _on_label_changed(self, _entry, checksum: str, entry: Gtk.Entry) -> None:
        new_label = entry.get_text().strip()
        if state.set_label(checksum, new_label):
            show_info(self, "Label salvo", "Label atualizado com sucesso.")
            self.refresh()
        else:
            show_error(self, "Erro", "Falha ao salvar label.")

    def _on_notes_save(self, checksum: str, view: Gtk.TextView) -> None:
        buf = view.get_buffer()
        start, end = buf.get_start_iter(), buf.get_end_iter()
        notes = buf.get_text(start, end, False)
        if state.set_notes(checksum, notes):
            show_info(self, "Notas salvas", "Notas salvas com mode 0600.")
        else:
            show_error(self, "Erro", "Falha ao salvar notas.")

    def _do_pin(self, index: int) -> None:
        if self._running:
            return
        self._running = True
        threading.Thread(
            target=self._pin_worker, args=(index, False), daemon=True,
        ).start()

    def _do_unpin(self, index: int) -> None:
        if self._running:
            return
        self._running = True
        threading.Thread(
            target=self._pin_worker, args=(index, True), daemon=True,
        ).start()

    def _pin_worker(self, index: int, unpin: bool) -> None:
        try:
            if unpin:
                ok, err = backend.unpin_blocking(index)
            else:
                ok, err = backend.pin_blocking(index)
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_pin_done, ok, err, unpin)

    def _on_pin_done(self, ok: bool, err: str, was_unpin: bool) -> bool:
        self._running = False
        action = "despinnar" if was_unpin else "pinnar"
        if not ok:
            show_error(self, f"Falha ao {action}", err)
        else:
            show_info(self, "OK", f"Deployment {action[:-2]+'ado'} com sucesso.")
            self.refresh()
            if self._on_changed:
                self._on_changed()
        return False

    def _do_rollback(self, d: backend.Deployment) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading=f"Reverter pra deployment {d.base_commit}?",
            body=(
                f"Vai trocar o deployment ATIVO pelo selecionado. "
                f"Apos reboot, o sistema vai bootar a partir deste.\n\n"
                f"<b>Detalhes do deployment alvo:</b>\n"
                f"  • Versao: {d.version or '(sem versao)'}\n"
                f"  • Data: {d.timestamp_str}\n"
                f"  • Commit: {d.base_commit}\n\n"
                f"Nenhum dado de usuario sera perdido. <tt>/var</tt> e "
                f"<tt>/home</tt> sao compartilhados entre deployments.\n\n"
                f"Sera pedida senha admin (pkexec)."
            ),
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("rollback", "Reverter")
        dlg.set_response_appearance("rollback", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_rollback_confirmed)
        dlg.present(self.get_root())

    def _on_rollback_confirmed(self, _dlg, response: str) -> None:
        if response != "rollback":
            return
        self._running = True
        threading.Thread(target=self._rollback_worker, daemon=True).start()

    def _rollback_worker(self) -> None:
        try:
            ok, err = backend.rollback_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao: {e}"
        GLib.idle_add(self._on_rollback_done, ok, err)

    def _on_rollback_done(self, ok: bool, err: str) -> bool:
        self._running = False
        if not ok:
            show_error(self, "Falha no rollback", err)
        else:
            show_info(
                self, "Rollback feito",
                "Reinicie o sistema para usar o deployment selecionado.\n\n"
                "(O sistema atual continua rodando ate o reboot.)",
            )
            self.refresh()
            if self._on_changed:
                self._on_changed()
        return False
