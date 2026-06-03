"""Tab Status: estado do baseline + acoes principais + controle de perfil."""

from __future__ import annotations

import threading
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from vigia_common.platform import install_hint

from .. import backend
from ._helpers import make_clamp, show_error, show_info


class StatusTab(Adw.Bin):
    """Hero card + acoes: criar baseline, verificar, atualizar."""

    def __init__(
        self,
        on_check_done: Callable[["backend.CheckResult"], None],
    ) -> None:
        super().__init__()
        self._on_check_done = on_check_done
        self._running = False
        self._pulse_id: int | None = None
        self._operation_label = "Trabalhando..."

        # Cleanup ao destruir o widget (evita memory leak do GLib.timeout)
        self.connect("destroy", self._on_destroy)

        # ---- Hero ---- #
        self._hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._hero.set_halign(Gtk.Align.CENTER)
        self._hero.set_margin_top(36)
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
        self._state_sub.set_max_width_chars(48)

        self._hero.append(self._state_label)
        self._hero.append(self._state_sub)

        # ---- Stats ---- #
        self._stats_group = Adw.PreferencesGroup()
        self._stats_group.set_title("Ultimo check")

        self._row_total = Adw.ActionRow(title="Total de entradas monitoradas")
        self._row_total.add_css_class("property")
        self._lbl_total = Gtk.Label(label="—")
        self._lbl_total.add_css_class("monospace")
        self._row_total.add_suffix(self._lbl_total)

        self._row_added = Adw.ActionRow(title="Adicionadas")
        self._row_added.add_css_class("property")
        self._lbl_added = Gtk.Label(label="—")
        self._lbl_added.add_css_class("monospace")
        self._row_added.add_suffix(self._lbl_added)

        self._row_removed = Adw.ActionRow(title="Removidas")
        self._row_removed.add_css_class("property")
        self._lbl_removed = Gtk.Label(label="—")
        self._lbl_removed.add_css_class("monospace")
        self._row_removed.add_suffix(self._lbl_removed)

        self._row_changed = Adw.ActionRow(title="Modificadas")
        self._row_changed.add_css_class("property")
        self._lbl_changed = Gtk.Label(label="—")
        self._lbl_changed.add_css_class("monospace")
        self._row_changed.add_suffix(self._lbl_changed)

        self._row_when = Adw.ActionRow(title="Quando")
        self._row_when.add_css_class("property")
        self._lbl_when = Gtk.Label(label="Nunca")
        self._lbl_when.add_css_class("monospace")
        self._row_when.add_suffix(self._lbl_when)

        for r in (self._row_total, self._row_added, self._row_removed, self._row_changed, self._row_when):
            self._stats_group.add(r)

        # ---- Baseline info ---- #
        self._baseline_group = Adw.PreferencesGroup()
        self._baseline_group.set_margin_top(24)
        self._baseline_group.set_title("Baseline")

        self._row_baseline_age = Adw.ActionRow(title="Criado")
        self._row_baseline_age.add_css_class("property")
        self._lbl_baseline_age = Gtk.Label(label="—")
        self._lbl_baseline_age.add_css_class("monospace")
        self._row_baseline_age.add_suffix(self._lbl_baseline_age)
        self._baseline_group.add(self._row_baseline_age)

        # ---- Actions ---- #
        self._actions_group = Adw.PreferencesGroup()
        self._actions_group.set_margin_top(24)
        self._actions_group.set_title("Acoes")

        # Check
        self._check_row = Adw.ActionRow(title="Verificar integridade")
        self._check_row.set_subtitle("Compara o sistema com o baseline. Pode demorar vários minutos.")
        self._check_btn = Gtk.Button(label="Verificar")
        self._check_btn.add_css_class("suggested-action")
        self._check_btn.set_valign(Gtk.Align.CENTER)
        self._check_btn.connect("clicked", self._on_check_clicked)
        self._check_row.add_suffix(self._check_btn)
        self._actions_group.add(self._check_row)

        # Init / Update
        self._init_row = Adw.ActionRow(title="Criar baseline")
        self._init_row.set_subtitle("Snapshot inicial do sistema. Faça quando ele estiver 'limpo'.")
        self._init_btn = Gtk.Button(label="Criar")
        self._init_btn.set_valign(Gtk.Align.CENTER)
        self._init_btn.connect("clicked", self._on_init_clicked)
        self._init_row.add_suffix(self._init_btn)
        self._actions_group.add(self._init_row)

        self._update_row = Adw.ActionRow(title="Re-baseline (apos updates legitimos)")
        self._update_row.set_subtitle("Aceita as mudanças atuais como nova baseline.")
        self._update_btn = Gtk.Button(label="Atualizar")
        self._update_btn.set_valign(Gtk.Align.CENTER)
        self._update_btn.connect("clicked", self._on_update_clicked)
        self._update_row.add_suffix(self._update_btn)
        self._actions_group.add(self._update_row)

        # ---- Progress ---- #
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._progress_box.set_visible(False)
        self._progress_box.set_margin_top(16)
        self._progress_label = Gtk.Label(label="Trabalhando...")
        self._progress_label.add_css_class("dim-label")
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_pulse_step(0.1)
        self._progress_box.append(self._progress_label)
        self._progress_box.append(self._progress_bar)

        # ---- Layout ---- #
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        outer.set_margin_top(20)
        outer.set_margin_bottom(32)
        outer.set_margin_start(20)
        outer.set_margin_end(20)
        outer.append(self._hero)
        outer.append(self._stats_group)
        outer.append(self._baseline_group)
        outer.append(self._actions_group)
        outer.append(self._progress_box)

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
        installed = backend.aide_installed()
        has_baseline = backend.baseline_exists()
        last_ts, last_summary = backend.get_last_check()

        # Estado
        for cls in ("success", "warning", "error", "dim-label"):
            self._state_label.remove_css_class(cls)

        if not installed:
            self._state_label.set_label("AIDE não instalado")
            self._state_label.add_css_class("error")
            self._state_sub.set_label(
                "Para usar, instale o AIDE: " + install_hint("aide")
            )
        elif not has_baseline:
            self._state_label.set_label("Sem baseline")
            self._state_label.add_css_class("warning")
            self._state_sub.set_label(
                "Crie um baseline para começar a monitorar integridade dos arquivos."
            )
        elif last_summary is None:
            self._state_label.set_label("Baseline ativo")
            self._state_label.add_css_class("dim-label")
            self._state_sub.set_label(
                "Baseline criado, ainda não houve verificação. Clique 'Verificar'."
            )
        elif last_summary.has_changes:
            self._state_label.set_label("Mudanças detectadas")
            self._state_label.add_css_class("warning")
            n = last_summary.added + last_summary.removed + last_summary.changed
            self._state_sub.set_label(
                f"{n} arquivos divergem do baseline. Veja a aba 'Mudanças'."
            )
        else:
            self._state_label.set_label("Integro")
            self._state_label.add_css_class("success")
            self._state_sub.set_label("Sistema bate com o baseline. Nada mudou.")

        # Stats
        if last_summary is not None:
            self._lbl_total.set_label(f"{last_summary.total_entries:,}".replace(",", "."))
            self._lbl_added.set_label(str(last_summary.added))
            self._lbl_removed.set_label(str(last_summary.removed))
            self._lbl_changed.set_label(str(last_summary.changed))
        else:
            for lbl in (self._lbl_total, self._lbl_added, self._lbl_removed, self._lbl_changed):
                lbl.set_label("—")

        if last_ts is not None:
            self._lbl_when.set_label(last_ts.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            self._lbl_when.set_label("Nunca")

        # Baseline info
        age = backend.baseline_age_seconds()
        self._lbl_baseline_age.set_label(backend.format_age(age))

        # Botoes
        self._check_btn.set_sensitive(installed and has_baseline and not self._running)
        self._init_btn.set_sensitive(installed and not self._running)
        self._init_btn.set_label("Recriar" if has_baseline else "Criar")
        self._update_btn.set_sensitive(installed and has_baseline and not self._running)

    # ============================================================
    # Actions
    # ============================================================

    def _on_check_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        self._set_running(True, "Verificando integridade (pode demorar vários minutos)...")
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        try:
            result = backend.run_check_blocking()
        except Exception as e:  # pylint: disable=broad-except
            result = backend.CheckResult(
                success=False, summary=backend.CheckSummary(), changes=[],
                error=f"Excecao no worker: {e}",
            )
        GLib.idle_add(self._on_check_finished, result)

    def _on_check_finished(self, result: backend.CheckResult) -> bool:
        self._set_running(False)
        if not result.success:
            show_error(self, "Verificacao falhou", result.error or "Erro desconhecido.")
        else:
            self.refresh()
            self._on_check_done(result)
        return False

    def _on_init_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return

        if backend.baseline_exists():
            dlg = Adw.AlertDialog(
                heading="Recriar baseline?",
                body=(
                    "Vai sobrescrever o baseline atual. Use esta opção se você quer "
                    "começar do zero (ex: depois de uma reinstalação limpa do sistema)."
                ),
            )
            dlg.add_response("cancel", "Cancelar")
            dlg.add_response("init", "Recriar")
            dlg.set_response_appearance("init", Adw.ResponseAppearance.DESTRUCTIVE)
            dlg.set_default_response("cancel")
            dlg.connect("response", self._on_init_confirmed)
            dlg.present(self.get_root())
        else:
            self._do_init()

    def _on_init_confirmed(self, _dlg, response: str) -> None:
        if response == "init":
            self._do_init()

    def _do_init(self) -> None:
        self._set_running(True, "Criando baseline (pode demorar bastante)...")
        threading.Thread(target=self._init_worker, daemon=True).start()

    def _init_worker(self) -> None:
        try:
            ok, err = backend.run_init_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao no worker: {e}"
        GLib.idle_add(self._on_init_finished, ok, err)

    def _on_init_finished(self, ok: bool, err: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, "Falha ao criar baseline", err)
        else:
            show_info(self, "Baseline criado", "O baseline está ativo. Agora 'Verificar' compara contra ele.")
            self.refresh()
        return False

    def _on_update_clicked(self, _btn: Gtk.Button) -> None:
        if self._running:
            return
        dlg = Adw.AlertDialog(
            heading="Aceitar mudanças atuais?",
            body=(
                "Re-baseline aceita o estado atual do sistema como referência. "
                "Faça isso após uma atualização legítima do sistema (dnf, etc.).\n\n"
                "Se você não consegue explicar as mudanças, NÃO aceite — investigue primeiro."
            ),
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("update", "Aceitar e atualizar")
        dlg.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.connect("response", self._on_update_confirmed)
        dlg.present(self.get_root())

    def _on_update_confirmed(self, _dlg, response: str) -> None:
        if response != "update":
            return
        self._set_running(True, "Atualizando baseline...")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self) -> None:
        try:
            ok, err = backend.run_update_blocking()
        except Exception as e:  # pylint: disable=broad-except
            ok, err = False, f"Excecao no worker: {e}"
        GLib.idle_add(self._on_update_finished, ok, err)

    def _on_update_finished(self, ok: bool, err: str) -> bool:
        self._set_running(False)
        if not ok:
            show_error(self, "Falha ao atualizar baseline", err)
        else:
            show_info(self, "Baseline atualizado", "O estado atual foi aceito como nova referência.")
            self.refresh()
        return False

    # ============================================================
    # Progress
    # ============================================================

    def _set_running(self, running: bool, label: str = "Trabalhando...") -> None:
        self._running = running
        self._progress_box.set_visible(running)
        self._progress_label.set_label(label)
        if running:
            self._pulse_id = GLib.timeout_add(100, self._pulse_tick)
        elif self._pulse_id is not None:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = None
        # Recalcula sensibilidades
        installed = backend.aide_installed()
        has_baseline = backend.baseline_exists()
        self._check_btn.set_sensitive(installed and has_baseline and not running)
        self._init_btn.set_sensitive(installed and not running)
        self._update_btn.set_sensitive(installed and has_baseline and not running)

    def _pulse_tick(self) -> bool:
        self._progress_bar.pulse()
        return self._running

    def _on_destroy(self, *_args) -> None:
        """Cleanup: para o GLib.timeout do pulse bar (memory leak fix)."""
        if self._pulse_id is not None:
            try:
                GLib.source_remove(self._pulse_id)
            except Exception:  # pylint: disable=broad-except
                pass
            self._pulse_id = None
