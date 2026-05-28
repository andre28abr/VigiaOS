"""CLI `vigia` — status e backup/restore da suite pela linha de comando.

Subcomandos:
    vigia status [--json]              Estado da suite (módulos, scans, config)
    vigia backup [ARQUIVO.zip]         Cria backup .zip (0600)
    vigia restore ARQUIVO.zip [--dry-run]   Restaura de um backup
    vigia version                      Versão do Hub

Sem subcomando -> mostra o status resumido.

Entry point registrado no pyproject.toml: `vigia = vigia_hub.cli:main`.
PURO PYTHON (sem GTK) — roda em terminal headless.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from . import backup as backup_mod
from . import status as status_mod


def _cmd_status(args: argparse.Namespace) -> int:
    st = status_mod.gather()
    if getattr(args, "json", False):
        print(json.dumps(status_mod.to_dict(st), ensure_ascii=False, indent=2))
    else:
        print(status_mod.format_text(st))
    return 0


def _cmd_backup(args: argparse.Namespace) -> int:
    dest = Path(args.path) if args.path else None
    ok, msg, path = backup_mod.create_backup(dest)
    print(msg)
    if ok and path is not None:
        print(f"  → {path}")
    return 0 if ok else 1


def _cmd_restore(args: argparse.Namespace) -> int:
    ok, msg, labels = backup_mod.restore_backup(
        Path(args.path), dry_run=args.dry_run
    )
    print(msg)
    for label in labels:
        print(f"  • {label}")
    if ok and not args.dry_run:
        print("\nReinicie o Hub para aplicar todas as mudanças.")
    return 0 if ok else 1


def _cmd_version(_args: argparse.Namespace) -> int:
    print(f"vigia {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vigia",
        description="Vigia Suite — utilitário de linha de comando.",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_status = sub.add_parser("status", help="Mostra o estado da suite.")
    p_status.add_argument(
        "--json", action="store_true", help="Saída em JSON."
    )

    p_backup = sub.add_parser(
        "backup", help="Cria backup .zip (0600) de config + relatórios."
    )
    p_backup.add_argument(
        "path", nargs="?", default=None,
        help="Arquivo .zip de destino (padrão: ~/.local/share/vigia-hub/backups/).",
    )

    p_restore = sub.add_parser("restore", help="Restaura de um backup .zip.")
    p_restore.add_argument("path", help="Arquivo .zip a restaurar.")
    p_restore.add_argument(
        "--dry-run", action="store_true",
        help="Só mostra o que seria restaurado, sem escrever.",
    )

    sub.add_parser("version", help="Mostra a versão.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cmd = getattr(args, "cmd", None)
    if cmd is None or cmd == "status":
        return _cmd_status(args)
    if cmd == "backup":
        return _cmd_backup(args)
    if cmd == "restore":
        return _cmd_restore(args)
    if cmd == "version":
        return _cmd_version(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
