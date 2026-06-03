"""Testes do backend do Tool Installer (Fedora Workstation, dnf).

Cobre install/uninstall, o helper _run_pkg_cmd, a checagem de updates
(`dnf check-update`) e a aplicacao (`pkexec dnf upgrade -y`).
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


class TestInstall:
    def test_install_uses_dnf(self, monkeypatch):
        run = _fake_run(stdout="done")
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, _ = backend.install_packages_blocking(["lynis", "aide"])
        assert ok is True
        assert run.calls[0] == ["pkexec", "dnf", "install", "-y", "lynis", "aide"]

    def test_uninstall_uses_dnf_remove(self, monkeypatch):
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
        assert ok is False and "encontrado" in out


class TestUpdateCommands:
    def test_check_cmd(self):
        assert backend.check_update_command() == ["dnf", "check-update"]

    def test_update_cmd(self):
        assert backend.update_command() == ["dnf", "upgrade", "-y"]
        assert backend.update_command(elevated=True) == [
            "pkexec", "dnf", "upgrade", "-y",
        ]

    def test_display_cmd(self):
        assert backend.update_command_display() == "sudo dnf upgrade"


class TestParseDnfCheckUpdate:
    def test_extracts_names_strips_arch(self):
        out = (
            "Last metadata expiration check: 0:10:00 ago on Mon.\n"
            "\n"
            "lynis.noarch            3.0.9-1.fc40      updates\n"
            "kernel.x86_64           6.8.1-1.fc40      updates\n"
        )
        assert backend.parse_dnf_check_update(out) == ["kernel", "lynis"]

    def test_ignores_obsoleting_block(self):
        out = (
            "foo.x86_64    1.0    repo\n"
            "Obsoleting Packages\n"
            "bar.x86_64    2.0    baz-1.0.x86_64    repo\n"
        )
        assert backend.parse_dnf_check_update(out) == ["foo"]

    def test_empty_inputs(self):
        assert backend.parse_dnf_check_update("") == []
        assert backend.parse_dnf_check_update(
            "Last metadata expiration check: x\n") == []

    def test_dedup_and_sorted(self):
        out = "foo.x86_64 1 r\nfoo.i686 1 r\nabc.noarch 2 r\n"
        assert backend.parse_dnf_check_update(out) == ["abc", "foo"]


class TestCheckUpdates:
    def test_rc100_has_updates(self, monkeypatch):
        monkeypatch.setattr(
            backend.subprocess, "run",
            _fake_run(100, "lynis.noarch 3.0.9 updates\n"))
        info = backend.check_updates()
        assert info.checked and info.available and info.packages == ["lynis"]

    def test_rc0_up_to_date(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(0, ""))
        info = backend.check_updates()
        assert info.checked is True and info.available is False

    def test_error_returncode_sets_error(self, monkeypatch):
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(1, "", "boom"))
        info = backend.check_updates()
        assert info.checked is False and "boom" in info.error

    def test_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=180)

        monkeypatch.setattr(backend.subprocess, "run", boom)
        info = backend.check_updates()
        assert info.checked is False and "tempo limite" in info.error

    def test_binary_missing(self, monkeypatch):
        def boom(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(backend.subprocess, "run", boom)
        info = backend.check_updates()
        assert info.checked is False and "encontrado" in info.error


class TestRunSystemUpdate:
    def test_uses_pkexec_dnf(self, monkeypatch):
        run = _fake_run(0, "ok")
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, _ = backend.run_system_update_blocking()
        assert ok is True
        assert run.calls[0] == ["pkexec", "dnf", "upgrade", "-y"]


class TestSplitUpdates:
    def test_separa_suite_de_sistema(self):
        suite, system = backend.split_updates(
            ["kernel", "lynis", "glibc", "clamav"])
        assert suite == ["lynis", "clamav"]
        assert system == ["kernel", "glibc"]

    def test_pacotes_vigia_vao_pra_suite(self):
        suite, system = backend.split_updates(["vigia-hub", "bash"])
        assert "vigia-hub" in suite and "bash" in system

    def test_vazio(self):
        assert backend.split_updates([]) == ([], [])

    def test_preserva_ordem_de_entrada(self):
        suite, _ = backend.split_updates(["clamav", "lynis"])
        assert suite == ["clamav", "lynis"]


class TestUpdatesToNotifications:
    def test_vazio_quando_sem_update(self):
        assert backend.updates_to_notifications(backend.UpdateInfo()) == []
        assert backend.updates_to_notifications(
            backend.UpdateInfo(checked=True, available=False)) == []

    def test_so_sistema(self):
        info = backend.UpdateInfo(
            checked=True, available=True, packages=["kernel", "glibc"])
        notes = backend.updates_to_notifications(info)
        assert len(notes) == 1
        assert "sistema" in notes[0].title.lower()

    def test_so_suite(self):
        info = backend.UpdateInfo(
            checked=True, available=True, packages=["lynis"])
        notes = backend.updates_to_notifications(info)
        assert len(notes) == 1
        assert "suíte" in notes[0].title.lower()

    def test_sistema_e_suite(self):
        info = backend.UpdateInfo(
            checked=True, available=True,
            packages=["kernel", "lynis", "clamav"])
        notes = backend.updates_to_notifications(info)
        assert len(notes) == 2
        titles = " ".join(n.title.lower() for n in notes)
        assert "sistema" in titles and "suíte" in titles

    def test_sem_lista_vira_notif_de_sistema(self):
        info = backend.UpdateInfo(checked=True, available=True, packages=[])
        notes = backend.updates_to_notifications(info)
        assert len(notes) == 1
        assert "sistema" in notes[0].title.lower()
