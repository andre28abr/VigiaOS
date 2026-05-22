"""Entry point: `python -m vigia_selinux` ou `vigia-selinux` apos pip install."""

from __future__ import annotations

import sys

from .app import VigiaSelinuxApp


def main() -> int:
    app = VigiaSelinuxApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
