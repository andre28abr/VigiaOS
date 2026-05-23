"""Entry point: `python -m vigia_installer` ou `vigia-installer`."""

from __future__ import annotations

import sys

from .app import VigiaInstallerApp


def main() -> int:
    app = VigiaInstallerApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
