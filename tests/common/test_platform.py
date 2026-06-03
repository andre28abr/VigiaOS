"""Testes para vigia_common.platform (detecção atômico vs dnf)."""

from __future__ import annotations

from vigia_common import platform as plat


class TestIsAtomic:
    def test_always_false_on_workstation(self):
        # O VigiaOS roda em Fedora Workstation — is_atomic() é sempre False.
        # (O projeto migrou do Silverblue/atômico de vez; ver platform.py.)
        assert plat.is_atomic() is False


class TestPackageManager:
    def test_rpm_ostree_when_atomic(self, monkeypatch):
        monkeypatch.setattr(plat, "is_atomic", lambda: True)
        assert plat.package_manager() == "rpm-ostree"
        assert plat.needs_reboot_to_apply() is True

    def test_dnf_when_not_atomic(self, monkeypatch):
        monkeypatch.setattr(plat, "is_atomic", lambda: False)
        assert plat.package_manager() == "dnf"
        assert plat.needs_reboot_to_apply() is False


class TestInstallHint:
    def test_atomic_with_reboot(self, monkeypatch):
        monkeypatch.setattr(plat, "is_atomic", lambda: True)
        assert plat.install_hint("lynis") == "rpm-ostree install lynis && systemctl reboot"

    def test_atomic_no_reboot(self, monkeypatch):
        monkeypatch.setattr(plat, "is_atomic", lambda: True)
        assert plat.install_hint("aide", reboot=False) == "rpm-ostree install aide"

    def test_workstation_never_reboots(self, monkeypatch):
        monkeypatch.setattr(plat, "is_atomic", lambda: False)
        assert (
            plat.install_hint("clamav", "clamav-update")
            == "sudo dnf install clamav clamav-update"
        )
