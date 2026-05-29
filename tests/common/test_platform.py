"""Testes para vigia_common.platform (detecção atômico vs dnf)."""

from __future__ import annotations

from vigia_common import platform as plat


class TestIsAtomic:
    def test_atomic_when_marker_present(self, monkeypatch):
        monkeypatch.setattr(
            plat.os.path, "exists", lambda p: p == plat._OSTREE_MARKER
        )
        assert plat.is_atomic() is True

    def test_not_atomic_when_marker_absent_and_no_rpm_ostree(self, monkeypatch):
        monkeypatch.setattr(plat.os.path, "exists", lambda p: False)
        monkeypatch.setattr(plat.shutil, "which", lambda cmd: None)
        assert plat.is_atomic() is False

    def test_fallback_atomic_when_rpm_ostree_and_ostree_dir(self, monkeypatch):
        # Marcador ausente, mas rpm-ostree presente E /ostree existe.
        monkeypatch.setattr(plat.os.path, "exists", lambda p: False)
        monkeypatch.setattr(plat.shutil, "which", lambda cmd: "/usr/bin/rpm-ostree")
        monkeypatch.setattr(plat.os.path, "isdir", lambda p: p == "/ostree")
        assert plat.is_atomic() is True

    def test_not_atomic_when_rpm_ostree_but_no_ostree_dir(self, monkeypatch):
        # rpm-ostree instalado num sistema dnf, mas sem /ostree → não é atômico.
        monkeypatch.setattr(plat.os.path, "exists", lambda p: False)
        monkeypatch.setattr(plat.shutil, "which", lambda cmd: "/usr/bin/rpm-ostree")
        monkeypatch.setattr(plat.os.path, "isdir", lambda p: False)
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
