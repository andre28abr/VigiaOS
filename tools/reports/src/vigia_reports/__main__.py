"""Entry point: `python -m vigia_reports` ou `vigia-reports`."""

from __future__ import annotations

import sys

def main() -> int:
    argv = sys.argv[1:]
    # Modo headless (timer/cron): gera o relatorio sem importar GTK.
    if "--generate" in argv:
        from .cli import main_headless
        return main_headless(argv)
    from .app import VigiaReportsApp
    app = VigiaReportsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
