"""Tests pro backend do Vigia Deployments Manager.

Cobre:
- rpmostree_available via shutil.which
- get_deployments com mock de subprocess (parser JSON)
- get_boot_usage com mock de df
- Dataclasses defaults
- is_safe_to_delete logic
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vigia_deployments import backend


# ============================================================
# Sanity
# ============================================================


class TestRpmOstreeAvailable:
    @patch("vigia_deployments.backend.shutil.which")
    def test_available(self, mock_which):
        mock_which.return_value = "/usr/bin/rpm-ostree"
        assert backend.rpmostree_available() is True

    @patch("vigia_deployments.backend.shutil.which")
    def test_not_available(self, mock_which):
        mock_which.return_value = None
        assert backend.rpmostree_available() is False


# ============================================================
# Dataclasses
# ============================================================


class TestDataclassDefaults:
    def test_deployment_defaults(self):
        d = backend.Deployment(
            index=0, checksum="abc", base_commit="abc",
            timestamp=0, timestamp_str="", osname="",
            origin="", version="",
            booted=True, pinned=False, staged=False,
        )
        assert d.index == 0
        assert d.layered_packages == []
        assert d.removed_base_packages == []
        assert d.unlocked == "none"

    def test_bootusage_defaults(self):
        u = backend.BootUsage()
        assert u.total_mb == 0
        assert u.used_mb == 0
        assert u.avail_mb == 0
        assert u.percent_used == 0
        assert u.available is False


# ============================================================
# Parser JSON do rpm-ostree status
# ============================================================


SAMPLE_STATUS_JSON = """
{
  "deployments": [
    {
      "checksum": "abc123def456abc123def456abc123def456abc123def456abc123def456abcd",
      "timestamp": 1716800000,
      "osname": "fedora",
      "origin": "fedora:fedora/41/x86_64/silverblue",
      "version": "41.20260520.0",
      "booted": true,
      "pinned": false,
      "staged": false,
      "requested-packages": ["dnscrypt-proxy", "chkrootkit"],
      "requested-base-removals": []
    },
    {
      "checksum": "fff999eee888fff999eee888fff999eee888fff999eee888fff999eee888ffff",
      "timestamp": 1716700000,
      "osname": "fedora",
      "origin": "fedora:fedora/41/x86_64/silverblue",
      "version": "41.20260519.0",
      "booted": false,
      "pinned": true,
      "staged": false,
      "requested-packages": []
    }
  ]
}
"""


class TestGetDeployments:
    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.rpmostree_available")
    def test_parses_json(self, mock_avail, mock_run):
        mock_avail.return_value = True
        mock_run.return_value = (0, SAMPLE_STATUS_JSON, "")

        deployments = backend.get_deployments()
        assert len(deployments) == 2

        d0 = deployments[0]
        assert d0.index == 0
        assert d0.checksum.startswith("abc123")
        assert d0.base_commit == "abc123de"
        assert d0.timestamp == 1716800000
        assert d0.booted is True
        assert d0.pinned is False
        assert "dnscrypt-proxy" in d0.layered_packages
        assert "chkrootkit" in d0.layered_packages

        d1 = deployments[1]
        assert d1.index == 1
        assert d1.booted is False
        assert d1.pinned is True

    @patch("vigia_deployments.backend.rpmostree_available")
    def test_empty_when_not_available(self, mock_avail):
        mock_avail.return_value = False
        assert backend.get_deployments() == []

    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.rpmostree_available")
    def test_empty_when_cmd_fails(self, mock_avail, mock_run):
        mock_avail.return_value = True
        mock_run.return_value = (1, "", "error")
        assert backend.get_deployments() == []

    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.rpmostree_available")
    def test_empty_when_invalid_json(self, mock_avail, mock_run):
        mock_avail.return_value = True
        mock_run.return_value = (0, "not valid json {", "")
        assert backend.get_deployments() == []

    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.rpmostree_available")
    def test_format_timestamp(self, mock_avail, mock_run):
        """timestamp_str eh formatado pra display."""
        mock_avail.return_value = True
        mock_run.return_value = (0, SAMPLE_STATUS_JSON, "")
        ds = backend.get_deployments()
        assert ds[0].timestamp_str  # nao vazio


# ============================================================
# Boot usage
# ============================================================


SAMPLE_DF_OUTPUT = """\
Filesystem     1M-blocks  Used Available Use% Mounted on
/dev/nvme0n1p2       976   245       675  27% /boot
"""


class TestGetBootUsage:
    @patch("vigia_deployments.backend.Path.is_dir")
    @patch("vigia_deployments.backend._run")
    def test_parses_df_output(self, mock_run, mock_isdir):
        mock_isdir.return_value = True
        mock_run.return_value = (0, SAMPLE_DF_OUTPUT, "")

        u = backend.get_boot_usage()
        assert u.available is True
        assert u.total_mb == 976
        assert u.used_mb == 245
        assert u.avail_mb == 675
        assert u.percent_used == 27

    @patch("vigia_deployments.backend.Path.is_dir")
    def test_no_boot_dir(self, mock_isdir):
        mock_isdir.return_value = False
        u = backend.get_boot_usage()
        assert u.available is False

    @patch("vigia_deployments.backend.Path.is_dir")
    @patch("vigia_deployments.backend._run")
    def test_df_command_fails(self, mock_run, mock_isdir):
        mock_isdir.return_value = True
        mock_run.return_value = (1, "", "")
        u = backend.get_boot_usage()
        assert u.available is False


# ============================================================
# is_safe_to_delete
# ============================================================


class TestIsSafeToDelete:
    def test_booted_not_safe(self):
        d = backend.Deployment(
            index=0, checksum="x", base_commit="x", timestamp=0,
            timestamp_str="", osname="", origin="", version="",
            booted=True, pinned=False, staged=False,
        )
        assert backend.is_safe_to_delete(d) is False

    def test_pinned_not_safe(self):
        d = backend.Deployment(
            index=1, checksum="x", base_commit="x", timestamp=0,
            timestamp_str="", osname="", origin="", version="",
            booted=False, pinned=True, staged=False,
        )
        assert backend.is_safe_to_delete(d) is False

    def test_normal_rollback_safe(self):
        d = backend.Deployment(
            index=1, checksum="x", base_commit="x", timestamp=0,
            timestamp_str="", osname="", origin="", version="",
            booted=False, pinned=False, staged=False,
        )
        assert backend.is_safe_to_delete(d) is True


# ============================================================
# Operations error handling
# ============================================================


class TestOperationsErrorHandling:
    @patch("vigia_deployments.backend.shutil.which")
    def test_rollback_no_pkexec(self, mock_which):
        mock_which.return_value = None
        ok, err = backend.rollback_blocking()
        assert not ok
        assert "pkexec" in err.lower()

    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.shutil.which")
    @patch("vigia_deployments.backend.rpmostree_available")
    def test_rollback_auth_cancel(self, mock_avail, mock_which, mock_run):
        mock_avail.return_value = True
        mock_which.return_value = "/usr/bin/pkexec"
        mock_run.return_value = (126, "", "")
        ok, err = backend.rollback_blocking()
        assert not ok
        assert "cancel" in err.lower() or "autenti" in err.lower()

    def test_pin_invalid_index(self):
        with patch("vigia_deployments.backend.shutil.which", return_value="/usr/bin/pkexec"):
            ok, err = backend.pin_blocking(-1)
            assert not ok
            assert "inválido" in err.lower()

    @patch("vigia_deployments.backend._run")
    @patch("vigia_deployments.backend.shutil.which")
    def test_cleanup_all_command_format(self, mock_which, mock_run):
        """Cleanup chama 'rpm-ostree cleanup -p -r -m' em 1 pkexec."""
        mock_which.return_value = "/usr/bin/pkexec"
        mock_run.return_value = (0, "", "")
        ok, _ = backend.cleanup_all_blocking()
        assert ok
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pkexec"
        assert "rpm-ostree" in cmd
        assert "cleanup" in cmd
        assert "-p" in cmd
        assert "-r" in cmd
        assert "-m" in cmd
