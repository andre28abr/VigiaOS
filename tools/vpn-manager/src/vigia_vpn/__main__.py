"""Entry point: `python -m vigia_vpn` ou `vigia-vpn`."""

from __future__ import annotations

import sys

from .app import VigiaVpnApp


def main() -> int:
    app = VigiaVpnApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
