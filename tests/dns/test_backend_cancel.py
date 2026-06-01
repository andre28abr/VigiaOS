"""Testes de cancelamento pkexec (rc 126/127) do backend dnscrypt-proxy.

Para cada operacao que roda via pkexec e trata returncode in (126, 127),
rc=126 e rc=127 devem resultar em FALHA com mensagem contendo "cancel"
(case-insensitive):
  - enable_blocking      -> (False, "...cancel...")
  - disable_blocking     -> (False, "...cancel...")
  - set_servers_blocking -> (False, "...cancel...")  [via _atomic_write_config_via_pkexec]

NOTA de mock: dnscrypt_backend.py faz `import subprocess`/`import shutil` no
topo e roteia TODO pkexec pelo helper `_run`. Monkeypatcha-se entao
`backend._run` (e `backend.shutil.which` p/ passar nos guards de instalacao).
Nenhum pkexec/systemctl real e' disparado e /etc nao e' tocado.
"""

from __future__ import annotations

import pytest

from vigia_dns import dnscrypt_backend as backend


def _fake_run_rc(rc: int):
    """_run falso: grava cmds em .calls, devolve (rc, "", "")."""
    calls = []

    def runner(cmd, timeout=30):
        calls.append(cmd)
        return rc, "", ""

    runner.calls = calls
    return runner


@pytest.fixture(autouse=True)
def _bins_present(monkeypatch):
    """dnscrypt-proxy e pkexec "instalados" (shutil.which truthy)."""
    monkeypatch.setattr(backend.shutil, "which", lambda _name: "/usr/bin/x")


class TestEnableCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend, "_run", _fake_run_rc(rc))
        ok, msg = backend.enable_blocking()
        assert ok is False
        assert "cancel" in msg.lower()


class TestDisableCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend, "_run", _fake_run_rc(rc))
        ok, msg = backend.disable_blocking()
        assert ok is False
        assert "cancel" in msg.lower()


class TestSetServersCancel:
    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, tmp_path, rc):
        # CONFIG_PATH.exists() True + _read_config_lines() nao-vazio ->
        # chega em _atomic_write_config_via_pkexec -> _run (que cancela).
        cfg = tmp_path / "dnscrypt-proxy.toml"
        cfg.write_text("server_names = []\n", encoding="utf-8")
        monkeypatch.setattr(backend, "CONFIG_PATH", cfg)
        monkeypatch.setattr(
            backend, "_read_config_lines", lambda: ["server_names = []\n"]
        )
        run = _fake_run_rc(rc)
        monkeypatch.setattr(backend, "_run", run)
        ok, msg = backend.set_servers_blocking(["cloudflare", "google"])
        assert ok is False
        assert "cancel" in msg.lower()
        # confirma que de fato chegou ao pkexec (helper foi chamado)
        assert run.calls, "pkexec helper nao foi chamado"
