"""Tab Visao Geral: KPI cards + sparklines de CPU, RAM, Rede."""

from __future__ import annotations


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from .. import COLOR_CPU, COLOR_NET, COLOR_RAM
from .. import backend
from ..graphs import Sparkline
from ._helpers import make_clamp


REFRESH_MS = 1000  # 1Hz


# Selo da plataforma no hero: pill verde (atomico) / azul (Workstation).
# Usa cores nomeadas do libadwaita (theme-aware, dark/light).
_PLATFORM_CSS = """
.vigia-platform-badge {
  border-radius: 999px;
  padding: 3px 14px;
  font-weight: bold;
  font-size: 0.85em;
}
.vigia-platform-atomic {
  background-color: @success_bg_color;
  color: @success_fg_color;
}
.vigia-platform-workstation {
  background-color: @accent_bg_color;
  color: @accent_fg_color;
}
"""

_CSS_LOADED = False


def _ensure_platform_css() -> None:
    """Carrega o CSS do selo uma unica vez no display padrao."""
    global _CSS_LOADED
    if _CSS_LOADED:
        return
    display = Gdk.Display.get_default()
    if display is None:  # headless / sem display
        return
    provider = Gtk.CssProvider()
    if hasattr(provider, "load_from_string"):  # GTK >= 4.12
        provider.load_from_string(_PLATFORM_CSS)
    else:  # pragma: no cover - GTK antigo
        provider.load_from_data(_PLATFORM_CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    _CSS_LOADED = True


class OverviewTab(Adw.Bin):
    """Hero + KPIs + sparklines em grid."""

    def __init__(self) -> None:
        super().__init__()
        self._prev_cpu: backend.CpuTimes | None = None
        self._prev_disk: backend.DiskIo | None = None
        self._prev_net: backend.NetIo | None = None
        self._tick_id: int = 0

        # ---- Hero ----
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        hero.set_halign(Gtk.Align.CENTER)
        hero.set_margin_top(28)
        hero.set_margin_bottom(8)

        self._hostname_lbl = Gtk.Label(label="—")
        self._hostname_lbl.add_css_class("title-1")
        self._hostname_lbl.set_halign(Gtk.Align.CENTER)
        hero.append(self._hostname_lbl)

        # Selo da plataforma (Silverblue vs Workstation). Identidade da
        # maquina fica no hostname acima; aqui a cor (verde=atomico /
        # azul=Workstation) deixa obvio qual sistema esta rodando. Estatico:
        # setado uma vez (a plataforma nao muda em runtime).
        _ensure_platform_css()
        self._platform_lbl = Gtk.Label(label="")
        self._platform_lbl.add_css_class("vigia-platform-badge")
        self._platform_lbl.set_halign(Gtk.Align.CENTER)
        self._platform_lbl.set_margin_top(2)
        plat_label, plat_atomic = backend.get_platform_label()
        self._platform_lbl.set_label(plat_label)
        self._platform_lbl.add_css_class(
            "vigia-platform-atomic" if plat_atomic else "vigia-platform-workstation"
        )
        hero.append(self._platform_lbl)

        self._sub_lbl = Gtk.Label(label="")
        self._sub_lbl.add_css_class("dim-label")
        self._sub_lbl.set_halign(Gtk.Align.CENTER)
        self._sub_lbl.set_max_width_chars(70)
        self._sub_lbl.set_wrap(True)
        self._sub_lbl.set_justify(Gtk.Justification.CENTER)
        hero.append(self._sub_lbl)

        # ---- Load average row (3 KPI cards lado a lado) ----
        load_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        load_box.set_halign(Gtk.Align.CENTER)
        load_box.set_margin_top(8)
        load_box.set_margin_bottom(8)
        self._load_cards = []
        for label in ("1 min", "5 min", "15 min"):
            card = self._build_kpi_card(label, "—")
            load_box.append(card["widget"])
            self._load_cards.append(card)

        # ---- Sparklines grid (CPU + RAM + Rede + Disco) ----
        # Cada card: titulo curto + valor atual grande + sparkline
        sparks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        sparks_box.set_margin_top(20)

        self._cpu_card = self._build_spark_card("CPU", COLOR_CPU, "%.0f%%")
        sparks_box.append(self._cpu_card["widget"])

        self._ram_card = self._build_spark_card("Memória", COLOR_RAM, "%.0f%%")
        sparks_box.append(self._ram_card["widget"])

        # Rede: RX + TX em sparklines paralelas
        self._net_rx_card = self._build_spark_card("Rede ↓ (download)", COLOR_NET, "%s")
        sparks_box.append(self._net_rx_card["widget"])

        self._net_tx_card = self._build_spark_card("Rede ↑ (upload)", COLOR_NET, "%s")
        sparks_box.append(self._net_tx_card["widget"])

        # ---- Disco (barras simples por mountpoint) ----
        self._disk_group = Adw.PreferencesGroup()
        self._disk_group.set_margin_top(28)
        self._disk_group.set_title("Disco")
        self._disk_rows: list = []

        # ---- Top processos (resumo) ----
        self._top_group = Adw.PreferencesGroup()
        self._top_group.set_margin_top(28)
        self._top_group.set_title("Top processos")
        self._top_group.set_description("Top 3 por CPU + top 3 por memória")
        self._top_rows: list = []

        # ---- Layout ----
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.set_margin_top(0)
        inner.set_margin_bottom(32)
        inner.set_margin_start(28)
        inner.set_margin_end(28)
        inner.append(hero)
        inner.append(load_box)
        inner.append(sparks_box)
        inner.append(self._disk_group)
        inner.append(self._top_group)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(make_clamp(inner))
        self.set_child(scrolled)

        # ---- Start refresh tick ----
        self._on_tick()  # primeira leitura
        self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)

        # Para ao destruir
        self.connect("destroy", self._on_destroy)

    # ============================================================
    # Pause/resume API (chamada por window.py quando tab muda)
    # ============================================================

    def pause_tick(self) -> None:
        """Para o GLib.timeout — usado quando tab fica invisivel."""
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def resume_tick(self) -> None:
        """Reinicia o timeout (se nao estava ativo)."""
        if self._tick_id == 0:
            self._on_tick()  # leitura imediata
            self._tick_id = GLib.timeout_add(REFRESH_MS, self._on_tick)

    # ============================================================
    # Card builders
    # ============================================================

    def _build_kpi_card(self, label: str, default_value: str) -> dict:
        """Card pequeno com valor numerico grande + label embaixo."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        card.add_css_class("card")
        card.set_size_request(120, 64)
        card.set_margin_top(0)

        val_lbl = Gtk.Label(label=default_value)
        val_lbl.add_css_class("title-2")
        val_lbl.set_halign(Gtk.Align.CENTER)
        val_lbl.set_margin_top(8)
        card.append(val_lbl)

        lbl = Gtk.Label(label=label)
        lbl.add_css_class("caption")
        lbl.add_css_class("dim-label")
        lbl.set_halign(Gtk.Align.CENTER)
        lbl.set_margin_bottom(6)
        card.append(lbl)

        return {"widget": card, "val": val_lbl, "label": lbl}

    def _build_spark_card(
        self, title: str, color: tuple[float, float, float], val_fmt: str
    ) -> dict:
        """Card grande com titulo + valor atual + sparkline."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("card")

        # Header (titulo + valor atual à direita)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(2)
        header.set_margin_start(14)
        header.set_margin_end(14)

        title_lbl = Gtk.Label(label=title)
        title_lbl.add_css_class("caption-heading")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_hexpand(True)
        title_lbl.set_xalign(0)
        header.append(title_lbl)

        val_lbl = Gtk.Label(label="—")
        val_lbl.add_css_class("title-3")
        val_lbl.add_css_class("monospace")
        val_lbl.set_halign(Gtk.Align.END)
        header.append(val_lbl)

        card.append(header)

        # Sparkline
        spark = Sparkline(color=color, history_size=60, max_y=None, min_height=42)
        spark.set_margin_start(14)
        spark.set_margin_end(14)
        spark.set_margin_top(2)
        spark.set_margin_bottom(10)
        card.append(spark)

        return {"widget": card, "val": val_lbl, "spark": spark, "val_fmt": val_fmt}

    # ============================================================
    # Refresh tick
    # ============================================================

    def _on_destroy(self, *_args) -> None:
        if self._tick_id:
            GLib.source_remove(self._tick_id)
            self._tick_id = 0

    def _on_tick(self) -> bool:
        # Hero / system info
        info = backend.get_system_info()
        self._hostname_lbl.set_label(info.hostname)
        # Tira o '(Silverblue)' do PRETTY_NAME — a variante ja' esta no selo.
        distro_short = info.distro.split(" (")[0].strip()
        self._sub_lbl.set_label(
            f"{distro_short} · kernel {info.kernel} · "
            f"uptime {backend.format_uptime(info.uptime_sec)} · "
            f"{info.n_cpus} CPU{'s' if info.n_cpus > 1 else ''}"
        )

        # Load avg
        load1, load5, load15 = backend.get_load_avg()
        loads = (load1, load5, load15)
        for card, value in zip(self._load_cards, loads):
            card["val"].set_label(f"{value:.2f}")
            for cls in ("success", "warning", "error"):
                card["val"].remove_css_class(cls)
            # cor baseada em load vs n_cpus
            ratio = value / max(1, info.n_cpus)
            if ratio < 0.7:
                card["val"].add_css_class("success")
            elif ratio < 1.5:
                card["val"].add_css_class("warning")
            else:
                card["val"].add_css_class("error")

        # CPU
        cpu = backend.get_cpu_snapshot(self._prev_cpu)
        self._prev_cpu = cpu.times
        self._cpu_card["val"].set_label(f"{cpu.total_pct:.0f}%")
        self._cpu_card["spark"].push(cpu.total_pct)

        # RAM
        mem = backend.get_mem_snapshot()
        if mem.total_kb > 0:
            mem_pct = mem.used_kb / mem.total_kb * 100.0
            self._ram_card["val"].set_label(f"{mem_pct:.0f}%")
            self._ram_card["spark"].push(mem_pct)

        # Net
        net = backend.get_net_snapshot(self._prev_net)
        self._prev_net = net.io
        if net.rates:
            # Agrega todas as interfaces (RX + TX)
            total_rx = sum(rx for rx, _ in net.rates.values())
            total_tx = sum(tx for _, tx in net.rates.values())
        else:
            total_rx = 0.0
            total_tx = 0.0
        self._net_rx_card["val"].set_label(backend.format_mbps(total_rx))
        self._net_rx_card["spark"].push(total_rx)
        self._net_tx_card["val"].set_label(backend.format_mbps(total_tx))
        self._net_tx_card["spark"].push(total_tx)

        # Disco — uso por mountpoint
        disk = backend.get_disk_snapshot(self._prev_disk)
        self._prev_disk = disk.io
        self._render_disks(disk.mounts)

        # Top processos
        # PERF: Overview so usa cpu_pct e rss_kb. Pular conexoes e I/O
        # economiza ~1500 syscalls/seg (sem readlinks em /proc/<pid>/fd/*
        # nem leitura de /proc/<pid>/io nem parse de /proc/net/*).
        procs = backend.list_processes(include_connections=False, include_io=False)
        self._render_top(procs)

        return True  # continua o timeout

    def _render_disks(self, mounts: list[backend.DiskUsage]) -> None:
        for r in self._disk_rows:
            self._disk_group.remove(r)
        self._disk_rows = []

        if not mounts:
            row = Adw.ActionRow(title="Nenhum mountpoint detectado")
            row.add_css_class("dim-label")
            self._disk_group.add(row)
            self._disk_rows.append(row)
            return

        # Limita a top 4 mountpoints por tamanho
        mounts_sorted = sorted(mounts, key=lambda m: m.total_bytes, reverse=True)[:4]

        for m in mounts_sorted:
            pct = (m.used_bytes / m.total_bytes * 100.0) if m.total_bytes else 0.0
            row = Adw.ActionRow(title=m.mountpoint)
            row.set_subtitle(
                f"{backend.format_bytes(m.used_bytes)} usado de "
                f"{backend.format_bytes(m.total_bytes)} · "
                f"{m.fstype}"
            )
            row.set_subtitle_lines(2)
            row.add_css_class("property")

            badge = Gtk.Label(label=f"{pct:.0f}%")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            if pct > 90:
                badge.add_css_class("error")
            elif pct > 75:
                badge.add_css_class("warning")
            else:
                badge.add_css_class("success")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)

            self._disk_group.add(row)
            self._disk_rows.append(row)

    def _render_top(self, procs: list[backend.ProcessInfo]) -> None:
        for r in self._top_rows:
            self._top_group.remove(r)
        self._top_rows = []

        if not procs:
            row = Adw.ActionRow(title="Sem processos")
            row.add_css_class("dim-label")
            self._top_group.add(row)
            self._top_rows.append(row)
            return

        # Top 3 CPU
        top_cpu = sorted(procs, key=lambda p: p.cpu_pct, reverse=True)[:3]
        for p in top_cpu:
            if p.cpu_pct < 0.1:
                continue
            row = Adw.ActionRow(title=p.comm)
            row.set_subtitle(f"PID {p.pid} · {p.user}")
            row.add_css_class("property")
            badge = Gtk.Label(label=f"{p.cpu_pct:.1f}% CPU")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.add_css_class("success" if p.cpu_pct < 50 else "warning")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)
            self._top_group.add(row)
            self._top_rows.append(row)

        # Top 3 MEM
        top_mem = sorted(procs, key=lambda p: p.rss_kb, reverse=True)[:3]
        for p in top_mem:
            if p.rss_kb < 1024:
                continue
            row = Adw.ActionRow(title=p.comm)
            row.set_subtitle(f"PID {p.pid} · {p.user}")
            row.add_css_class("property")
            badge = Gtk.Label(label=f"{backend.format_kb(p.rss_kb)}")
            badge.add_css_class("monospace")
            badge.add_css_class("caption-heading")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)
            self._top_group.add(row)
            self._top_rows.append(row)
