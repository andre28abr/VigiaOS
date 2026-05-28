"""Tests pro logging_setup do Vigia Hub."""

from __future__ import annotations

import logging
import os

import pytest

from vigia_hub import logging_setup


class TestSetupLogging:
    def setup_method(self):
        # Reset estado entre tests
        logging_setup._CONFIGURED = False
        # Limpa handlers existentes
        root = logging.getLogger()
        for h in list(root.handlers):
            root.removeHandler(h)

    def test_is_idempotent(self):
        """Chamar 2x nao adiciona handlers duplicados."""
        logging_setup.setup_logging()
        first_count = len(logging.getLogger().handlers)
        logging_setup.setup_logging()
        second_count = len(logging.getLogger().handlers)
        assert first_count == second_count

    def test_respects_env_var(self, monkeypatch):
        monkeypatch.setenv("VIGIA_LOG_LEVEL", "DEBUG")
        logging_setup.setup_logging()
        assert logging.getLogger().level == logging.DEBUG

    def test_default_is_info(self, monkeypatch):
        monkeypatch.delenv("VIGIA_LOG_LEVEL", raising=False)
        logging_setup.setup_logging()
        assert logging.getLogger().level == logging.INFO

    def test_invalid_level_falls_back_to_info(self, monkeypatch):
        monkeypatch.setenv("VIGIA_LOG_LEVEL", "VERBOSE")  # not valid
        logging_setup.setup_logging()
        assert logging.getLogger().level == logging.INFO


class TestGetLogger:
    def test_returns_logger_with_name(self):
        log = logging_setup.get_logger("vigia_hub.test")
        assert isinstance(log, logging.Logger)
        assert log.name == "vigia_hub.test"
