"""Setup de logging do Vigia Hub.

Substitui os `print("[tag] ...")` espalhados pelo codigo por logging
estruturado. Logs vao pro stderr (default) e podem ser controlados via
variavel de ambiente VIGIA_LOG_LEVEL (DEBUG, INFO, WARNING, ERROR).

Default: INFO. Em desenvolvimento, exporte VIGIA_LOG_LEVEL=DEBUG pra
ver logs detalhados (ex: '[lock] toggled', '[tray] start').

Format: "[YYYY-MM-DD HH:MM:SS] LEVEL: tag: mensagem"
"""

from __future__ import annotations

import logging
import os
import sys


_CONFIGURED = False


def setup_logging() -> None:
    """Configura root logger. Idempotente — chamar varias vezes e' OK."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.environ.get("VIGIA_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    # Remove handlers anteriores (caso pytest tenha adicionado)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Retorna logger nomeado. Chame setup_logging() antes."""
    return logging.getLogger(name)
