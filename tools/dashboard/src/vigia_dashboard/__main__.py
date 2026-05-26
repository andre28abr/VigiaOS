"""Entry point: `python -m vigia_dashboard` ou `vigia-dashboard`."""

from __future__ import annotations

import sys

from .app import VigiaDashboardApp


def main() -> int:
    app = VigiaDashboardApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
