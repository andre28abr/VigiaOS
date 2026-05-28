"""Tests pro auth.py (v0.5.9 — refatorado pra pkexec direto).

Mudancas vs versao anterior:
- Removido: install_policy, uninstall_policy, wait_for_polkit_recognition,
  is_policy_installed, policy_xml — nao usamos mais .policy custom
- Adicionado: check_auth (sync), check_auth_async (async), pkexec_available
- Estrategia nova: pkexec /usr/bin/true via subprocess (sync) ou
  Gio.Subprocess (async). Sem PyGObject Polkit lib (thread-unsafe).
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vigia_hub import auth


# ============================================================
# Constantes
# ============================================================


class TestConstants:
    def test_pkexec_cmd_format(self):
        """Comando deve ser pkexec /usr/bin/true."""
        assert auth.PKEXEC_CMD[0] == "pkexec"
        assert auth.PKEXEC_CMD[1] == "/usr/bin/true"

    def test_no_polkit_action_id_constant(self):
        """v0.5.9 removeu .policy custom — sem ACTION_ID exposto."""
        # Nao deve mais existir
        assert not hasattr(auth, "ACTION_ID")
        assert not hasattr(auth, "POLICY_FILENAME")
        assert not hasattr(auth, "INSTALL_TARGET")


# ============================================================
# check_auth (sync)
# ============================================================


class TestCheckAuth:
    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_true_on_exit_zero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        ok, err = auth.check_auth()
        assert ok is True
        assert err == ""

    @patch("vigia_hub.auth.subprocess.run")
    def test_calls_pkexec_with_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        auth.check_auth()
        args = mock_run.call_args[0][0]
        assert args[0] == "pkexec"
        assert "/usr/bin/true" in args

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_false_on_exit_126(self, mock_run):
        """Exit 126 = user cancelled."""
        mock_run.return_value = MagicMock(returncode=126, stderr="")
        ok, err = auth.check_auth()
        assert ok is False
        assert "cancela" in err.lower() or "incorreta" in err.lower()

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_false_on_exit_127(self, mock_run):
        """Exit 127 = pkexec not found (system without Polkit)."""
        mock_run.return_value = MagicMock(returncode=127, stderr="")
        ok, err = auth.check_auth()
        assert ok is False
        assert "pkexec" in err.lower()

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Timeout 5min se user nao respondeu."""
        mock_run.side_effect = subprocess.TimeoutExpired("pkexec", 300)
        ok, err = auth.check_auth()
        assert ok is False
        assert "timeout" in err.lower()

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_false_when_pkexec_missing(self, mock_run):
        """FileNotFoundError = pkexec nem instalado."""
        mock_run.side_effect = FileNotFoundError("pkexec")
        ok, err = auth.check_auth()
        assert ok is False
        assert "pkexec" in err.lower()

    @patch("vigia_hub.auth.subprocess.run")
    def test_returns_stderr_on_unknown_error(self, mock_run):
        """Outros exits passam o stderr."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="some custom polkit error",
        )
        ok, err = auth.check_auth()
        assert ok is False
        assert "polkit error" in err.lower()

    @patch("vigia_hub.auth.subprocess.run")
    def test_timeout_300s(self, mock_run):
        """Confere que timeout passado e' 300s."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        auth.check_auth()
        kwargs = mock_run.call_args[1]
        assert kwargs.get("timeout") == 300


# ============================================================
# _format_pkexec_error (helper)
# ============================================================


class TestFormatPkexecError:
    def test_exit_126_returns_cancel_message(self):
        msg = auth._format_pkexec_error(126, "")
        assert "cancela" in msg.lower()

    def test_exit_127_returns_not_found(self):
        msg = auth._format_pkexec_error(127, "")
        assert "pkexec" in msg.lower()

    def test_uses_stderr_when_available(self):
        msg = auth._format_pkexec_error(1, "custom error from pkexec")
        assert msg == "custom error from pkexec"

    def test_generic_message_when_no_stderr(self):
        msg = auth._format_pkexec_error(99, "")
        assert "99" in msg


# ============================================================
# pkexec_available
# ============================================================


class TestPkexecAvailable:
    @patch("shutil.which")
    def test_true_when_present(self, mock_which):
        mock_which.return_value = "/usr/bin/pkexec"
        assert auth.pkexec_available() is True

    @patch("shutil.which")
    def test_false_when_missing(self, mock_which):
        mock_which.return_value = None
        assert auth.pkexec_available() is False


# ============================================================
# check_auth_async (interface)
# ============================================================


class TestCheckAuthAsync:
    def test_callback_called_on_gi_missing(self):
        """Se PyGObject Gio nao disponivel, callback recebe (False, err)."""
        results = []

        def callback(ok, err):
            results.append((ok, err))

        # No mac dev, gi nao instalado -> deve chamar callback com erro
        auth.check_auth_async(callback)

        # Em ambiente sem GI, callback e' invocado imediatamente
        # Em ambiente com GI, callback e' chamado pelo GMainLoop async
        # (que nao roda no teste). Aqui so verificamos que NAO crashou.
        # Se callback ja' foi chamado (sem GI), deve ter err
        if results:
            ok, err = results[0]
            assert ok is False
            assert isinstance(err, str)

    def test_callback_is_callable_param(self):
        """Funcao aceita callable como parametro sem crashar."""
        # Nao crasha mesmo com callback lambda
        auth.check_auth_async(lambda ok, err: None)
