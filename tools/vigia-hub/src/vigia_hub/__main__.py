"""Entry point do VigiaOS: `vigia-os` (ou `vigia-hub`, `python -m vigia_hub`).

CLI:
    vigia-os                  # abre o VigiaOS (seção Início)
    vigia-os --section blue   # abre já numa seção (inicio/hub/red/blue)
    vigia-os --minimized      # inicia sem janela visível (só tray; requer
                              # settings.show_tray=True; senão ignora a flag)
"""

from __future__ import annotations

import sys

from .app import VigiaHubApp
from .logging_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    setup_logging()  # ANTES de qualquer log no app
    argv = list(sys.argv if argv is None else argv)

    minimized = "--minimized" in argv
    argv = [a for a in argv if a != "--minimized"]

    # --section <inicio|hub|red|blue>: abre direto numa seção (usado pelos
    # atalhos vigia-blue/vigia-red). Removido de argv antes do Gio.run.
    start_section = None
    if "--section" in argv:
        i = argv.index("--section")
        if i + 1 < len(argv):
            start_section = argv[i + 1]
            del argv[i:i + 2]
        else:
            del argv[i]

    app = VigiaHubApp(start_minimized=minimized, start_section=start_section)
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main())
