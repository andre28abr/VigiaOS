"""Testes para vigia_common.platform (Fedora Workstation / dnf)."""

from __future__ import annotations

from vigia_common import platform as plat


class TestPackageManager:
    def test_dnf(self):
        assert plat.package_manager() == "dnf"
        assert plat.needs_reboot_to_apply() is False


class TestInstallHint:
    def test_workstation(self):
        assert (
            plat.install_hint("clamav", "clamav-update")
            == "sudo dnf install clamav clamav-update"
        )

    def test_reboot_param_ignored(self):
        # `reboot` é aceito por compatibilidade mas não muda o comando (dnf).
        assert plat.install_hint("aide", reboot=False) == "sudo dnf install aide"
