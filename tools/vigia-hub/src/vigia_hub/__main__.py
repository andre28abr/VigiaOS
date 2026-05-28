"""Entry point: `python -m vigia_hub` ou `vigia-hub` apos pip install.

CLI:
    vigia-hub               # abre janela normalmente
    vigia-hub --minimized   # inicia sem mostrar janela (so tray, requer
                            # settings.show_tray=True; senao ignora a flag)
"""

from __future__ import annotations

import sys

from .app import VigiaHubApp
from .logging_setup import setup_logging


def main() -> int:
    setup_logging()  # ANTES de qualquer log no app
    minimized = "--minimized" in sys.argv
    if minimized:
        # Remove a flag pra nao confundir Gio.Application.run
        argv = [a for a in sys.argv if a != "--minimized"]
    else:
        argv = sys.argv
    app = VigiaHubApp(start_minimized=minimized)
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main())
