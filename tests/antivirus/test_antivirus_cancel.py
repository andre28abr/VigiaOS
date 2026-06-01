"""Testes de cancelamento pkexec + regressao do construtor de comando do scan.

(1) update_db_blocking: rc 126/127 (pkexec cancelado) -> falha com "cancel".
(2) Regressao: o comando do clamscan NAO pode conter as flags invalidas
    `--no-summary=no` nem `--bell=no` (faziam o clamscan abortar antes de
    escanear). Captura-se o `cmd` passado ao Popen.

NOTA de mock: backend.py faz `import subprocess`/`import shutil` no topo, entao
monkeypatcha-se `backend.subprocess` / `backend.shutil` / `backend._run`.
Nenhum subprocess real (pkexec/clamscan) e' disparado.
"""

from __future__ import annotations

import threading
import types

import pytest

from vigia_antivirus import backend


# ============================================================
# (1) Cancelamento pkexec — update_db_blocking
# ============================================================


class TestUpdateDbCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_pkexec_cancelled(self, monkeypatch, rc):
        # freshclam_installed() e pkexec disponiveis -> chega no _run.
        monkeypatch.setattr(backend.shutil, "which", lambda _name: "/usr/bin/x")
        captured = []

        def fake_run(cmd, timeout=30):
            captured.append(cmd)
            return rc, "", ""

        monkeypatch.setattr(backend, "_run", fake_run)
        ok, msg = backend.update_db_blocking()
        assert ok is False
        assert "cancel" in msg.lower()
        # garante que de fato passou pelo pkexec freshclam (path correto)
        assert captured and captured[0] == ["pkexec", "freshclam"]


# ============================================================
# (2) Regressao: comando do clamscan sem flags invalidas
# ============================================================


def _fake_popen_factory(captured: list, rc: int = 0, lines=None):
    """Cria um substituto de subprocess.Popen que grava o cmd em `captured`
    e devolve um processo falso cujo stdout itera `lines` (default 1 linha).
    """
    if lines is None:
        lines = ["dummy line\n"]

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


def _run_scan_capturing(monkeypatch, path: str, stop_after_first=True):
    """Dispara scan_async com Popen mockado e devolve o cmd capturado.

    stop_flag retorna True na 1a chamada (se stop_after_first) para encerrar
    o loop imediatamente — nenhum clamscan real roda.
    """
    captured: list = []
    monkeypatch.setattr(backend, "clamav_installed", lambda: True)
    monkeypatch.setattr(
        backend.subprocess, "Popen", _fake_popen_factory(captured)
    )
    # nao salvar relatorio em ~ durante o teste
    monkeypatch.setattr(backend, "_save_report", lambda result: None)

    done = threading.Event()

    def on_done(_result):
        done.set()

    stop_state = {"n": 0}

    def stop_flag():
        stop_state["n"] += 1
        return stop_after_first and stop_state["n"] >= 1

    t = backend.scan_async(
        path,
        on_line=lambda _line: None,
        on_done=on_done,
        stop_flag=stop_flag,
    )
    t.join(timeout=5)
    assert done.wait(timeout=5), "scan worker nao terminou a tempo"
    assert captured, "Popen nao foi chamado (worker abortou antes do comando)"
    return captured[0]


class TestScanCommandRegression:
    def test_cmd_has_no_invalid_summary_flag(self, monkeypatch, tmp_path):
        target = tmp_path / "alvo.txt"
        target.write_text("x", encoding="utf-8")
        cmd = _run_scan_capturing(monkeypatch, str(target))
        joined = " ".join(cmd)
        assert "--no-summary=no" not in joined
        assert not any(c.startswith("--no-summary=") for c in cmd)

    def test_cmd_has_no_invalid_bell_flag(self, monkeypatch, tmp_path):
        target = tmp_path / "alvo.txt"
        target.write_text("x", encoding="utf-8")
        cmd = _run_scan_capturing(monkeypatch, str(target))
        joined = " ".join(cmd)
        assert "--bell=no" not in joined
        assert not any(c.startswith("--bell=") for c in cmd)

    def test_cmd_is_clamscan_recursive_with_path(self, monkeypatch, tmp_path):
        target = tmp_path / "alvo.txt"
        target.write_text("x", encoding="utf-8")
        cmd = _run_scan_capturing(monkeypatch, str(target))
        assert cmd[0] == "clamscan"
        assert "-r" in cmd
        # path vem apos o "--" terminador de flags
        assert "--" in cmd
        assert cmd[-1] == str(target)
        # nenhum token com '=no' (cobre a familia de flags booleanas quebradas)
        assert not any(tok.endswith("=no") for tok in cmd)
