"""Entry point: `python -m vigia_reports` ou `vigia-reports`."""

from __future__ import annotations

import sys

from .app import VigiaReportsApp


def main() -> int:
    app = VigiaReportsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
