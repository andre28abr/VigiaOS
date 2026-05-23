"""Entry point: `python -m vigia_hardening` ou `vigia-hardening` apos pip install."""

from __future__ import annotations

import sys

from .app import VigiaHardeningApp


def main() -> int:
    app = VigiaHardeningApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
