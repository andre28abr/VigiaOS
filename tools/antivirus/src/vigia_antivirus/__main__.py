"""Entry point: `python -m vigia_antivirus` ou `vigia-antivirus`."""

from __future__ import annotations

import sys

from .app import VigiaAntivirusApp


def main() -> int:
    app = VigiaAntivirusApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
