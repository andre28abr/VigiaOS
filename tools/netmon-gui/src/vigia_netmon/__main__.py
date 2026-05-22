"""Entry point: `python -m vigia_netmon` ou `vigia-netmon` apos pip install."""

from __future__ import annotations

import sys

from .app import VigiaNetmonApp


def main() -> int:
    app = VigiaNetmonApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
