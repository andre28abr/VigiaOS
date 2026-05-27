"""Entry point: `python -m vigia_rootkit` ou `vigia-rootkit`."""

from __future__ import annotations

import sys

from .app import VigiaRootkitApp


def main() -> int:
    app = VigiaRootkitApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
