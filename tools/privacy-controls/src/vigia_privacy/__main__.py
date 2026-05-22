"""Entry point: `python -m vigia_privacy` ou `vigia-privacy` (depois de pip install)."""

from __future__ import annotations

import sys

from .app import VigiaPrivacyApp


def main() -> int:
    app = VigiaPrivacyApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
