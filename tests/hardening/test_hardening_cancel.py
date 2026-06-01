"""Testes de cancelamento pkexec (rc 126/127) + regressao do julgamento por
artefato em run_audit_blocking.

(1) Cancelamento: run_audit_blocking com rc 126/127 -> (False, "...cancel...").

(2) Regressao "julga pelo artefato": o Lynis pode sair com returncode != 0
    MESMO tendo (re)gerado o relatorio. A funcao deve:
      - retornar (True, "") quando o relatorio foi regenerado (mtime avancou),
        IGNORANDO o rc != 0;
      - retornar (False, ...) quando rc != 0 E o relatorio NAO foi regenerado.

NOTA de mock: backend.py faz `import subprocess`/`import shutil` no topo, entao
monkeypatcha-se `backend.subprocess.run` e `backend.shutil.which`. REPORT_PATH
e' redirecionado p/ um arquivo temporario (monkeypatch.setattr). Nenhum pkexec
ou lynis real e' disparado e /var/log nao e' tocado.
"""

from __future__ import annotations

import os
import types

import pytest

from vigia_hardening import backend


def _run_returning(rc: int, side_effect=None):
    """subprocess.run falso: returncode=rc. `side_effect(cmd)` roda antes de
    retornar (p/ simular o Lynis regenerando o relatorio)."""
    calls = []

    def runner(cmd, *a, **kw):
        calls.append(cmd)
        if side_effect is not None:
            side_effect(cmd)
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

    runner.calls = calls
    return runner


@pytest.fixture(autouse=True)
def _lynis_present(monkeypatch):
    """lynis_installed() -> True (via shutil.which) p/ todos os testes."""
    monkeypatch.setattr(backend.shutil, "which", lambda _name: "/usr/bin/lynis")


# ============================================================
# (1) Cancelamento pkexec
# ============================================================


class TestRunAuditCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, tmp_path, rc):
        report = tmp_path / "lynis-report.dat"
        monkeypatch.setattr(backend, "REPORT_PATH", report)
        monkeypatch.setattr(backend.subprocess, "run", _run_returning(rc))
        ok, msg = backend.run_audit_blocking()
        assert ok is False
        assert "cancel" in msg.lower()


# ============================================================
# (2) Regressao: julga pelo artefato (mtime), nao pelo rc
# ============================================================


class TestRunAuditJudgesByArtifact:
    def test_rc_nonzero_but_report_regenerated_is_success(
        self, monkeypatch, tmp_path
    ):
        report = tmp_path / "lynis-report.dat"
        report.write_text("antigo", encoding="utf-8")
        # "antes": fixa o mtime no passado.
        old = report.stat().st_mtime - 100
        os.utime(report, (old, old))
        monkeypatch.setattr(backend, "REPORT_PATH", report)

        def regenerate(_cmd):
            # Lynis "regenera" o relatorio: mtime avanca claramente.
            new = old + 50
            os.utime(report, (new, new))

        monkeypatch.setattr(
            backend.subprocess, "run", _run_returning(1, side_effect=regenerate)
        )
        ok, msg = backend.run_audit_blocking()
        assert ok is True
        assert msg == ""

    def test_rc_nonzero_and_report_not_regenerated_is_failure(
        self, monkeypatch, tmp_path
    ):
        report = tmp_path / "lynis-report.dat"
        report.write_text("antigo", encoding="utf-8")
        old = report.stat().st_mtime - 100
        os.utime(report, (old, old))
        monkeypatch.setattr(backend, "REPORT_PATH", report)
        # rc=1 e NENHUMA alteracao de mtime (sem side_effect) -> falha.
        monkeypatch.setattr(backend.subprocess, "run", _run_returning(1))
        ok, msg = backend.run_audit_blocking()
        assert ok is False
        assert "1" in msg  # menciona o codigo de saida

    def test_rc_nonzero_no_report_at_all_is_failure(self, monkeypatch, tmp_path):
        # Relatorio nunca existiu (before=0.0) e nao foi gerado (after=0.0).
        report = tmp_path / "nao-existe.dat"
        monkeypatch.setattr(backend, "REPORT_PATH", report)
        monkeypatch.setattr(backend.subprocess, "run", _run_returning(1))
        ok, msg = backend.run_audit_blocking()
        assert ok is False
        assert "1" in msg

    def test_rc_zero_without_regeneration_is_success(self, monkeypatch, tmp_path):
        # Sanity: rc=0 e sem mudanca de mtime ainda e' sucesso (happy path).
        report = tmp_path / "nao-existe.dat"
        monkeypatch.setattr(backend, "REPORT_PATH", report)
        monkeypatch.setattr(backend.subprocess, "run", _run_returning(0))
        ok, msg = backend.run_audit_blocking()
        assert ok is True
        assert msg == ""
