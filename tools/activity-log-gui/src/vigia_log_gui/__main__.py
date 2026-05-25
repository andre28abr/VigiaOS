"""Entry point: `python -m vigia_log_gui` ou `vigia-log-gui`."""

from __future__ import annotations

import sys

from .app import VigiaLogGuiApp


def main() -> int:
    app = VigiaLogGuiApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
