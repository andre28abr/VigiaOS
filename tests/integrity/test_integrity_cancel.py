"""Testes de cancelamento pkexec (rc 126/127) + regressao get_last_check.

(1) Cancelamento: para cada operacao que roda via pkexec e trata
    returncode in (126, 127), rc=126 e rc=127 devem resultar em FALHA com
    mensagem contendo "cancel" (case-insensitive):
      - run_init_blocking      -> (False, "...cancel...")
      - run_check_blocking     -> CheckResult.success False, .error "...cancel..."
      - run_update_blocking    -> (False, "...cancel...")
      - apply_silverblue_profile  -> (False, "...cancel...")
      - remove_silverblue_profile -> (False, "...cancel...")

(2) Regressao get_last_check(): se state["last_check"] NAO for dict (string
    ou lista), deve retornar (None, None) SEM levantar AttributeError.

NOTA de mock: backend.py faz `import subprocess`/`import shutil` no topo,
entao monkeypatcha-se `backend.subprocess.run`. Guards (aide_installed,
baseline_exists, active_conf_path) sao mockados p/ chegar ao pkexec. Nenhum
subprocess real e' disparado e nada e' escrito em /var ou ~.
"""

from __future__ import annotations

import types

import pytest

from vigia_integrity import backend


def _fake_run_rc(rc: int):
    """subprocess.run falso: grava cmds em .calls, devolve returncode=rc."""
    calls = []

    def runner(cmd, *a, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

    runner.calls = calls
    return runner


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch):
    """Impede leitura/escrita real de ~/.config/vigia/file-integrity.json."""
    monkeypatch.setattr(backend, "load_state", lambda: {})
    monkeypatch.setattr(backend, "save_state", lambda state: None)


# ============================================================
# (1) Cancelamento pkexec
# ============================================================


class TestRunInitCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, tmp_path, rc):
        conf = tmp_path / "aide.conf"
        conf.write_text("dummy", encoding="utf-8")
        monkeypatch.setattr(backend, "aide_installed", lambda: True)
        monkeypatch.setattr(backend, "active_conf_path", lambda: conf)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run_rc(rc))
        ok, msg = backend.run_init_blocking()
        assert ok is False
        assert "cancel" in msg.lower()


class TestRunCheckCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend, "aide_installed", lambda: True)
        monkeypatch.setattr(backend, "baseline_exists", lambda: True)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run_rc(rc))
        result = backend.run_check_blocking()
        assert result.success is False
        assert "cancel" in result.error.lower()


class TestRunUpdateCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend, "aide_installed", lambda: True)
        monkeypatch.setattr(backend, "baseline_exists", lambda: True)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run_rc(rc))
        ok, msg = backend.run_update_blocking()
        assert ok is False
        assert "cancel" in msg.lower()


class TestApplySilverblueProfileCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run_rc(rc))
        ok, msg = backend.apply_silverblue_profile()
        assert ok is False
        assert "cancel" in msg.lower()


class TestRemoveSilverblueProfileCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run_rc(rc))
        ok, msg = backend.remove_silverblue_profile()
        assert ok is False
        assert "cancel" in msg.lower()


# ============================================================
# (2) Regressao: get_last_check com last_check nao-dict
# ============================================================


class TestGetLastCheckNonDictRegression:
    @pytest.mark.parametrize(
        "garbage",
        ["lixo", ["x"], 42, 3.14, True, ("a", "b")],
    )
    def test_non_dict_last_check_returns_none_none(self, monkeypatch, garbage):
        # last_check corrompido (nao-dict) nao pode levantar AttributeError.
        monkeypatch.setattr(
            backend, "load_state", lambda: {"last_check": garbage}
        )
        ts, summary = backend.get_last_check()
        assert ts is None
        assert summary is None

    def test_string_last_check_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(
            backend, "load_state", lambda: {"last_check": "lixo"}
        )
        # nao deve levantar; explicitamente (None, None)
        assert backend.get_last_check() == (None, None)

    def test_list_last_check_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(
            backend, "load_state", lambda: {"last_check": ["x"]}
        )
        assert backend.get_last_check() == (None, None)

    def test_valid_dict_still_parses(self, monkeypatch):
        # sanity: dict valido continua funcionando (nao quebrei o happy path).
        monkeypatch.setattr(
            backend,
            "load_state",
            lambda: {
                "last_check": {
                    "timestamp": "2026-05-31T10:00:00",
                    "total_entries": 100,
                    "added": 1,
                    "removed": 2,
                    "changed": 3,
                }
            },
        )
        ts, summary = backend.get_last_check()
        assert ts is not None
        assert summary is not None
        assert summary.added == 1
        assert summary.removed == 2
        assert summary.changed == 3
        assert summary.total_entries == 100
