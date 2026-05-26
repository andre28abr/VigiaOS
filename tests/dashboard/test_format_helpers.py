"""Testes para format helpers do Dashboard backend.

format_uptime, format_kb, format_bytes, format_mbps — sao usados em
sparklines, KPI cards, tooltips. Bugs aqui mostram numeros errados ao
usuario.
"""

from __future__ import annotations

import pytest

from vigia_dashboard.backend import (
    format_bytes,
    format_kb,
    format_mbps,
    format_uptime,
)


class TestFormatUptime:
    def test_seconds_only(self):
        assert format_uptime(45) == "45s"

    def test_zero(self):
        assert format_uptime(0) == "0s"

    def test_minutes(self):
        assert format_uptime(60) == "1m"

    def test_minutes_plus(self):
        assert format_uptime(125) == "2m"

    def test_hours(self):
        assert format_uptime(3600) == "1h 0m"

    def test_hours_plus_minutes(self):
        assert format_uptime(3725) == "1h 2m"

    def test_days(self):
        assert format_uptime(86400) == "1d 0h 0m"

    def test_days_plus(self):
        assert format_uptime(123456) == "1d 10h 17m"

    def test_long_uptime(self):
        # 100 dias
        sec = 100 * 86400
        result = format_uptime(sec)
        assert result.startswith("100d")


class TestFormatKb:
    def test_bytes_under_kb(self):
        # KB de entrada → saida em KB se < 1024 KB
        assert format_kb(500) == "500 KB"

    def test_exact_mb(self):
        # 1024 KB = 1 MB
        assert format_kb(1024) == "1.0 MB"

    def test_mb_range(self):
        # 2048 KB = 2 MB
        assert format_kb(2048) == "2.0 MB"

    def test_gb_range(self):
        # 1 GB = 1024 * 1024 KB
        assert format_kb(1024 * 1024) == "1.0 GB"

    def test_large_gb(self):
        assert format_kb(8 * 1024 * 1024) == "8.0 GB"

    def test_zero(self):
        assert format_kb(0) == "0 KB"


class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500 B"

    def test_kb(self):
        assert format_bytes(1500) == "1.5 KB"

    def test_mb(self):
        assert format_bytes(2 * 1024 * 1024) == "2.0 MB"

    def test_gb(self):
        assert format_bytes(3 * 1024 ** 3) == "3.0 GB"

    def test_zero(self):
        assert format_bytes(0) == "0 B"


class TestFormatMbps:
    def test_mb_per_sec(self):
        # Input: MB/s. >=1 fica como MB/s.
        assert format_mbps(5.5) == "5.5 MB/s"

    def test_gb_per_sec(self):
        # >= 1024 MB/s → GB/s
        assert format_mbps(2048.0) == "2.0 GB/s"

    def test_kb_per_sec(self):
        # < 1 MB/s mas >= 0.001 MB/s → KB/s
        assert format_mbps(0.5) == "512 KB/s"

    def test_bytes_per_sec(self):
        # Muito pequeno (< 0.001 MB/s) → B/s
        assert format_mbps(0.0001) == "105 B/s"

    def test_zero(self):
        # Zero deve mostrar B/s, nao quebrar
        result = format_mbps(0.0)
        assert "B/s" in result or "MB/s" in result
