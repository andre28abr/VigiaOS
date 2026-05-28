"""Tests pro modulo auth.py do Vigia Hub (Polkit lock).

Cobre:
- policy_xml() retorna XML valido com action ID correto
- is_policy_installed checa os 2 dirs (system + /etc)
- installed_policy_path retorna path correto ou None
- install_policy chama pkexec install com formato esperado
- uninstall_policy idempotente
- check_auth retorna False se Polkit nao disponivel
- polkit_available True/False conforme import
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vigia_hub import auth


# ============================================================
# policy_xml
# ============================================================


class TestPolicyXml:
    def test_returns_valid_xml(self):
        xml = auth.policy_xml()
        # Parse — deve ser XML valido
        tree = ET.fromstring(xml)
        assert tree.tag == "policyconfig"

    def test_contains_action_id(self):
        xml = auth.policy_xml()
        assert auth.ACTION_ID in xml
        assert 'id="br.com.vigia.Hub.unlock"' in xml

    def test_contains_vendor(self):
        xml = auth.policy_xml()
        assert "VigiaOS" in xml

    def test_requires_auth_admin(self):
        """allow_active = auth_admin -> sempre pede senha."""
        xml = auth.policy_xml()
        assert "<allow_active>auth_admin</allow_active>" in xml
        assert "<allow_any>auth_admin</allow_any>" in xml
        assert "<allow_inactive>auth_admin</allow_inactive>" in xml

    def test_has_ptbr_translation(self):
        xml = auth.policy_xml()
        assert 'xml:lang="pt_BR"' in xml


# ============================================================
# is_policy_installed / installed_policy_path
# ============================================================


class TestIsPolicyInstalled:
    def test_false_when_no_files_exist(self, tmp_path: Path, monkeypatch):
        # Aponta POLICY_DIRS pra dirs vazios
        fake_dirs = [tmp_path / "a", tmp_path / "b"]
        for d in fake_dirs:
            d.mkdir()
        monkeypatch.setattr(auth, "POLICY_DIRS", fake_dirs)
        assert auth.is_policy_installed() is False

    def test_true_when_in_system_dir(self, tmp_path: Path, monkeypatch):
        sys_dir = tmp_path / "sys"
        sys_dir.mkdir()
        (sys_dir / auth.POLICY_FILENAME).write_text("<xml/>")
        monkeypatch.setattr(auth, "POLICY_DIRS", [sys_dir, tmp_path / "etc"])
        assert auth.is_policy_installed() is True

    def test_true_when_in_etc_dir(self, tmp_path: Path, monkeypatch):
        etc_dir = tmp_path / "etc"
        etc_dir.mkdir()
        (etc_dir / auth.POLICY_FILENAME).write_text("<xml/>")
        monkeypatch.setattr(auth, "POLICY_DIRS", [tmp_path / "sys", etc_dir])
        assert auth.is_policy_installed() is True


class TestInstalledPolicyPath:
    def test_returns_none_when_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(auth, "POLICY_DIRS", [tmp_path / "x"])
        assert auth.installed_policy_path() is None

    def test_returns_first_match(self, tmp_path: Path, monkeypatch):
        d1 = tmp_path / "sys"
        d2 = tmp_path / "etc"
        d1.mkdir()
        d2.mkdir()
        (d1 / auth.POLICY_FILENAME).write_text("<xml/>")
        (d2 / auth.POLICY_FILENAME).write_text("<xml/>")
        monkeypatch.setattr(auth, "POLICY_DIRS", [d1, d2])
        # Retorna o primeiro (sys tem prioridade)
        result = auth.installed_policy_path()
        assert result is not None
        assert result.parent == d1


# ============================================================
# install_policy
# ============================================================


class TestInstallPolicy:
    @patch("vigia_hub.auth.subprocess.run")
    def test_calls_pkexec_install(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        ok, err = auth.install_policy()
        assert ok is True
        assert err == ""
        # Confere que chamou pkexec install com -m 0644 -o root -g root
        args = mock_run.call_args[0][0]
        assert args[0] == "pkexec"
        assert args[1] == "install"
        assert "-m" in args
        assert "0644" in args
        assert "-o" in args
        assert "root" in args

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_error_on_pkexec_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=126,
            stderr="user canceled the authentication\n",
        )
        ok, err = auth.install_policy()
        assert ok is False
        assert "canceled" in err.lower() or "126" in err

    @patch("vigia_hub.auth.subprocess.run")
    def test_handles_oserror(self, mock_run):
        mock_run.side_effect = OSError("pkexec not found")
        ok, err = auth.install_policy()
        assert ok is False
        assert "pkexec" in err.lower()


# ============================================================
# uninstall_policy
# ============================================================


class TestUninstallPolicy:
    def test_idempotent_when_already_removed(self, tmp_path, monkeypatch):
        # Aponta INSTALL_TARGET pra path que nao existe
        monkeypatch.setattr(auth, "INSTALL_TARGET", tmp_path / "nope.policy")
        ok, err = auth.uninstall_policy()
        assert ok is True
        assert err == ""

    @patch("vigia_hub.auth.subprocess.run")
    def test_calls_pkexec_rm_if_file_exists(self, mock_run, tmp_path, monkeypatch):
        target = tmp_path / "test.policy"
        target.write_text("<xml/>")
        monkeypatch.setattr(auth, "INSTALL_TARGET", target)
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        ok, err = auth.uninstall_policy()
        assert ok is True
        args = mock_run.call_args[0][0]
        assert args[0] == "pkexec"
        assert args[1] == "rm"


# ============================================================
# check_auth / polkit_available
# ============================================================


class TestCheckAuth:
    def test_returns_false_when_polkit_unavailable(self):
        """Em ambiente sem PyGObject (ex: macOS dev), check_auth nao crasha.

        O modulo auth.py tem try/except ValueError/ImportError no import
        dentro de check_auth, entao retorna (False, "Polkit nao disponivel...")
        sem propagar excecao.
        """
        ok, err = auth.check_auth()
        # Resultado depende do ambiente, mas NUNCA crasha
        assert isinstance(ok, bool)
        assert isinstance(err, str)
        if not ok:
            # Mensagem de erro deve mencionar Polkit
            assert "polkit" in err.lower()


class TestPolkitAvailable:
    def test_returns_bool(self):
        """polkit_available sempre retorna True ou False, nao crasha."""
        result = auth.polkit_available()
        assert isinstance(result, bool)


# ============================================================
# Constantes
# ============================================================


class TestConstants:
    def test_action_id_format(self):
        assert auth.ACTION_ID == "br.com.vigia.Hub.unlock"

    def test_policy_filename(self):
        assert auth.POLICY_FILENAME == "br.com.vigia.Hub.policy"

    def test_install_target_in_etc(self):
        assert str(auth.INSTALL_TARGET).startswith("/etc/polkit-1/actions")

    def test_policy_dirs_includes_system_and_etc(self):
        paths = [str(d) for d in auth.POLICY_DIRS]
        assert any("/usr/share/polkit-1/actions" in p for p in paths)
        assert any("/etc/polkit-1/actions" in p for p in paths)
