"""Tab Alertas (v0.2): regras configuraveis + historico de disparos."""

from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from vigia_common.notifications import PRIORITY_HIGH, notify

from .. import alerts as alerts_mod
from .. import backend
from ._helpers import make_clamp, show_error


REFRESH_MS = 2000   # Avalia cada 2s


class AlertsTab(Adw.Bin):
    """Lista regras + adicionar/editar/remover + historico de eventos."""

    def __init__(self) -> None:
        super().__init__()
        self._tick_id = 0
        self._manager = alerts_mod.AlertManager()
        self._manager.set_rules(alerts_mod.load_rules())
        self._history: list[alerts_mod.AlertEvent] = []

        # Para snapshot de metricas (compartilha com Overview/Recursos)
        self._prev_cpu: backend.CpuTimes | None = None

        # ===== Header =====
        header_lbl = Gtk.Label(label="Alertas configuráveis")
        header_lbl.add_css_class("title-2")
        header_lbl.set_halign(Gtk.Align.START)
        header_lbl.set_margin_bottom(8)

        header_desc = Gtk.Label(
            label=(
                "Defina regras tipo \"CPU > 95% por 60s\" e receba "
                "<b>notificação desktop</b> quando disparar. Regras salvas em "
                "<tt>~/.config/vigia/dashboard-alerts.json</tt>.\n\n"
                "Cada regra tem <i>cooldown</i> para não spammar notificações "
                "do mesmo problema."
            )
        )
        header_desc.set_use_markup(True)
        header_desc.add_css_class("dim-label")
        header_desc.set_halign(Gtk.Align.START)
        header_desc.set_wrap(True)
        header_desc.set_xalign(0)
        header_desc.set_margin_bottom(24)

        # ===== Rules group =====
        self._rules_group = Adw.PreferencesGroup()
        self._rules_group.set_title("Regras")
        self._rules_group.set_description(
            "Toggle para ativar/desativar. Edite os parâmetros e salve para aplicar."
        )
        self._rule_rows: list = []

        # ===== Add button =====
        add_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_btn_box.set_halign(Gtk.Align.END)
        add_btn_box.set_margin_top(16)
        add_btn = Gtk.Button(label="Adicionar regra")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", lambda _b: self._show_add_dialog())
        add_btn_box.append(add_btn)

        # ===== History group =====
        self._history_group = Adw.PreferencesGroup()
        self._history_group.set_margin_top(28)
        self._history_group.set_title("Disparos recentes")
        self._history_group.set_description(
            "Últimos 20 alertas disparados nesta sessão (não persistido)."
        )
        self._history_rows: list = []

        # ===== Layout =====
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(header_lbl)
        inner.append(header_desc)
        inner.append(self._rules_group)
        inner.append(add_btn_box)
        inner.append(self._history_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        self.set_child(scrolled)

        # Render inicial
        self._render_rules()
        self._render_history()

        # Tick de avaliacao (coleta vai pra worker thread — ver _on_tick)
        self._collecting = False
        self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    # ============================================================
    # Snapshot de metricas atuais
    # ============================================================

    def _collect_metrics(self) -> dict[str, float]:
        """Coleta valores de todas as metricas suportadas em dict."""
        metrics: dict[str, float] = {}

        # CPU%
        cpu = backend.get_cpu_snapshot(self._prev_cpu)
        self._prev_cpu = cpu.times
        metrics["cpu_pct"] = cpu.total_pct

        if cpu.temp_c is not None:
            metrics["cpu_temp_c"] = cpu.temp_c

        # Memoria
        mem = backend.get_mem_snapshot()
        if mem.total_kb > 0:
            metrics["mem_pct"] = mem.used_kb / mem.total_kb * 100.0
        if mem.swap_total_kb > 0:
            metrics["swap_pct"] = mem.swap_used_kb / mem.swap_total_kb * 100.0

        # Load
        load1, _, _ = backend.get_load_avg()
        metrics["load_1"] = load1

        # Disco por mountpoint
        disk = backend.get_disk_snapshot(None)
        for m in disk.mounts:
            if m.total_bytes > 0:
                pct = m.used_bytes / m.total_bytes * 100.0
                if m.mountpoint == "/":
                    metrics["disk_pct_root"] = pct
                elif m.mountpoint == "/home":
                    metrics["disk_pct_home"] = pct

        return metrics

    # ============================================================
    # Tick de avaliacao
    # ============================================================

    def _on_tick(self) -> bool:
        # PERF: a coleta le /proc + /sys (2 globs) + os.statvfs por mountpoint —
        # statvfs pode BLOQUEAR em filesystem de rede. Como esta tab roda sempre
        # (monitor de background, nao pausa), tiramos a coleta do main loop pra
        # uma thread; a avaliacao/notificacao volta ao main loop.
        if self._collecting:
            return True  # coleta anterior ainda em andamento (fs lento)
        self._collecting = True
        threading.Thread(target=self._collect_worker, daemon=True).start()
        return True

    def _collect_worker(self) -> None:
        try:
            metrics = self._collect_metrics()
        except Exception:  # pylint: disable=broad-except
            metrics = None
        GLib.idle_add(self._process_metrics, metrics)

    def _process_metrics(self, metrics: dict | None) -> bool:
        self._collecting = False
        if metrics:
            try:
                for ev in self._manager.check(metrics):
                    self._on_alert_fired(ev)
            except Exception:  # pylint: disable=broad-except
                pass
        return False  # GLib.idle_add: nao repete

    def _on_alert_fired(self, event: alerts_mod.AlertEvent) -> None:
        """Dispara notificacao desktop nativa + adiciona ao historico."""
        op_label = ">" if event.op == "gt" else "<"
        # notif_id por regra: um novo disparo da mesma regra substitui o
        # banner anterior em vez de empilhar (evita spam no Shell).
        notify(
            f"Vigia: {event.rule_label}",
            f"{event.metric_label} {op_label} {event.threshold:.1f}\n"
            f"Valor atual: {event.current_value:.1f}",
            notif_id=f"vigia-alert-{event.rule_id}",
            priority=PRIORITY_HIGH,
        )

        # Historico (mantem ultimos 20)
        self._history.insert(0, event)
        self._history = self._history[:20]
        self._render_history()

    # ============================================================
    # Render rules
    # ============================================================

    def _render_rules(self) -> None:
        for r in self._rule_rows:
            self._rules_group.remove(r)
        self._rule_rows = []

        rules = self._manager.get_rules()
        if not rules:
            row = Adw.ActionRow(title="Nenhuma regra cadastrada")
            row.set_subtitle("Clique 'Adicionar regra' abaixo.")
            row.add_css_class("dim-label")
            self._rules_group.add(row)
            self._rule_rows.append(row)
            return

        for rule in rules:
            row = self._build_rule_row(rule)
            self._rules_group.add(row)
            self._rule_rows.append(row)

    def _build_rule_row(self, rule: alerts_mod.AlertRule) -> Adw.ExpanderRow:
        op_sym = ">" if rule.op == "gt" else "<"
        title = rule.label or alerts_mod.metric_label(rule.metric)
        subtitle = (
            f"{alerts_mod.metric_label(rule.metric)} {op_sym} "
            f"{rule.threshold:g} por {rule.duration_sec}s "
            f"(cooldown {rule.cooldown_sec}s)"
        )

        row = Adw.ExpanderRow()
        row.set_title(title)
        row.set_subtitle(subtitle)

        # Switch enabled/disabled (prefix)
        switch = Gtk.Switch()
        switch.set_active(rule.enabled)
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("notify::active",
                       lambda s, _ps, r=rule: self._on_toggle_enabled(r, s.get_active()))
        row.add_prefix(switch)

        # Details rows
        thr_row = Adw.ActionRow(title="Limiar")
        thr_row.add_css_class("property")
        thr_lbl = Gtk.Label(label=f"{op_sym} {rule.threshold:g}")
        thr_lbl.add_css_class("monospace")
        thr_row.add_suffix(thr_lbl)
        row.add_row(thr_row)

        dur_row = Adw.ActionRow(title="Duração mínima")
        dur_row.add_css_class("property")
        dur_row.set_subtitle("Tempo acima do limiar antes de disparar")
        dur_lbl = Gtk.Label(label=f"{rule.duration_sec}s")
        dur_lbl.add_css_class("monospace")
        dur_row.add_suffix(dur_lbl)
        row.add_row(dur_row)

        cd_row = Adw.ActionRow(title="Cooldown")
        cd_row.add_css_class("property")
        cd_row.set_subtitle("Min entre disparos consecutivos do mesmo alerta")
        cd_lbl = Gtk.Label(label=f"{rule.cooldown_sec}s")
        cd_lbl.add_css_class("monospace")
        cd_row.add_suffix(cd_lbl)
        row.add_row(cd_row)

        # Action buttons (edit, remove)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_halign(Gtk.Align.END)
        actions_box.set_margin_top(4)
        actions_box.set_margin_bottom(4)

        edit_btn = Gtk.Button(label="Editar")
        edit_btn.connect("clicked", lambda _b, r=rule: self._show_edit_dialog(r))
        actions_box.append(edit_btn)

        del_btn = Gtk.Button(label="Remover")
        del_btn.add_css_class("destructive-action")
        del_btn.connect("clicked", lambda _b, r=rule: self._confirm_remove(r))
        actions_box.append(del_btn)

        actions_row = Adw.ActionRow(title="Ações")
        actions_row.add_suffix(actions_box)
        row.add_row(actions_row)

        return row

    def _on_toggle_enabled(self, rule: alerts_mod.AlertRule, enabled: bool) -> None:
        """Toggle switch — atualiza rule e salva."""
        rule.enabled = enabled
        ok, err = alerts_mod.save_rules(self._manager.get_rules())
        if not ok:
            show_error(self, "Falha ao salvar", err)
        # Re-aplica regras no manager (para reset de state se desabilitada)
        self._manager.set_rules(self._manager.get_rules())

    # ============================================================
    # Add / Edit dialog
    # ============================================================

    def _show_add_dialog(self) -> None:
        self._show_rule_dialog(None)

    def _show_edit_dialog(self, rule: alerts_mod.AlertRule) -> None:
        self._show_rule_dialog(rule)

    def _show_rule_dialog(self, rule: alerts_mod.AlertRule | None) -> None:
        is_new = rule is None
        if is_new:
            rule = alerts_mod.AlertRule(
                id=alerts_mod.new_rule_id(),
                metric="cpu_pct",
                threshold=alerts_mod.METRICS["cpu_pct"]["default_threshold"],
                op="gt",
                duration_sec=30,
                cooldown_sec=300,
                label="",
                enabled=True,
            )

        dlg = Adw.AlertDialog(
            heading="Nova regra de alerta" if is_new else f"Editar: {rule.label or 'regra'}",
            body="Configure os parâmetros e clique 'Salvar'.",
        )

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_margin_top(12)

        # Nome
        body.append(Gtk.Label(label="Nome (opcional):", halign=Gtk.Align.START))
        name_entry = Gtk.Entry()
        name_entry.set_text(rule.label)
        name_entry.set_placeholder_text("ex: 'CPU sustentada alta'")
        body.append(name_entry)

        # Metric
        body.append(Gtk.Label(label="Métrica:", halign=Gtk.Align.START))
        metric_keys = list(alerts_mod.METRICS.keys())
        metric_labels = [alerts_mod.METRICS[k]["label"] for k in metric_keys]
        metric_combo = Gtk.DropDown.new_from_strings(metric_labels)
        try:
            metric_combo.set_selected(metric_keys.index(rule.metric))
        except ValueError:
            metric_combo.set_selected(0)
        body.append(metric_combo)

        # Operador
        body.append(Gtk.Label(label="Operador:", halign=Gtk.Align.START))
        op_combo = Gtk.DropDown.new_from_strings(["maior que (>)", "menor que (<)"])
        op_combo.set_selected(0 if rule.op == "gt" else 1)
        body.append(op_combo)

        # Threshold
        body.append(Gtk.Label(label="Limiar (threshold):", halign=Gtk.Align.START))
        thr_spin = Gtk.SpinButton.new_with_range(0, 150, 1)
        thr_spin.set_value(rule.threshold)
        thr_spin.set_digits(1)
        body.append(thr_spin)

        # Duration
        body.append(Gtk.Label(label="Duração mínima (segundos):", halign=Gtk.Align.START))
        dur_spin = Gtk.SpinButton.new_with_range(1, 3600, 1)
        dur_spin.set_value(rule.duration_sec)
        body.append(dur_spin)

        # Cooldown
        body.append(Gtk.Label(label="Cooldown (segundos):", halign=Gtk.Align.START))
        cd_spin = Gtk.SpinButton.new_with_range(0, 86400, 30)
        cd_spin.set_value(rule.cooldown_sec)
        body.append(cd_spin)

        dlg.set_extra_child(body)
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("save", "Salvar" if is_new else "Atualizar")
        dlg.set_default_response("save")
        dlg.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dlg.connect("response", self._on_dialog_response, rule, is_new,
                    name_entry, metric_combo, op_combo, thr_spin, dur_spin, cd_spin,
                    metric_keys)
        dlg.present(self.get_root())

    def _on_dialog_response(
        self, _dlg, response: str,
        rule: alerts_mod.AlertRule,
        is_new: bool,
        name_entry: Gtk.Entry,
        metric_combo: Gtk.DropDown,
        op_combo: Gtk.DropDown,
        thr_spin: Gtk.SpinButton,
        dur_spin: Gtk.SpinButton,
        cd_spin: Gtk.SpinButton,
        metric_keys: list[str],
    ) -> None:
        if response != "save":
            return

        rule.label = name_entry.get_text().strip()
        idx = metric_combo.get_selected()
        if 0 <= idx < len(metric_keys):
            rule.metric = metric_keys[idx]
        rule.op = "gt" if op_combo.get_selected() == 0 else "lt"
        rule.threshold = thr_spin.get_value()
        rule.duration_sec = int(dur_spin.get_value())
        rule.cooldown_sec = int(cd_spin.get_value())

        rules = self._manager.get_rules()
        if is_new:
            rules.append(rule)
        # Edit: rule ja esta na lista (e' a mesma referencia que veio do manager)

        ok, err = alerts_mod.save_rules(rules)
        if not ok:
            show_error(self, "Falha ao salvar", err)
            return

        self._manager.set_rules(rules)
        self._render_rules()

    # ============================================================
    # Remove
    # ============================================================

    def _confirm_remove(self, rule: alerts_mod.AlertRule) -> None:
        dlg = Adw.AlertDialog(
            heading=f"Remover '{rule.label or alerts_mod.metric_label(rule.metric)}'?",
            body="Esta ação não pode ser desfeita.",
        )
        dlg.add_response("cancel", "Cancelar")
        dlg.add_response("remove", "Remover")
        # UX consistency: default em Cancelar (Enter nao deve apagar)
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", self._on_remove_confirmed, rule)
        dlg.present(self.get_root())

    def _on_remove_confirmed(self, _dlg, response: str, rule: alerts_mod.AlertRule) -> None:
        if response != "remove":
            return
        rules = [r for r in self._manager.get_rules() if r.id != rule.id]
        ok, err = alerts_mod.save_rules(rules)
        if not ok:
            show_error(self, "Falha ao salvar", err)
            return
        self._manager.set_rules(rules)
        self._render_rules()

    # ============================================================
    # Render historico
    # ============================================================

    def _render_history(self) -> None:
        for r in self._history_rows:
            self._history_group.remove(r)
        self._history_rows = []

        if not self._history:
            row = Adw.ActionRow(title="Nenhum alerta disparado ainda")
            row.set_subtitle("Disparos aparecem aqui quando uma regra é ativada.")
            row.add_css_class("dim-label")
            self._history_group.add(row)
            self._history_rows.append(row)
            return

        for ev in self._history:
            op_sym = ">" if ev.op == "gt" else "<"
            time_str = datetime.fromtimestamp(ev.fired_at).strftime("%d/%m %H:%M:%S")

            row = Adw.ActionRow(title=ev.rule_label)
            row.set_subtitle(
                f"{time_str} · {ev.metric_label} {op_sym} {ev.threshold:g} "
                f"(atual: {ev.current_value:.1f})"
            )
            row.set_subtitle_lines(2)
            row.add_css_class("property")

            badge = Gtk.Label(label="!")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class("warning")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_prefix(badge)

            self._history_group.add(row)
            self._history_rows.append(row)
