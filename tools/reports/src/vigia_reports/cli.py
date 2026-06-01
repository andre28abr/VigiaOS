"""Modo headless: gera um relatório sem abrir a GUI.

    vigia-reports --generate <modelo> [--period N] [--admin]

Coleta, renderiza e salva (com selo .sha256), imprime o caminho e sai. É o que
o timer do systemd chama no agendamento automático. Sem `--generate`, o
`__main__` abre a interface normalmente.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import backend, renderer


def generate(template_id: str, days: int, elevated: bool) -> Path:
    period = backend.make_period(days)
    data = backend.collect_for(template_id, period, elevated=elevated)
    html = renderer.render_html(template_id, data)
    output_dir = backend.ensure_reports_dir()
    return renderer.write_report(html, template_id, output_dir)


def main_headless(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="vigia-reports",
        description="Gera um relatório do VigiaOS sem abrir a interface.",
    )
    parser.add_argument(
        "--generate", metavar="MODELO", required=True,
        choices=sorted(backend.COLLECTORS),
        help="Modelo: " + ", ".join(sorted(backend.COLLECTORS)),
    )
    parser.add_argument("--period", type=int, default=30, help="Janela em dias (padrão: 30).")
    parser.add_argument(
        "--admin", action="store_true",
        help="Coleta elevada (pkexec) — NÃO use em timer headless (pede senha).",
    )
    args = parser.parse_args(argv)
    try:
        path = generate(args.generate, args.period, args.admin)
    except Exception as e:  # pylint: disable=broad-except
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(path)
    return 0
