"""Entry point: `python -m vigia_firmware` ou `vigia-firmware`."""

from __future__ import annotations

import sys

from .app import VigiaFirmwareApp


def main() -> int:
    app = VigiaFirmwareApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
