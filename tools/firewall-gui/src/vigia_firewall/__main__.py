"""Entry point: `python -m vigia_firewall` ou `vigia-firewall` apos pip install."""

from __future__ import annotations

import sys

from .app import VigiaFirewallApp


def main() -> int:
    app = VigiaFirewallApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
