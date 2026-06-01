"""Testes de cancelamento pkexec (rc 126/127) dos scanners de rootkit.

O worker `_run_scan_streaming` (usado por scan_chkrootkit_async /
scan_rkhunter_async) roda via `subprocess.Popen(["pkexec", ...])` e, ao final,
trata `proc.returncode in (126, 127)` marcando o scan como cancelado:
    result.cancelled = True
    result.error = "Autenticação cancelada (pkexec)."

Aqui mockamos o Popen (stdout vazio, returncode 126/127) e asseguramos que o
ScanResult entregue ao on_done reflete o cancelamento, com "cancel" na msg.
Nenhum pkexec/chkrootkit/rkhunter real e' disparado e nada e' escrito em ~.
"""

from __future__ import annotations

import threading

import pytest

from vigia_rootkit import backend


def _fake_popen_factory(captured: list, rc: int, lines=None):
    """Popen falso: grava cmd em `captured`, stdout itera `lines` (default
    vazio) e returncode=rc apos wait()."""
    if lines is None:
        lines = []

    class FakeProc:
        def __init__(self, cmd, *a, **kw):
            captured.append(cmd)
            self.stdout = iter(lines)
            self.returncode = rc

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return self.returncode

    return FakeProc


def _run_scan_and_get_result(monkeypatch, starter, rc):
    """Dispara um scanner async com Popen mockado (returncode=rc) e devolve
    (ScanResult, cmd_capturado)."""
    captured: list = []
    # scanners "instalados" + pkexec disponivel (mesmo which truthy)
    monkeypatch.setattr(backend.shutil, "which", lambda _name: "/usr/bin/x")
    monkeypatch.setattr(
        backend.subprocess, "Popen", _fake_popen_factory(captured, rc)
    )
    # garante que nada seja salvo em ~ (alem do guard de cancelado)
    monkeypatch.setattr(backend, "_save_report", lambda result: None)

    box = {}
    done = threading.Event()

    def on_done(result):
        box["result"] = result
        done.set()

    t = starter(on_line=lambda _l: None, on_done=on_done, stop_flag=lambda: False)
    t.join(timeout=5)
    assert done.wait(timeout=5), "worker nao terminou a tempo"
    return box["result"], (captured[0] if captured else None)


class TestChkrootkitCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        result, cmd = _run_scan_and_get_result(
            monkeypatch, backend.scan_chkrootkit_async, rc
        )
        assert result.cancelled is True
        assert "cancel" in result.error.lower()
        # confirma que o pkexec foi de fato o comando lancado
        assert cmd is not None and cmd[0] == "pkexec"


class TestRkhunterCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        result, cmd = _run_scan_and_get_result(
            monkeypatch, backend.scan_rkhunter_async, rc
        )
        assert result.cancelled is True
        assert "cancel" in result.error.lower()
        assert cmd is not None and cmd[0] == "pkexec"
