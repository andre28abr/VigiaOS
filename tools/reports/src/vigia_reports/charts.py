"""Gráficos SVG nativos para os relatórios — sem JS, sem deps, sem rede.

Cada função recebe dados simples (list de tuplas) e devolve uma string
`<svg>…</svg>` pronta pra embutir no template (com `| safe`). Vantagens
sobre Chart.js/canvas:

- **Offline / LGPD**: nenhuma chamada de rede (CDN), nenhum dado sai da máquina.
- **Print-perfeito**: vetorial, imprime/vira PDF nítido em qualquer zoom.
- **Zero dependência nova**: SVG é só texto (casa com a filosofia "stack leve"
  do Reports, que evita WeasyPrint/cairo).

Todo texto vindo de dado do usuário (IP, usuário) passa por `_esc()` (XML-safe).
"""

from __future__ import annotations

import html as _html
import math

# Paleta — espelha as variáveis CSS do base.html.
EMERALD = "#059669"
DANGER = "#dc2626"
WARN = "#d97706"
ZINC = "#71717a"
BORDER = "#e4e4e7"
TEXT = "#18181b"

_SVG_OPEN = (
    '<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
    'width="100%" height="{h}" font-family="-apple-system, Segoe UI, '
    'Cantarell, sans-serif" role="img">'
)


def _esc(value: object) -> str:
    return _html.escape(str(value), quote=True)


def _num(value: float) -> str:
    """Formata coordenada: int quando inteiro, senão 1 casa."""
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def _empty(msg: str = "sem dados", *, w: int = 600, h: int = 70) -> str:
    return (
        _SVG_OPEN.format(w=w, h=h)
        + f'<text x="{w / 2}" y="{h / 2}" text-anchor="middle" '
        f'dominant-baseline="central" font-size="12" fill="{ZINC}">'
        f"{_esc(msg)}</text></svg>"
    )


def hbar_chart(
    rows: list[tuple[str, float]],
    *,
    color: str = EMERALD,
    max_rows: int = 8,
    width: int = 600,
    label_w: int = 160,
    row_h: int = 26,
    gap: int = 8,
) -> str:
    """Barras horizontais rotuladas. rows = [(label, valor), …].

    Ideal para rankings (top IPs banidos, top usuários sudo).
    """
    rows = [(str(lbl), float(v)) for lbl, v in rows][:max_rows]
    if not rows:
        return _empty("sem dados")
    maxv = max((v for _, v in rows), default=0) or 1
    bar_max = width - label_w - 56  # espaço pro número no fim
    height = len(rows) * (row_h + gap)
    parts = [_SVG_OPEN.format(w=width, h=height)]
    y = 0.0
    for label, v in rows:
        bw = max(2.0, bar_max * v / maxv)
        cy = y + row_h / 2
        parts.append(
            f'<text x="0" y="{_num(cy + 4)}" font-size="12" fill="{TEXT}">'
            f"{_esc(label)}</text>"
        )
        parts.append(
            f'<rect x="{label_w}" y="{_num(y + 3)}" width="{_num(bw)}" '
            f'height="{row_h - 6}" rx="3" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{_num(label_w + bw + 8)}" y="{_num(cy + 4)}" '
            f'font-size="12" font-weight="700" fill="{TEXT}">{_esc(int(v))}</text>'
        )
        y += row_h + gap
    parts.append("</svg>")
    return "".join(parts)


def bar_chart(
    pairs: list[tuple[str, float]],
    *,
    color: str = DANGER,
    width: int = 600,
    height: int = 150,
) -> str:
    """Barras verticais (histograma). pairs = [(label, valor), …].

    Ideal para séries temporais (tentativas falhadas por dia). Quando há
    muitas barras, rotula só algumas (evita sobreposição).
    """
    pairs = [(str(lbl), float(v)) for lbl, v in pairs]
    if not pairs:
        return _empty("sem dados")
    maxv = max((v for _, v in pairs), default=0) or 1
    n = len(pairs)
    pad_top, pad_bottom = 14, 22
    chart_h = height - pad_top - pad_bottom
    gap = 4 if n > 20 else 6
    bw = max(3.0, (width - gap * (n + 1)) / n)
    label_every = max(1, math.ceil(n / 12))
    parts = [_SVG_OPEN.format(w=width, h=height)]
    # linha de base
    base_y = pad_top + chart_h
    parts.append(
        f'<line x1="0" y1="{base_y}" x2="{width}" y2="{base_y}" '
        f'stroke="{BORDER}" stroke-width="1"/>'
    )
    x = gap
    for i, (label, v) in enumerate(pairs):
        bh = (chart_h * v / maxv) if v > 0 else 0
        y = pad_top + (chart_h - bh)
        if bh > 0:
            parts.append(
                f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(bw)}" '
                f'height="{_num(bh)}" rx="2" fill="{color}"/>'
            )
        if i % label_every == 0:
            parts.append(
                f'<text x="{_num(x + bw / 2)}" y="{height - 6}" font-size="9" '
                f'text-anchor="middle" fill="{ZINC}">{_esc(label)}</text>'
            )
        x += bw + gap
    parts.append("</svg>")
    return "".join(parts)


def donut(
    segments: list[tuple[str, float, str]],
    *,
    size: int = 150,
    stroke: int = 24,
) -> str:
    """Rosca proporcional. segments = [(label, valor, cor), …].

    Desenha o anel com `stroke-dasharray` por segmento e o total no centro.
    A legenda (qual cor é o quê) fica no template.
    """
    segs = [(str(lbl), float(v), str(c)) for lbl, v, c in segments if float(v) > 0]
    total = sum(v for _, v, _ in segs)
    if total <= 0:
        return _empty("sem dados", w=size, h=size)
    r = (size - stroke) / 2
    c = size / 2
    circ = 2 * math.pi * r
    parts = [_SVG_OPEN.format(w=size, h=size)]
    # anel de fundo
    parts.append(
        f'<circle cx="{_num(c)}" cy="{_num(c)}" r="{_num(r)}" fill="none" '
        f'stroke="{BORDER}" stroke-width="{stroke}"/>'
    )
    offset = 0.0
    for _label, v, color in segs:
        seg_len = circ * v / total
        parts.append(
            f'<circle cx="{_num(c)}" cy="{_num(c)}" r="{_num(r)}" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" '
            f'stroke-dasharray="{seg_len:.2f} {circ - seg_len:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {_num(c)} {_num(c)})"/>'
        )
        offset += seg_len
    parts.append(
        f'<text x="{_num(c)}" y="{_num(c)}" text-anchor="middle" '
        f'dominant-baseline="central" font-size="24" font-weight="700" '
        f'fill="{TEXT}">{int(total)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
