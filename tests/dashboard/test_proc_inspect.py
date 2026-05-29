"""Testes do inspetor de processo (strace -c) do Dashboard.

Parser puro + inspect_process_blocking com subprocess mockado (nao precisa
de strace nem root).
"""

from __future__ import annotations

import subprocess
import types

from vigia_dashboard import proc_inspect as pi


SAMPLE = """\
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 45.00    0.001234          12       100         2 read
 30.00    0.000800          10        80           write
 25.00    0.000600           8        50         1 openat
------ ----------- ----------- --------- --------- ----------------
100.00    0.002634                   230         3 total
"""


class TestParseStraceSummary:
    def test_parses_rows(self):
        rows, total = pi.parse_strace_summary(SAMPLE)
        assert [r.syscall for r in rows] == ["read", "write", "openat"]
        assert total == 230  # 100 + 80 + 50 (recalculado, ignora linha total)

    def test_errors_column_optional(self):
        rows, _ = pi.parse_strace_summary(SAMPLE)
        by_name = {r.syscall: r for r in rows}
        assert by_name["read"].errors == 2
        assert by_name["write"].errors == 0  # sem coluna de erro
        assert by_name["openat"].errors == 1

    def test_sorted_by_time_desc(self):
        rows, _ = pi.parse_strace_summary(SAMPLE)
        pcts = [r.time_pct for r in rows]
        assert pcts == sorted(pcts, reverse=True)

    def test_skips_header_separator_total(self):
        rows, _ = pi.parse_strace_summary(SAMPLE)
        names = {r.syscall for r in rows}
        assert "syscall" not in names and "total" not in names
        assert all("-" not in r.syscall for r in rows)

    def test_empty_text(self):
        rows, total = pi.parse_strace_summary("")
        assert rows == [] and total == 0

    def test_ignores_pkexec_noise(self):
        noisy = "==== AUTHENTICATING FOR org.freedesktop.policykit ====\n" + SAMPLE
        rows, total = pi.parse_strace_summary(noisy)
        assert len(rows) == 3 and total == 230

    def test_comma_decimal_locale(self):
        # locale pt-BR: strace imprime virgula decimal ("100,00") — bug real
        # reportado pelo Andre. O parser tem que normalizar pra ponto.
        sample = (
            "% time     seconds  usecs/call     calls    errors syscall\n"
            " 60,00    0,001000          10       100         5 read\n"
            " 40,00    0,000500           5        50           write\n"
            "100,00    0,001500                   150         5 total\n"
        )
        rows, total = pi.parse_strace_summary(sample)
        assert [r.syscall for r in rows] == ["read", "write"]
        assert total == 150
        assert rows[0].time_pct == 60.0


def _fake_run(returncode=0, stdout="", stderr=""):
    def runner(cmd, *a, **kw):
        runner.cmd = cmd
        return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)
    return runner


class TestInspectProcessBlocking:
    def test_success(self, monkeypatch):
        monkeypatch.setattr(pi, "strace_installed", lambda: True)
        # timeout costuma retornar 124, e o resumo vai pro stderr
        run = _fake_run(returncode=124, stderr=SAMPLE)
        monkeypatch.setattr(pi.subprocess, "run", run)
        res = pi.inspect_process_blocking(1234)
        assert res.error == ""
        assert res.total_calls == 230
        assert res.rows[0].syscall == "read"
        # comando: pkexec env LC_ALL=C timeout -s INT <dur> strace -f -c -p <pid>
        assert run.cmd[:3] == ["pkexec", "env", "LC_ALL=C"]
        assert "strace" in run.cmd
        assert run.cmd[-2:] == ["-p", "1234"]

    def test_not_installed(self, monkeypatch):
        monkeypatch.setattr(pi, "strace_installed", lambda: False)
        res = pi.inspect_process_blocking(1)
        assert "strace não instalado" in res.error

    def test_auth_cancelled(self, monkeypatch):
        monkeypatch.setattr(pi, "strace_installed", lambda: True)
        monkeypatch.setattr(pi.subprocess, "run", _fake_run(returncode=126))
        res = pi.inspect_process_blocking(1)
        assert "cancelada" in res.error.lower()

    def test_empty_stderr_is_error(self, monkeypatch):
        monkeypatch.setattr(pi, "strace_installed", lambda: True)
        monkeypatch.setattr(pi.subprocess, "run", _fake_run(returncode=124, stderr=""))
        res = pi.inspect_process_blocking(1)
        assert res.rows == [] and "Sem dados" in res.error

    def test_timeout(self, monkeypatch):
        monkeypatch.setattr(pi, "strace_installed", lambda: True)

        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        monkeypatch.setattr(pi.subprocess, "run", boom)
        res = pi.inspect_process_blocking(1)
        assert "tempo limite" in res.error
