"""Entry point: `python -m vigia_caps` ou `vigia-caps`."""

from __future__ import annotations

import sys

from .app import VigiaCapsApp


def main() -> int:
    app = VigiaCapsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
