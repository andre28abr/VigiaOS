"""Testes dos gráficos SVG (charts.py) — puros, sem GTK, sem rede."""

from __future__ import annotations

from vigia_reports import charts


class TestHBar:
    def test_basic_svg(self):
        svg = charts.hbar_chart([("185.1.2.3", 48), ("91.4.5.6", 24)])
        assert svg.startswith("<svg")
        assert svg.rstrip().endswith("</svg>")
        assert "185.1.2.3" in svg
        assert ">48<" in svg

    def test_empty(self):
        assert "sem dados" in charts.hbar_chart([])

    def test_caps_max_rows(self):
        rows = [(f"ip{i}", i + 1) for i in range(20)]
        svg = charts.hbar_chart(rows, max_rows=5)
        assert svg.count("<rect") == 5  # uma barra por linha

    def test_escapes_user_data(self):
        svg = charts.hbar_chart([("<script>x", 3)])
        assert "<script>" not in svg
        assert "&lt;script&gt;" in svg

    def test_zero_values_no_crash(self):
        assert "<svg" in charts.hbar_chart([("a", 0), ("b", 0)])


class TestBar:
    def test_basic_svg(self):
        svg = charts.bar_chart([("30/05", 5), ("31/05", 12)])
        assert svg.startswith("<svg")
        assert "<rect" in svg

    def test_empty(self):
        assert "sem dados" in charts.bar_chart([])

    def test_all_zero_no_div_by_zero(self):
        # maxv vira 1 internamente; não deve dividir por zero
        assert "<svg" in charts.bar_chart([("a", 0), ("b", 0)])

    def test_label_thinning(self):
        pairs = [(f"{i:02d}/05", i) for i in range(1, 31)]
        svg = charts.bar_chart(pairs)
        # 30 barras mas labels ralos (evita sobreposição)
        assert svg.count("<text") < 30


class TestDonut:
    def test_basic_total_center(self):
        svg = charts.donut([("Aceitos", 3, "#059669"), ("Falhados", 142, "#dc2626")])
        assert svg.startswith("<svg")
        assert "#059669" in svg and "#dc2626" in svg
        assert ">145<" in svg  # total no centro

    def test_all_zero_empty(self):
        assert "sem dados" in charts.donut([("a", 0, "#000"), ("b", 0, "#111")])

    def test_skips_zero_segments(self):
        svg = charts.donut([("a", 5, "#059669"), ("b", 0, "#dc2626")])
        # 1 círculo de fundo + 1 segmento (o zero não desenha)
        assert svg.count("<circle") == 2
