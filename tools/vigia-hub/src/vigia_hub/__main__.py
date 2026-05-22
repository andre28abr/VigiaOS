"""Entry point: `python -m vigia_hub` ou `vigia-hub` apos pip install."""

from __future__ import annotations

import sys

from .app import VigiaHubApp


def main() -> int:
    app = VigiaHubApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
