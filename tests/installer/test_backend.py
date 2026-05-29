"""Testes do backend do Tool Installer.

Cobre o dispatch rpm-ostree (atomico) vs dnf (Workstation) introduzido no
B3, o helper _run_pkg_cmd e reboot_system.

NOTA de mock: backend.py faz `from vigia_common.platform import is_atomic`
no topo (binding no namespace do modulo), entao monkeypatcha-se
`backend.is_atomic` — NAO `vigia_common.platform.is_atomic`.
"""

from __future__ import annotations

import subprocess
import types

import pytest

from vigia_installer import backend


def _fake_run(returncode=0, stdout="", stderr=""):
    """subprocess.run falso que grava os cmds recebidos em .calls."""
    calls = []

    def runner(cmd, *a, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr
        )

    runner.calls = calls
    return runner


class TestInstallDispatch:
    def test_install_atomic_uses_rpm_ostree(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        run = _fake_run(stdout="done")
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, _ = backend.install_packages_blocking(["lynis"])
        assert ok is True
        assert run.calls[0] == [
            "pkexec", "rpm-ostree", "install", "--idempotent", "lynis",
        ]

    def test_install_workstation_uses_dnf(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        run = _fake_run(stdout="done")
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, _ = backend.install_packages_blocking(["lynis", "aide"])
        assert ok is True
        assert run.calls[0] == ["pkexec", "dnf", "install", "-y", "lynis", "aide"]

    def test_uninstall_atomic_no_idempotent(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        run = _fake_run()
        monkeypatch.setattr(backend.subprocess, "run", run)
        backend.uninstall_packages_blocking(["lynis"])
        assert run.calls[0] == ["pkexec", "rpm-ostree", "uninstall", "lynis"]

    def test_uninstall_workstation_uses_dnf_remove(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        run = _fake_run()
        monkeypatch.setattr(backend.subprocess, "run", run)
        backend.uninstall_packages_blocking(["lynis"])
        assert run.calls[0] == ["pkexec", "dnf", "remove", "-y", "lynis"]

    def test_empty_list_never_calls_subprocess(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            backend.subprocess, "run", lambda *a, **k: called.append(1)
        )
        ok_i, _ = backend.install_packages_blocking([])
        ok_u, _ = backend.uninstall_packages_blocking([])
        assert ok_i is False and ok_u is False
        assert called == []


class TestRunPkgCmd:
    def test_success_strips_stdout(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(0, "  ok\n"))
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is True and out == "ok"

    @pytest.mark.parametrize("rc", [126, 127])
    def test_pkexec_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(rc))
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and "cancelada" in out.lower()

    def test_generic_failure_includes_stderr(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(1, "", "erro X"))
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and "erro X" in out and "1" in out

    def test_failure_truncates_long_output(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(1, "", "E" * 2000))
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and out.count("E") <= 800

    def test_falls_back_to_stdout_when_no_stderr(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(1, "saida", ""))
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and "saida" in out

    def test_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=10)

        monkeypatch.setattr(backend.subprocess, "run", boom)
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and "tempo limite" in out

    def test_binary_missing(self, monkeypatch):
        def boom(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(backend.subprocess, "run", boom)
        ok, out = backend._run_pkg_cmd(["x"], 10, "teste")
        assert ok is False and "nao encontrado" in out


class TestRebootSystem:
    def test_success(self, monkeypatch):
        run = _fake_run(0)
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, out = backend.reboot_system()
        assert ok is True and out == ""
        assert run.calls[0] == ["pkexec", "systemctl", "reboot"]

    @pytest.mark.parametrize("rc", [126, 127])
    def test_cancelled(self, monkeypatch, rc):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(rc))
        ok, out = backend.reboot_system()
        assert ok is False and "cancelada" in out.lower()

    def test_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=10)

        monkeypatch.setattr(backend.subprocess, "run", boom)
        ok, out = backend.reboot_system()
        assert ok is False and "demorou" in out

    def test_binary_missing(self, monkeypatch):
        def boom(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(backend.subprocess, "run", boom)
        ok, out = backend.reboot_system()
        assert ok is False and "nao encontrado" in out
