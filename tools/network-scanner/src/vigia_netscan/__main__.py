"""Entry point: `python -m vigia_netscan` ou `vigia-netscan`."""

from __future__ import annotations

import sys

from .app import VigiaNetscanApp


def main() -> int:
    app = VigiaNetscanApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
