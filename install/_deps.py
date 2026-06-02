#!/usr/bin/env python3
"""Lê as registries dos produtos do shell (VigiaBlue / VigiaRed) e emite as
dependências externas declaradas (``Module.requires``) em TSV, para o instalador
guiado (``install/vigia-setup.sh``) montar a tabela e a lista de instalação a
partir da **fonte única de verdade** (o código) — sem duplicar pacote à mão.

Saída — uma linha por dependência, campos separados por ``\x1f`` (US — não é
*whitespace*, então o ``read`` do bash preserva campos vazios como o ``package``
de uma dep ``source``):

    PRODUTO<US>MODULO<US>LABEL<US>KIND<US>PACKAGE<US>CHECKS_CSV

onde ``PRODUTO ∈ {Blue, Red}`` e ``KIND ∈ {rpm, pip, source}``.

É puro: importa só a parte de dados do shell (não abre GTK). Se um produto não
importar (ex.: ainda sem módulos com deps), é ignorado silenciosamente — então
um módulo novo do Red com ``requires`` aparece aqui automaticamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for _p in ("vigia-common", "vigia-blue", "vigia-red"):
    sys.path.insert(0, str(_REPO / "tools" / _p / "src"))

# (rótulo do produto, módulo Python da registry)
_PRODUCTS = [("Blue", "vigia_blue.registry"), ("Red", "vigia_red.registry")]


def main() -> None:
    seen: set[tuple[str, str, str]] = set()
    for product, modname in _PRODUCTS:
        try:
            registry = __import__(modname, fromlist=["MODULES"])
        except Exception:  # noqa: BLE001 — produto sem registry/deps é só ignorado
            continue
        for mod in getattr(registry, "MODULES", []):
            for dep in getattr(mod, "requires", ()) or ():
                key = (dep.kind, dep.package, dep.label)
                if key in seen:
                    continue
                seen.add(key)
                checks = ",".join(getattr(dep, "checks", ()) or ())
                print("\x1f".join((product, mod.name, dep.label, dep.kind,
                                   dep.package or "", checks)))


if __name__ == "__main__":
    main()
