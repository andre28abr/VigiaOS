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
        assert ok is False and "encontrado" in out


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
        assert ok is False and "encontrado" in out


class TestUpdateCommands:
    def test_check_cmd_atomic(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        assert backend.check_update_command() == ["rpm-ostree", "upgrade", "--check"]

    def test_check_cmd_workstation(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        assert backend.check_update_command() == ["dnf", "check-update"]

    def test_update_cmd_atomic(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        assert backend.update_command() == ["rpm-ostree", "upgrade"]
        assert backend.update_command(elevated=True) == [
            "pkexec", "rpm-ostree", "upgrade",
        ]

    def test_update_cmd_workstation(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        assert backend.update_command() == ["dnf", "upgrade", "-y"]
        assert backend.update_command(elevated=True) == [
            "pkexec", "dnf", "upgrade", "-y",
        ]

    def test_display_cmd(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        assert backend.update_command_display() == "rpm-ostree upgrade"
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
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


class TestParseRpmOstreeCheck:
    def test_extracts_arrow_lines(self):
        out = "Diff:\n  lynis 3.0.8 -> 3.0.9\n  yara 4.5 -> 4.5.1\n"
        assert backend.parse_rpm_ostree_check(out) == ["lynis", "yara"]

    def test_skips_version_header_line(self):
        out = "Version: 40.20240101.0 -> 40.20240115.0\n  foo 1 -> 2\n"
        assert backend.parse_rpm_ostree_check(out) == ["foo"]

    def test_empty_when_no_arrows(self):
        assert backend.parse_rpm_ostree_check("No upgrade available.") == []


class TestCheckUpdates:
    def test_atomic_rc77_up_to_date(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(77, ""))
        info = backend.check_updates()
        assert info.checked is True and info.available is False

    def test_atomic_rc0_with_update(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        monkeypatch.setattr(
            backend.subprocess, "run",
            _fake_run(0, "AvailableUpdate:\n  foo 1 -> 2\n"))
        info = backend.check_updates()
        assert info.checked and info.available and info.packages == ["foo"]

    def test_atomic_rc0_no_upgrade_text(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        monkeypatch.setattr(
            backend.subprocess, "run", _fake_run(0, "No upgrade available."))
        info = backend.check_updates()
        assert info.checked is True and info.available is False

    def test_workstation_rc100_has_updates(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        monkeypatch.setattr(
            backend.subprocess, "run",
            _fake_run(100, "lynis.noarch 3.0.9 updates\n"))
        info = backend.check_updates()
        assert info.checked and info.available and info.packages == ["lynis"]

    def test_workstation_rc0_up_to_date(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(0, ""))
        info = backend.check_updates()
        assert info.checked is True and info.available is False

    def test_error_returncode_sets_error(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
        monkeypatch.setattr(backend.subprocess, "run", _fake_run(1, "", "boom"))
        info = backend.check_updates()
        assert info.checked is False and "boom" in info.error

    def test_timeout(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)

        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=180)

        monkeypatch.setattr(backend.subprocess, "run", boom)
        info = backend.check_updates()
        assert info.checked is False and "tempo limite" in info.error

    def test_binary_missing(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)

        def boom(*a, **k):
            raise FileNotFoundError()

        monkeypatch.setattr(backend.subprocess, "run", boom)
        info = backend.check_updates()
        assert info.checked is False and "encontrado" in info.error


class TestRunSystemUpdate:
    def test_atomic_uses_pkexec_rpm_ostree(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: True)
        run = _fake_run(0, "ok")
        monkeypatch.setattr(backend.subprocess, "run", run)
        ok, _ = backend.run_system_update_blocking()
        assert ok is True
        assert run.calls[0] == ["pkexec", "rpm-ostree", "upgrade"]

    def test_workstation_uses_pkexec_dnf(self, monkeypatch):
        monkeypatch.setattr(backend, "is_atomic", lambda: False)
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

    def test_atomico_sem_lista_vira_notif_de_sistema(self):
        info = backend.UpdateInfo(checked=True, available=True, packages=[])
        notes = backend.updates_to_notifications(info)
        assert len(notes) == 1
        assert "sistema" in notes[0].title.lower()
