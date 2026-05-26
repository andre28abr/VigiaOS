"""Tab Recursos: graficos detalhados de CPU, RAM, Disco, Rede."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .. import COLOR_CPU, COLOR_DISK, COLOR_NET, COLOR_RAM
from .. import backend
from ..graphs import LineChart, StackedBar
from ._helpers import make_clamp


REFRESH_MS = 1000


class ResourcesTab(Adw.Bin):
    """4 graficos: CPU (per-core), Memoria (stacked), Disco I/O, Rede."""

    def __init__(self) -> None:
        super().__init__()
        self._prev_cpu: backend.CpuTimes | None = None
        self._prev_disk: backend.DiskIo | None = None
        self._prev_net: backend.NetIo | None = None
        self._tick_id: int = 0
        self._cpu_chart_series_set = False

        # ============================================================
        # CPU group
        # ============================================================
        cpu_group = Adw.PreferencesGroup()
        cpu_group.set_title("CPU")
        cpu_group.set_description("Uso por core, frequencia, temperatura")

        # Chart container
        self._cpu_chart = LineChart(
            history_size=60,
            max_y=100.0,
            y_label_fmt="{:.0f}%",
            min_height=160,
        )
        cpu_chart_row = Adw.PreferencesRow()
        cpu_chart_row.set_activatable(False)
        cpu_chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        cpu_chart_box.set_margin_top(8)
        cpu_chart_box.set_margin_bottom(8)
        cpu_chart_box.append(self._cpu_chart)
        cpu_chart_row.set_child(cpu_chart_box)
        cpu_group.add(cpu_chart_row)

        # CPU info rows
        self._cpu_freq_row = Adw.ActionRow(title="Frequencia atual")
        self._cpu_freq_row.add_css_class("property")
        self._cpu_freq_lbl = Gtk.Label(label="—")
        self._cpu_freq_lbl.add_css_class("monospace")
        self._cpu_freq_row.add_suffix(self._cpu_freq_lbl)
        cpu_group.add(self._cpu_freq_row)

        self._cpu_temp_row = Adw.ActionRow(title="Temperatura")
        self._cpu_temp_row.add_css_class("property")
        self._cpu_temp_row.set_subtitle("Maximum entre todos os sensores")
        self._cpu_temp_lbl = Gtk.Label(label="—")
        self._cpu_temp_lbl.add_css_class("monospace")
        self._cpu_temp_row.add_suffix(self._cpu_temp_lbl)
        cpu_group.add(self._cpu_temp_row)

        # ============================================================
        # Memory group
        # ============================================================
        mem_group = Adw.PreferencesGroup()
        mem_group.set_margin_top(28)
        mem_group.set_title("Memoria")
        mem_group.set_description("RAM e swap")

        # Stacked bar
        self._mem_bar = StackedBar(min_height=24)
        mem_bar_row = Adw.PreferencesRow()
        mem_bar_row.set_activatable(False)
        mem_bar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        mem_bar_box.set_margin_top(12)
        mem_bar_box.set_margin_bottom(6)
        mem_bar_box.set_margin_start(8)
        mem_bar_box.set_margin_end(8)
        mem_bar_box.append(self._mem_bar)
        mem_bar_row.set_child(mem_bar_box)
        mem_group.add(mem_bar_row)

        # RAM rows
        self._mem_total_row = Adw.ActionRow(title="Total")
        self._mem_total_row.add_css_class("property")
        self._mem_total_lbl = Gtk.Label(label="—")
        self._mem_total_lbl.add_css_class("monospace")
        self._mem_total_row.add_suffix(self._mem_total_lbl)
        mem_group.add(self._mem_total_row)

        self._mem_used_row = Adw.ActionRow(title="Em uso")
        self._mem_used_row.add_css_class("property")
        self._mem_used_lbl = Gtk.Label(label="—")
        self._mem_used_lbl.add_css_class("monospace")
        self._mem_used_row.add_suffix(self._mem_used_lbl)
        mem_group.add(self._mem_used_row)

        self._mem_cache_row = Adw.ActionRow(title="Cache + buffers")
        self._mem_cache_row.add_css_class("property")
        self._mem_cache_row.set_subtitle("Memoria liberavel pelo kernel se necessario")
        self._mem_cache_lbl = Gtk.Label(label="—")
        self._mem_cache_lbl.add_css_class("monospace")
        self._mem_cache_row.add_suffix(self._mem_cache_lbl)
        mem_group.add(self._mem_cache_row)

        self._mem_swap_row = Adw.ActionRow(title="Swap")
        self._mem_swap_row.add_css_class("property")
        self._mem_swap_lbl = Gtk.Label(label="—")
        self._mem_swap_lbl.add_css_class("monospace")
        self._mem_swap_row.add_suffix(self._mem_swap_lbl)
        mem_group.add(self._mem_swap_row)

        # ============================================================
        # Disk I/O
        # ============================================================
        disk_group = Adw.PreferencesGroup()
        disk_group.set_margin_top(28)
        disk_group.set_title("Disco — I/O")
        disk_group.set_description("Leitura e escrita por device em tempo real")

        self._disk_chart = LineChart(
            history_size=60,
            max_y=None,
            y_label_fmt="{:.1f} MB/s",
            min_height=160,
        )
        self._disk_chart.set_series([
            ("Read", COLOR_DISK),
            ("Write", (1.0, 0.42, 0.42)),  # red para diferenciar
        ])
        disk_chart_row = Adw.PreferencesRow()
        disk_chart_row.set_activatable(False)
        disk_chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        disk_chart_box.set_margin_top(8)
        disk_chart_box.set_margin_bottom(8)
        disk_chart_box.append(self._disk_chart)
        disk_chart_row.set_child(disk_chart_box)
        disk_group.add(disk_chart_row)

        self._disk_devices_lbl = Gtk.Label(label="—")
        self._disk_devices_lbl.add_css_class("dim-label")
        self._disk_devices_lbl.add_css_class("caption")
        self._disk_devices_lbl.set_halign(Gtk.Align.START)
        self._disk_devices_lbl.set_wrap(True)
        self._disk_devices_lbl.set_xalign(0)
        disk_devices_row = Adw.ActionRow(title="Devices monitorados")
        disk_devices_row.add_suffix(self._disk_devices_lbl)
        disk_group.add(disk_devices_row)

        # ============================================================
        # Network
        # ============================================================
        net_group = Adw.PreferencesGroup()
        net_group.set_margin_top(28)
        net_group.set_title("Rede")
        net_group.set_description("Download e upload por interface (agregado)")

        self._net_chart = LineChart(
            history_size=60,
            max_y=None,
            y_label_fmt="{:.2f} MB/s",
            min_height=160,
        )
        self._net_chart.set_series([
            ("↓ RX", COLOR_NET),
            ("↑ TX", (0.20, 0.83, 0.60)),  # emerald
        ])
        net_chart_row = Adw.PreferencesRow()
        net_chart_row.set_activatable(False)
        net_chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        net_chart_box.set_margin_top(8)
        net_chart_box.set_margin_bottom(8)
        net_chart_box.append(self._net_chart)
        net_chart_row.set_child(net_chart_box)
        net_group.add(net_chart_row)

        self._net_ifaces_group = Adw.PreferencesGroup()
        self._net_ifaces_group.set_margin_top(12)
        self._net_ifaces_rows: list = []

        # ============================================================
        # Layout
        # ============================================================
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(24)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(cpu_group)
        inner.append(mem_group)
        inner.append(disk_group)
        inner.append(net_group)
        inner.append(self._net_ifaces_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        self.set_child(scrolled)

        # Start
        self._on_tick()
        self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *_args) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    # PERF: pause/resume usado por window.py quando tab muda
    def pause_tick(self) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def resume_tick(self) -> None:
        if self._tick_id == 0:
            self._on_tick()
            self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)

    # ============================================================
    # Refresh
    # ============================================================

    def _on_tick(self) -> bool:
        cpu = backend.get_cpu_snapshot(self._prev_cpu)
        self._prev_cpu = cpu.times
        self._render_cpu(cpu)

        mem = backend.get_mem_snapshot()
        self._render_mem(mem)

        disk = backend.get_disk_snapshot(self._prev_disk)
        self._prev_disk = disk.io
        self._render_disk(disk)

        net = backend.get_net_snapshot(self._prev_net)
        self._prev_net = net.io
        self._render_net(net)

        return True

    def _render_cpu(self, cpu: backend.CpuSnapshot) -> None:
        n_cores = len(cpu.per_core_pct) - 1  # primeiro e' total agregado
        if n_cores <= 0:
            return

        # Inicializa series do chart se ainda nao foi
        if not self._cpu_chart_series_set:
            series_defs = []
            for i in range(n_cores):
                # Gradient emerald → ciano por core
                t = i / max(1, n_cores - 1) if n_cores > 1 else 0.5
                r = 0.20 + (0.13 - 0.20) * t   # emerald → ciano
                g = 0.83 + (0.83 - 0.83) * t
                b = 0.60 + (0.93 - 0.60) * t
                series_defs.append((f"Core {i}", (r, g, b)))
            self._cpu_chart.set_series(series_defs)
            self._cpu_chart_series_set = True

        # Push valores
        self._cpu_chart.push(*cpu.per_core_pct[1:])

        # Frequencia — esconde row se nao disponivel (VM tipicamente)
        if cpu.freq_mhz > 0:
            self._cpu_freq_row.set_visible(True)
            if cpu.freq_mhz >= 1000:
                self._cpu_freq_lbl.set_label(f"{cpu.freq_mhz / 1000:.2f} GHz")
            else:
                self._cpu_freq_lbl.set_label(f"{cpu.freq_mhz:.0f} MHz")
        else:
            # Sem cpufreq exposto (comum em VM) — esconde a row inteira
            self._cpu_freq_row.set_visible(False)

        # Temperatura — esconde row se nenhum sensor encontrado
        if cpu.temp_c is None:
            self._cpu_temp_row.set_visible(False)
        else:
            self._cpu_temp_row.set_visible(True)
            for cls in ("success", "warning", "error", "dim-label"):
                self._cpu_temp_lbl.remove_css_class(cls)
            self._cpu_temp_lbl.set_label(f"{cpu.temp_c:.0f} °C")
            if cpu.temp_c > 85:
                self._cpu_temp_lbl.add_css_class("error")
            elif cpu.temp_c > 70:
                self._cpu_temp_lbl.add_css_class("warning")
            else:
                self._cpu_temp_lbl.add_css_class("success")

    def _render_mem(self, mem: backend.MemSnapshot) -> None:
        if mem.total_kb <= 0:
            return

        used_frac = mem.used_kb / mem.total_kb
        cache_frac = mem.cached_kb / mem.total_kb
        # free = resto
        free_frac = max(0.0, 1.0 - used_frac - cache_frac)

        # Cores das 3 secoes — ajustadas pra contraste melhor contra o
        # background (#18181b ≈ 0.094 rgb). O segmento "free" antes era
        # 0.18/0.18/0.20 — quase invisivel. Agora 0.32/0.32/0.36 (zinc-600).
        self._mem_bar.set_segments([
            (COLOR_RAM, used_frac),
            ((0.30, 0.55, 0.40), cache_frac),  # verde mais claro para cache
            ((0.32, 0.32, 0.36), free_frac),    # cinza claro (zinc-600) para free
        ])

        self._mem_total_lbl.set_label(backend.format_kb(mem.total_kb))
        self._mem_used_lbl.set_label(
            f"{backend.format_kb(mem.used_kb)} ({used_frac * 100:.0f}%)"
        )
        self._mem_cache_lbl.set_label(
            f"{backend.format_kb(mem.cached_kb + mem.buffers_kb)} "
            f"({(cache_frac + mem.buffers_kb / mem.total_kb) * 100:.0f}%)"
        )

        for cls in ("success", "warning", "error"):
            self._mem_used_lbl.remove_css_class(cls)
        if used_frac > 0.90:
            self._mem_used_lbl.add_css_class("error")
        elif used_frac > 0.75:
            self._mem_used_lbl.add_css_class("warning")
        else:
            self._mem_used_lbl.add_css_class("success")

        if mem.swap_total_kb > 0:
            swap_frac = mem.swap_used_kb / mem.swap_total_kb
            self._mem_swap_lbl.set_label(
                f"{backend.format_kb(mem.swap_used_kb)} / "
                f"{backend.format_kb(mem.swap_total_kb)} "
                f"({swap_frac * 100:.0f}%)"
            )
        else:
            self._mem_swap_lbl.set_label("nenhum swap configurado")

    def _render_disk(self, disk: backend.DiskSnapshot) -> None:
        # Agrega total de I/O
        if disk.rates:
            total_read = sum(r for r, _ in disk.rates.values())
            total_write = sum(w for _, w in disk.rates.values())
        else:
            total_read = 0.0
            total_write = 0.0

        self._disk_chart.push(total_read, total_write)

        if disk.io.devices:
            devs = ", ".join(sorted(disk.io.devices.keys()))
            self._disk_devices_lbl.set_label(devs)

    def _render_net(self, net: backend.NetSnapshot) -> None:
        if net.rates:
            total_rx = sum(rx for rx, _ in net.rates.values())
            total_tx = sum(tx for _, tx in net.rates.values())
        else:
            total_rx = 0.0
            total_tx = 0.0

        self._net_chart.push(total_rx, total_tx)

        # Rows por interface
        for r in self._net_ifaces_rows:
            self._net_ifaces_group.remove(r)
        self._net_ifaces_rows = []

        if not net.io.ifaces:
            row = Adw.ActionRow(title="Nenhuma interface detectada")
            row.add_css_class("dim-label")
            self._net_ifaces_group.add(row)
            self._net_ifaces_rows.append(row)
            return

        for iface in sorted(net.io.ifaces.keys()):
            rx, tx = net.rates.get(iface, (0.0, 0.0))
            row = Adw.ActionRow(title=iface)
            row.set_subtitle(
                f"↓ {backend.format_mbps(rx)} · ↑ {backend.format_mbps(tx)}"
            )
            row.add_css_class("property")
            self._net_ifaces_group.add(row)
            self._net_ifaces_rows.append(row)
