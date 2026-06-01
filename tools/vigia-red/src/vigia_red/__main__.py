"""Entry point: `vigia-red` (ou `python -m vigia_red`)."""

from __future__ import annotations

import sys

from .registry import CATEGORIES, META, MODULES, ORDER


def main() -> int:
    from vigia_common.shell import run_product
    return run_product(META, MODULES, CATEGORIES, ORDER)


if __name__ == "__main__":
    sys.exit(main())
