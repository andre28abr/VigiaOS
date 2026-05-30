"""Testes do net_bandwidth (parser do nethogs -t + snapshot mockado).

Pure-Python — sem GTK, sem nethogs, sem root (subprocess mockado).
"""

from __future__ import annotations

import types

from vigia_dashboard import net_bandwidth as nb


SAMPLE = (
    "/usr/lib/firefox/firefox/2345/1000\t120.5\t980.2\n"
    "/usr/bin/curl/3001/1000\t5.0\t2.0\n"
    "unknown TCP/0/0\t0\t0\n"
)


class TestParseNethogsTrace:
    def test_parses_rows(self):
        rows = nb.parse_nethogs_trace(SAMPLE)
        assert [r.program for r in rows] == ["firefox", "curl"]
        ff = rows[0]
        assert ff.pid == 2345
        assert ff.sent_kbps == 120.5 and ff.recv_kbps == 980.2

    def test_sorted_by_total_desc(self):
        rows = nb.parse_nethogs_trace(SAMPLE)
        totals = [r.sent_kbps + r.recv_kbps for r in rows]
        assert totals == sorted(totals, reverse=True)

    def test_attributed_flag(self):
        rows = nb.parse_nethogs_trace(SAMPLE)
        assert all(r.attributed for r in rows)  # firefox/curl têm pid real

    def test_zero_traffic_lines_skipped(self):
        # "unknown TCP/0/0  0  0" tem tráfego zero -> ignorado
        rows = nb.parse_nethogs_trace(SAMPLE)
        assert "unknown TCP" not in [r.program for r in rows]
        assert "desconhecido" not in [r.program for r in rows]

    def test_unattributed_connection_shown_by_remote(self):
        # nethogs nao atribuiu (pid 0) mas HA trafego -> mostra endpoint remoto
        rows = nb.parse_nethogs_trace(
            "192.168.15.4:35690-1.0.0.1:443/0/0\t0.04\t0.01\n"
        )
        assert len(rows) == 1
        assert rows[0].pid == 0 and rows[0].attributed is False
        assert rows[0].program == "1.0.0.1:443"

    def test_real_nethogs_output(self):
        # output REAL da VM (conexão DoH pré-existente não atribuída +
        # cabeçalhos 'Adding local address' / 'Refreshing:').
        real = (
            "Adding local address: 192.168.15.4\n"
            "Ethernet link detected\n"
            "\n"
            "Refreshing:\n"
            "192.168.15.4:35690-1.0.0.1:443/0/0\t0.0433594\t0.0128906\n"
            "unknown TCP/0/0\t0\t0\n"
        )
        rows = nb.parse_nethogs_trace(real)
        assert len(rows) == 1
        assert rows[0].program == "1.0.0.1:443"
        assert rows[0].attributed is False
        assert abs(rows[0].sent_kbps - 0.0433594) < 1e-6

    def test_dedupe_keeps_last_refresh(self):
        # 2 refreshes do mesmo processo => mantém a última (estado recente)
        text = (
            "/usr/bin/curl/3001/1000\t5.0\t2.0\n"
            "/usr/bin/curl/3001/1000\t9.9\t1.1\n"
        )
        rows = nb.parse_nethogs_trace(text)
        assert len(rows) == 1
        assert rows[0].sent_kbps == 9.9 and rows[0].recv_kbps == 1.1

    def test_comma_decimal_locale(self):
        # locale pt-BR: nethogs poderia imprimir vírgula decimal
        rows = nb.parse_nethogs_trace("/usr/bin/curl/3001/1000\t5,5\t2,2\n")
        assert rows[0].sent_kbps == 5.5 and rows[0].recv_kbps == 2.2

    def test_empty(self):
        assert nb.parse_nethogs_trace("") == []

    def test_ignores_garbage_lines(self):
        rows = nb.parse_nethogs_trace("Waiting for first packet...\n" + SAMPLE)
        assert len(rows) == 2


def _fake_run(returncode=0, stdout="", stderr=""):
    def runner(cmd, *a, **kw):
        runner.cmd = cmd
        return types.SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr
        )
    return runner


class TestBandwidthSnapshot:
    def test_not_installed(self, monkeypatch):
        monkeypatch.setattr(nb, "nethogs_installed", lambda: False)
        res = nb.bandwidth_snapshot_blocking()
        assert "nethogs não instalado" in res.error

    def test_success_cmd_and_rows(self, monkeypatch):
        monkeypatch.setattr(nb, "nethogs_installed", lambda: True)
        run = _fake_run(returncode=0, stdout=SAMPLE)
        monkeypatch.setattr(nb.subprocess, "run", run)
        res = nb.bandwidth_snapshot_blocking()
        assert res.error == ""
        assert res.rows[0].program == "firefox"
        # comando: pkexec env LC_ALL=C nethogs -t -c N -d D
        assert run.cmd[:4] == ["pkexec", "env", "LC_ALL=C", "nethogs"]
        assert "-t" in run.cmd

    def test_auth_cancelled(self, monkeypatch):
        monkeypatch.setattr(nb, "nethogs_installed", lambda: True)
        monkeypatch.setattr(nb.subprocess, "run", _fake_run(returncode=126))
        res = nb.bandwidth_snapshot_blocking()
        assert "cancelada" in res.error.lower()

    def test_empty_output_is_error(self, monkeypatch):
        monkeypatch.setattr(nb, "nethogs_installed", lambda: True)
        monkeypatch.setattr(
            nb.subprocess, "run", _fake_run(returncode=0, stdout="")
        )
        res = nb.bandwidth_snapshot_blocking()
        assert res.rows == [] and "Sem tráfego" in res.error

    def test_binary_missing(self, monkeypatch):
        monkeypatch.setattr(nb, "nethogs_installed", lambda: True)

        def boom(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(nb.subprocess, "run", boom)
        res = nb.bandwidth_snapshot_blocking()
        assert "encontrado" in res.error
