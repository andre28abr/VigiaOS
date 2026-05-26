"""Testes para parsers de /proc no Dashboard backend.

Estes parsers sao chamados a 1Hz — bugs aqui causam UI errada
constantemente. Cobre formatos reais do kernel Linux.
"""

from __future__ import annotations

import sys
from unittest.mock import mock_open, patch

import pytest

from vigia_dashboard import backend


# ============================================================
# /proc/stat parser
# ============================================================


SAMPLE_PROC_STAT = """cpu  100000 200 50000 800000 5000 0 1000 0 0 0
cpu0 12500 25 6250 100000 625 0 125 0 0 0
cpu1 12500 25 6250 100000 625 0 125 0 0 0
cpu2 12500 25 6250 100000 625 0 125 0 0 0
cpu3 12500 25 6250 100000 625 0 125 0 0 0
cpu4 12500 25 6250 100000 625 0 125 0 0 0
cpu5 12500 25 6250 100000 625 0 125 0 0 0
cpu6 12500 25 6250 100000 625 0 125 0 0 0
cpu7 12500 25 6250 100000 625 0 125 0 0 0
intr 12345
ctxt 999999
"""


class TestReadCpuTimes:
    def test_parses_total_cpu(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_PROC_STAT)):
            times = backend._read_cpu_times()
        # cpu (total) + cpu0..cpu7 = 9 entries
        assert len(times.cores) == 9
        # Total cpu times
        assert times.cores[0] == (100000, 200, 50000, 800000, 5000, 0, 1000)

    def test_parses_per_core_cpu(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_PROC_STAT)):
            times = backend._read_cpu_times()
        # cpu0 = (12500, 25, 6250, 100000, 625, 0, 125)
        assert times.cores[1] == (12500, 25, 6250, 100000, 625, 0, 125)

    def test_handles_missing_file(self):
        with patch("builtins.open", side_effect=OSError("not found")):
            times = backend._read_cpu_times()
        assert times.cores == []


# ============================================================
# get_cpu_snapshot delta calculation
# ============================================================


class TestCpuSnapshot:
    def test_first_call_no_delta(self):
        """Primeira chamada sem prev — pct=0."""
        with patch("builtins.open", mock_open(read_data=SAMPLE_PROC_STAT)):
            with patch("vigia_dashboard.backend._read_cpu_freq", return_value=0.0):
                with patch("vigia_dashboard.backend._read_cpu_temp", return_value=None):
                    snap = backend.get_cpu_snapshot(None)
        assert all(p == 0.0 for p in snap.per_core_pct)

    def test_delta_calculation(self):
        """Com prev, calcula % via formula (1 - idle_delta/total_delta) * 100."""
        # Prev: 800000 idle total
        prev = backend.CpuTimes(
            timestamp=1000.0,
            cores=[
                (100000, 200, 50000, 800000, 5000, 0, 1000),  # cpu total
                (12500, 25, 6250, 100000, 625, 0, 125),  # cpu0
            ],
        )

        # Current: aumentou idle apenas — espera cpu_pct baixo
        current_data = """cpu  100100 200 50050 800950 5000 0 1000 0 0 0
cpu0 12525 25 6260 100120 625 0 125 0 0 0
"""
        with patch("builtins.open", mock_open(read_data=current_data)):
            with patch("vigia_dashboard.backend._read_cpu_freq", return_value=0.0):
                with patch("vigia_dashboard.backend._read_cpu_temp", return_value=None):
                    snap = backend.get_cpu_snapshot(prev)

        # CPU total: total_delta=1100, idle_delta=950 → pct=(1-950/1100)*100 = ~13.6%
        assert 0 <= snap.total_pct <= 100
        assert snap.total_pct < 50  # nao saturado


# ============================================================
# get_mem_snapshot
# ============================================================


SAMPLE_MEMINFO = """MemTotal:       16000000 kB
MemFree:         3000000 kB
MemAvailable:    8000000 kB
Buffers:          500000 kB
Cached:          4500000 kB
SwapCached:           0 kB
Active:          7000000 kB
Inactive:        1500000 kB
SwapTotal:       2000000 kB
SwapFree:        1500000 kB
SReclaimable:    1000000 kB
"""


class TestMemSnapshot:
    def test_parses_meminfo(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_MEMINFO)):
            mem = backend.get_mem_snapshot()
        assert mem.total_kb == 16000000
        assert mem.free_kb == 3000000
        assert mem.available_kb == 8000000
        assert mem.buffers_kb == 500000
        # Cached + SReclaimable
        assert mem.cached_kb == 4500000 + 1000000
        assert mem.swap_total_kb == 2000000
        assert mem.swap_free_kb == 1500000

    def test_used_kb_uses_available(self):
        """used = total - available (nao - free, porque free ignora cache)."""
        with patch("builtins.open", mock_open(read_data=SAMPLE_MEMINFO)):
            mem = backend.get_mem_snapshot()
        assert mem.used_kb == 16000000 - 8000000

    def test_swap_used_calculation(self):
        with patch("builtins.open", mock_open(read_data=SAMPLE_MEMINFO)):
            mem = backend.get_mem_snapshot()
        assert mem.swap_used_kb == 2000000 - 1500000

    def test_missing_meminfo_returns_empty(self):
        with patch("builtins.open", side_effect=OSError("not found")):
            mem = backend.get_mem_snapshot()
        assert mem.total_kb == 0
        assert mem.used_kb == 0


# ============================================================
# get_load_avg
# ============================================================


class TestLoadAvg:
    def test_parses_loadavg(self):
        with patch("builtins.open", mock_open(read_data="0.50 0.75 1.00 2/345 67890\n")):
            load = backend.get_load_avg()
        assert load == (0.50, 0.75, 1.00)

    def test_handles_missing_file(self):
        with patch("builtins.open", side_effect=OSError("not found")):
            load = backend.get_load_avg()
        assert load == (0.0, 0.0, 0.0)

    def test_handles_malformed_loadavg(self):
        with patch("builtins.open", mock_open(read_data="not a number")):
            load = backend.get_load_avg()
        assert load == (0.0, 0.0, 0.0)


# ============================================================
# Socket inodes parsing (per-process connections)
# ============================================================


SAMPLE_PROC_NET_TCP = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0
   1: 0100007F:1F40 0100007F:8B60 01 00000000:00000000 00:00000000 00000000  1000        0 23456 1 0000000000000000 20 4 30 10 -1
   2: 0100007F:8B60 0100007F:1F40 06 00000000:00000000 00:00000000 00000000  1000        0 34567 1 0000000000000000 20 4 30 10 -1
"""


class TestSocketParsing:
    """Cache TTL 1s e' limpo via fixture autouse (isolamento)."""

    @pytest.fixture(autouse=True)
    def reset_sock_cache(self):
        backend._SOCK_INODES_CACHE = (0.0, {})
        yield
        backend._SOCK_INODES_CACHE = (0.0, {})

    def test_parses_tcp(self):
        """Mock /proc/net/tcp com 3 sockets; resto retorna empty."""
        from io import StringIO

        def fake_open(path, *args, **kwargs):
            if path == "/proc/net/tcp":
                return StringIO(SAMPLE_PROC_NET_TCP)
            return StringIO("header line\n")

        with patch("builtins.open", side_effect=fake_open):
            inode_map = backend._read_socket_inodes_to_conn()

        # Linha 0: state 0A inode 12345 = LISTEN
        # Linha 1: state 01 inode 23456 = ESTABLISHED
        # Linha 2: state 06 inode 34567 = TIME_WAIT (other)
        assert inode_map.get(12345) == "tcp_listen"
        assert inode_map.get(23456) == "tcp_established"
        assert inode_map.get(34567) == "tcp_other"

    def test_missing_files_returns_empty(self):
        with patch("builtins.open", side_effect=OSError("not found")):
            inode_map = backend._read_socket_inodes_to_conn()
        assert inode_map == {}


# ============================================================
# format_uptime edge cases adicionais
# ============================================================


class TestFormatUptimeMore:
    def test_negative_seconds(self):
        # Negativo nao deveria acontecer, mas nao deve quebrar
        result = backend.format_uptime(-100)
        # Como < 60: '-100s'. Nao quebra mas e' bizarro
        assert isinstance(result, str)
