"""Entry point: `python -m vigia_hash` ou `vigia-hash`."""

from __future__ import annotations

import sys

from .app import VigiaHashApp


def main() -> int:
    app = VigiaHashApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
