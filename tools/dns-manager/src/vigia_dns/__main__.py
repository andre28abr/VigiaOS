"""Entry point: `python -m vigia_dns` ou `vigia-dns`."""

from __future__ import annotations

import sys

from .app import VigiaDnsApp


def main() -> int:
    app = VigiaDnsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
