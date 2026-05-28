"""Entry point: `python -m vigia_deployments` ou `vigia-deployments`."""

from __future__ import annotations

import sys

from .app import VigiaDeploymentsApp


def main() -> int:
    app = VigiaDeploymentsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
