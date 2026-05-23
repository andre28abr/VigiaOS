"""Entry point: `python -m vigia_integrity` ou `vigia-integrity`."""

from __future__ import annotations

import sys

from .app import VigiaIntegrityApp


def main() -> int:
    app = VigiaIntegrityApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
