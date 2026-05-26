"""Widgets de grafico via Cairo + Gtk.DrawingArea.

3 tipos:
- Sparkline: mini grafico de linha para Visao Geral (200x40)
- LineChart: grafico de linha com escala (400x140) — usado em Recursos
- StackedBar: barra horizontal segmentada (RAM com cache/used/free)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk  # noqa: E402


@dataclass
class Series:
    """Uma serie de dados (CPU%, RAM%, etc) com cor."""
    name: str
    color: tuple[float, float, float]    # RGB 0-1
    values: deque                          # deque com floats (recente no fim)


class Sparkline(Gtk.DrawingArea):
    """Mini grafico de linha. Mostra uma serie em ~60 pontos.

    Range Y: fixo (0-100) ou auto-scale via max_y=None.
    """

    def __init__(
        self,
        color: tuple[float, float, float],
        history_size: int = 60,
        max_y: float | None = 100.0,
        min_height: int = 36,
    ) -> None:
        super().__init__()
        self._color = color
        self._values: deque = deque(maxlen=history_size)
        self._max_y_fixed = max_y
        self._max_y_auto = 1.0
        self.set_content_height(min_height)
        self.set_hexpand(True)
        self.set_draw_func(self._on_draw)

    def push(self, value: float) -> None:
        """Adiciona valor; queue_draw apenas se mudou (PERF — evita redraw idle)."""
        new_val = max(0.0, value)
        # Se buffer cheio E ultimo valor identico (epsilon 0.005), skip redraw.
        # Em sistema idle, CPU% oscila 0.0→0.0 — redraw redundante.
        last = self._values[-1] if self._values else None
        self._values.append(new_val)
        if self._max_y_fixed is None and self._values:
            self._max_y_auto = max(self._max_y_auto * 0.9, max(self._values))
        if last is not None and abs(last - new_val) < 0.005:
            # Mesma posicao + scroll do buffer eh imperceptivel — skip.
            return
        self.queue_draw()

    def reset(self) -> None:
        self._values.clear()
        self.queue_draw()

    def _on_draw(self, _area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        # Fundo: transparente. Linha guia inferior sutil.
        cr.set_source_rgba(0.55, 0.55, 0.58, 0.18)
        cr.set_line_width(1)
        cr.move_to(0, height - 0.5)
        cr.line_to(width, height - 0.5)
        cr.stroke()

        if not self._values:
            return

        max_y = self._max_y_fixed or self._max_y_auto or 1.0
        if max_y <= 0:
            max_y = 1.0

        n = len(self._values)
        if n < 2:
            return

        # Calcula pontos
        margin = 2
        usable_w = width - 2 * margin
        usable_h = height - 2 * margin
        step_x = usable_w / max(1, self._values.maxlen - 1)
        start_x = width - margin - (n - 1) * step_x

        # Path da linha
        points = []
        for i, v in enumerate(self._values):
            x = start_x + i * step_x
            y = height - margin - (v / max_y) * usable_h
            points.append((x, y))

        # Area de baixo (fill claro)
        r, g, b = self._color
        cr.set_source_rgba(r, g, b, 0.18)
        cr.move_to(points[0][0], height - margin)
        for x, y in points:
            cr.line_to(x, y)
        cr.line_to(points[-1][0], height - margin)
        cr.close_path()
        cr.fill()

        # Linha
        cr.set_source_rgba(r, g, b, 0.95)
        cr.set_line_width(1.8)
        cr.set_line_join(2)  # round
        cr.move_to(points[0][0], points[0][1])
        for x, y in points[1:]:
            cr.line_to(x, y)
        cr.stroke()

        # Ponto final destacado
        last_x, last_y = points[-1]
        cr.set_source_rgba(r, g, b, 1.0)
        cr.arc(last_x, last_y, 2.5, 0, 6.2832)
        cr.fill()


class LineChart(Gtk.DrawingArea):
    """Grafico de linha multi-serie com eixo Y.

    Cada serie tem cor propria. Auto-scale baseado em max de todas.
    """

    def __init__(
        self,
        history_size: int = 60,
        max_y: float | None = None,
        y_label_fmt: str = "{:.0f}",
        min_height: int = 140,
    ) -> None:
        super().__init__()
        self._series: list[Series] = []
        self._history_size = history_size
        self._max_y_fixed = max_y
        self._max_y_auto = 1.0
        self._y_label_fmt = y_label_fmt
        self.set_content_height(min_height)
        self.set_hexpand(True)
        self.set_draw_func(self._on_draw)

    def set_series(self, series_defs: list[tuple[str, tuple[float, float, float]]]) -> None:
        """Recria series. Limpa historico se mudar."""
        self._series = [
            Series(name=name, color=color, values=deque(maxlen=self._history_size))
            for name, color in series_defs
        ]
        self.queue_draw()

    def push(self, *values: float) -> None:
        """Push 1 valor por serie. Numero de args == numero de series."""
        if len(values) != len(self._series):
            return
        for s, v in zip(self._series, values):
            s.values.append(max(0.0, v))

        if self._max_y_fixed is None:
            current_max = max(
                (max(s.values) if s.values else 0.0) for s in self._series
            )
            # Suaviza decay
            self._max_y_auto = max(self._max_y_auto * 0.92, current_max, 0.001)

        self.queue_draw()

    def _on_draw(self, _area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        # Padding interno
        pad_l = 48
        pad_r = 12
        pad_t = 12
        pad_b = 22

        chart_w = width - pad_l - pad_r
        chart_h = height - pad_t - pad_b
        if chart_w <= 0 or chart_h <= 0:
            return

        # Background
        cr.set_source_rgba(0.09, 0.09, 0.11, 0.0)  # transparent
        cr.paint()

        # Determinar max Y
        max_y = self._max_y_fixed if self._max_y_fixed is not None else self._max_y_auto
        if max_y <= 0:
            max_y = 1.0

        # Grid horizontal (4 linhas)
        cr.set_source_rgba(0.4, 0.4, 0.43, 0.25)
        cr.set_line_width(1)
        for i in range(5):
            y = pad_t + chart_h * i / 4
            cr.move_to(pad_l, y)
            cr.line_to(pad_l + chart_w, y)
            cr.stroke()

        # Labels Y
        cr.set_source_rgba(0.6, 0.6, 0.62, 0.85)
        cr.select_font_face("monospace")
        cr.set_font_size(9)
        for i in range(5):
            y_val = max_y * (1 - i / 4)
            y_px = pad_t + chart_h * i / 4
            label = self._y_label_fmt.format(y_val)
            extents = cr.text_extents(label)
            cr.move_to(pad_l - extents.width - 6, y_px + extents.height / 2 - 1)
            cr.show_text(label)

        if not self._series:
            return

        # Plot cada serie
        for s in self._series:
            if not s.values or len(s.values) < 2:
                continue
            n = len(s.values)
            step_x = chart_w / max(1, self._history_size - 1)
            start_x = pad_l + chart_w - (n - 1) * step_x

            points = []
            for i, v in enumerate(s.values):
                x = start_x + i * step_x
                y = pad_t + chart_h - (v / max_y) * chart_h
                points.append((x, y))

            r, g, b = s.color

            # Area de baixo
            cr.set_source_rgba(r, g, b, 0.12)
            cr.move_to(points[0][0], pad_t + chart_h)
            for x, y in points:
                cr.line_to(x, y)
            cr.line_to(points[-1][0], pad_t + chart_h)
            cr.close_path()
            cr.fill()

            # Linha
            cr.set_source_rgba(r, g, b, 0.95)
            cr.set_line_width(1.8)
            cr.move_to(points[0][0], points[0][1])
            for x, y in points[1:]:
                cr.line_to(x, y)
            cr.stroke()

            # Ponto final
            cr.set_source_rgba(r, g, b, 1.0)
            cr.arc(points[-1][0], points[-1][1], 2.5, 0, 6.2832)
            cr.fill()

        # Legenda (top-right)
        if len(self._series) > 1:
            cr.set_font_size(10)
            x = pad_l + chart_w
            y = pad_t + 4
            for s in reversed(self._series):
                if not s.values:
                    continue
                last = s.values[-1]
                label = f"{s.name}: {self._y_label_fmt.format(last)}"
                extents = cr.text_extents(label)
                x_label = x - extents.width - 14
                # Bola colorida
                r, g, b = s.color
                cr.set_source_rgba(r, g, b, 1.0)
                cr.arc(x_label - 8, y + 4, 3, 0, 6.2832)
                cr.fill()
                # Texto
                cr.set_source_rgba(0.85, 0.85, 0.87, 0.9)
                cr.move_to(x_label, y + 8)
                cr.show_text(label)
                y += 14


class StackedBar(Gtk.DrawingArea):
    """Barra horizontal segmentada para mostrar uso de RAM (used/cache/free)."""

    def __init__(self, min_height: int = 24) -> None:
        super().__init__()
        # Lista de (color, fraction). Fractions devem somar ~1.0.
        self._segments: list[tuple[tuple[float, float, float], float]] = []
        self.set_content_height(min_height)
        self.set_hexpand(True)
        self.set_draw_func(self._on_draw)

    def set_segments(
        self, segments: list[tuple[tuple[float, float, float], float]]
    ) -> None:
        self._segments = segments
        self.queue_draw()

    def _on_draw(self, _area: Gtk.DrawingArea, cr, width: int, height: int) -> None:
        # Background
        cr.set_source_rgba(0.18, 0.18, 0.20, 1.0)
        radius = min(8, height / 2)
        _rounded_rect(cr, 0, 0, width, height, radius)
        cr.fill()

        if not self._segments:
            return

        # Soma fracoes para normalizar (caso nao some 1.0)
        total_frac = sum(f for _, f in self._segments if f > 0) or 1.0

        # Pinta segmentos
        x = 0.0
        for color, frac in self._segments:
            if frac <= 0:
                continue
            r, g, b = color
            seg_w = (frac / total_frac) * width
            cr.set_source_rgba(r, g, b, 0.85)
            # No primeiro segmento, mantem borda arredondada esquerda
            # No ultimo segmento que ocupa tudo, arredonda direita
            _rounded_rect(cr, x, 0, seg_w, height, radius)
            cr.fill()
            x += seg_w


def _rounded_rect(cr, x: float, y: float, w: float, h: float, r: float) -> None:
    """Path de retangulo arredondado."""
    if r > h / 2:
        r = h / 2
    if r > w / 2:
        r = w / 2
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()
