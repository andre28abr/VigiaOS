"""Tab Cleanup — botao 'Limpar tudo' + alerta /boot cheio."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import backend
from ._helpers import make_clamp, show_error, show_info


class CleanupTab(Adw.Bin):
    """Cleanup + monitoramento de espaco em /boot."""

    def __init__(self, on_changed: Callable[[], None] | None = None) -> None:
        super().__init__()
        self._destroyed = False
        self._running = False
        self._on_changed = on_changed

        # Banner pra alerta
        self._alert_banner = Adw.Banner()
        self._alert_banner.set_revealed(False)

        # Header
        header_lbl = Gtk.Label(label="Cleanup do sistema")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(6)

        header_desc = Gtk.Label()
        header_desc.set_markup(
            "Limpa deployments antigos e cache de metadados pra liberar "
            "espaço em <tt>/boot</tt> (partição pequena: ~600MB-1GB) e "
            "<tt>/var</tt>.\n\n"
            "<b>O que será limpo</b>:\n"
            "  • <tt>-p</tt> Deployments pending (staged que ainda não bootaram)\n"
            "  • <tt>-r</tt> Deployment de rollback (boot anterior)\n"
            "  • <tt>-m</tt> Cache de refspecs\n\n"
            "<b>Não será afetado</b>: deployment ATIVO, deployments pinados."
        )
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(16)

        # Espaco /boot
        boot_group = Adw.PreferencesGroup()
        boot_group.set_title("Espaço em /boot")
        boot_group.set_description("Partição pequena. Cuidado com acúmulo de deployments.")

        self._row_boot_total = Adw.ActionRow(title="Total")
        self._row_boot_total.add_css_class("property")
        self._lbl_boot_total = Gtk.Label(label="—")
        self._lbl_boot_total.add_css_class("monospace")
        self._row_boot_total.add_suffix(self._lbl_boot_total)
        boot_group.add(self._row_boot_total)

        self._row_boot_used = Adw.ActionRow(title="Usado")
        self._row_boot_used.add_css_class("property")
        self._lbl_boot_used = Gtk.Label(label="—")
        self._lbl_boot_used.add_css_class("monospace")
        self._row_boot_used.add_suffix(self._lbl_boot_used)
        boot_group.add(self._row_boot_used)

        self._row_boot_avail = Adw.ActionRow(title="Disponível")
        self._row_boot_avail.add_css_class("property")
        self._lbl_boot_avail = Gtk.Label(label="—")
        self._lbl_boot_avail.add_css_class("monospace")
        self._row_boot_avail.add_suffix(self._lbl_boot_avail)
        boot_group.add(self._row_boot_avail)

        # Deployments
        deploy_group = Adw.PreferencesGroup()
        deploy_group.set_margin_top(16)
        deploy_group.set_title("Deployments atuais")

        self._row_total_deploys = Adw.ActionRow(title="Total")
        self._row_total_deploys.add_css_class("property")
        self._lbl_total_deploys = Gtk.Label(label="—")
        self._lbl_total_deploys.add_css_class("monospace")
        self._row_total_deploys.add_suffix(self._lbl_total_deploys)
        deploy_group.add(self._row_total_deploys)

        self._row_pinned = Adw.ActionRow(title="Pinados (preservados)")
        self._row_pinned.add_css_class("property")
        self._lbl_pinned = Gtk.Label(label="—")
        self._lbl_pinned.add_css_class("monospace")
        self._row_pinned.add_suffix(self._lbl_pinned)
        deploy_group.add(self._row_pinned)

        self._row_will_clean = Adw.ActionRow(title="Seriam limpos")
        self._row_will_clean.add_css_class("property")
        self._row_will_clean.set_subtitle("Não-ativos, não-pinados, não-staged")
        self._lbl_will_clean = Gtk.Label(label="—")
        self._lbl_will_clean.add_css_class("monospace")
        self._row_will_clean.add_suffix(self._lbl_will_clean)
        deploy_group.add(self._row_will_clean)

        # Action
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_halign(Gtk.Align.CENTER)
        action_box.set_margin_top(24)

        self._refresh_btn = Gtk.Button(label="Atualizar")
        self._refresh_btn.connect("clicked", lambda _b: self.refresh())
        action_box.append(self._refresh_btn)

        self._cleanup_btn = Gtk.Button(label="Limpar tudo (-p -r -m)")
        self._cleanup_btn.add_css_class("suggested-action")
        self._cleanup_btn.connect("clicked", self._on_cleanup_clicked)
        action_box.append(self._cleanup_btn)

        # Layout
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(28)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(boot_group)
        inner.append(deploy_group)
        inner.append(action_box)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.append(self._alert_banner)
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
            usage = backend.get_boot_usage()
            deployments = backend.get_deployments()
        except Exception as e:  # pylint: disable=broad-except
            print(f"[cleanup] refresh falhou: {e}", flush=True)
            usage = backend.BootUsage()
            deployments = []
        GLib.idle_add(self._apply, usage, deployments)

    def _apply(self, usage: backend.BootUsage, deployments: list[backend.Deployment]) -> bool:
        if self._destroyed:
            return False

        # /boot usage
        if usage.available:
            self._lbl_boot_total.set_label(f"{usage.total_mb} MB")
            self._lbl_boot_used.set_label(f"{usage.used_mb} MB ({usage.percent_used}%)")
            self._lbl_boot_avail.set_label(f"{usage.avail_mb} MB")

            # Coloring
            for cls in ("success", "warning", "error"):
                self._lbl_boot_used.remove_css_class(cls)
            if usage.percent_used >= 85:
                self._lbl_boot_used.add_css_class("error")
                self._alert_banner.set_title(
                    f"⚠ /boot está {usage.percent_used}% cheio. "
                    f"Limpe deployments antigos."
                )
                self._alert_banner.set_revealed(True)
            elif usage.percent_used >= 70:
                self._lbl_boot_used.add_css_class("warning")
                self._alert_banner.set_revealed(False)
            else:
                self._lbl_boot_used.add_css_class("success")
                self._alert_banner.set_revealed(False)
        else:
            self._lbl_boot_total.set_label("(não montado)")
            self._lbl_boot_used.set_label("—")
            self._lbl_boot_avail.set_label("—")
            self._alert_banner.set_revealed(False)

        # Deployments stats
        total = len(deployments)
        pinned = sum(1 for d in deployments if d.pinned)
        # Will clean: nao-booted, nao-pinned, nao-staged
        will_clean = sum(
            1 for d in deployments
            if not d.booted and not d.pinned and not d.staged
        )

        self._lbl_total_deploys.set_label(str(total))
        self._lbl_pinned.set_label(str(pinned))
        self._lbl_will_clean.set_label(str(will_clean))

        if will_clean > 0:
            self._lbl_will_clean.add_css_class("warning")
        else:
            for cls in ("warning", "error"):
                self._lbl_will_clean.remove_css_class(cls)

        return False

    # ============================================================
    # Cleanup action
    # ============================================================

    def _on_cleanup_clicked(self, _btn) -> None:
        if self._running:
            return

        dlg = Adw.AlertDialog(
            heading="Limpar tudo (cleanup -p -r -m)?",
            body=(
                "Vai executar <tt>pkexec rpm-ostree cleanup -p -r -m</tt> "
                "num só call.\n\n"
                "<b>O que será removido</b>:\n"
                "  • Deployments <b>pending</b> (staged que não bootaram)\n"
                "  • Deployment de <b>rollback</b> (boot anterior)\n"
                "  • <b>Cache de refspecs</b> (metadados antigos)\n\n"
                "<b>Preservados</b>: deployment ATIVO + pinados.\n\n"
                "Será pedida senha admin (pkexec)."
            ),
        )
        dlg.set_body_use_markup(True)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("cleanup", "Limpar tudo")
        dlg.set_response_appearance("cleanup", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_cleanup_confirmed)
        dlg.present(self.get_root())

    def _on_cleanup_confirmed(self, _dlg, response: str) -> None:
        if response != "cleanup":
            return
        self._running = True
        self._cleanup_btn.set_sensitive(False)
        threading.Thread(target=self._cleanup_worker, daemon=True).start()

    def _cleanup_worker(self) -> None:
        try:
            ok, err = backend.cleanup_all_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Exceção: {e}"
        GLib.idle_add(self._on_cleanup_done, ok, err)

    def _on_cleanup_done(self, ok: bool, err: str) -> bool:
        self._running = False
        self._cleanup_btn.set_sensitive(True)
        if not ok:
            show_error(self, "Falha no cleanup", err)
        else:
            show_info(
                self, "Cleanup concluído",
                "Pending, rollback e cached refs limpos. "
                "Espaço em /boot liberado.",
            )
            self.refresh()
            if self._on_changed:
                self._on_changed()
        return False
