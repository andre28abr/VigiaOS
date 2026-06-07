"""Entry point: `vigia-red` — abre o VigiaOS na seção Red.

O ecossistema foi unificado: os 3 produtos (Hub/Red/Blue) vivem numa janela só,
o VigiaOS. `vigia-red` virou um atalho que abre o VigiaOS já na seção Red.
Se o VigiaOS (pacote vigia_hub) não estiver instalado, cai no VigiaRed
standalone via shell (fallback — preserva instalações isoladas do Red).
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from vigia_hub.__main__ import main as vigia_os_main
    except ImportError:
        # vigia_hub ausente — abre o VigiaRed standalone (casca do shell).
        from vigia_common.shell import run_product

        from .registry import CATEGORIES, META, MODULES, ORDER
        return run_product(META, MODULES, CATEGORIES, ORDER)
    return vigia_os_main(["vigia-os", "--section", "red"])


if __name__ == "__main__":
    sys.exit(main())
