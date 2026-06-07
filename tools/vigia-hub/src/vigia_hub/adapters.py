"""Adaptador Module → ToolEntry para o VigiaOS.

O VigiaOS (a janela do Hub) renderiza os módulos do VigiaBlue/VigiaRed usando o
MESMO master-detail das ferramentas do Hub. Os dois lados já compartilham o
contrato de embed (`build_content() -> Gtk.Widget`); só falta traduzir o
registro: o Hub usa `ToolEntry`, os produtos usam `Module`. Este módulo faz a
ponte — e é puro (sem GTK), testável headless.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from vigia_common.shell import STATUS_LABEL, Module, dep_installed

from .registry import ToolEntry

# Path sentinela que nunca existe → ToolEntry.icon_path.is_file() devolve False
# SEM levantar exceção (não usar "\0", que faria is_file() estourar ValueError).
# Quando o ícone do módulo é um nome-de-tema (não um arquivo .svg), o VigiaOS usa
# `theme_icon_name`; o icon_path fica nesse sentinela só pra satisfazer o tipo.
_NO_ICON_FILE = Path("/nonexistent/__vigia_no_icon__")


@dataclass
class ModuleToolEntry(ToolEntry):
    """`ToolEntry` adaptada a partir de um `Module` de produto (Blue/Red).

    Campos extras que o master-detail do VigiaOS consulta via ``getattr`` — assim
    o `ToolEntry` "puro" do Hub (que não os possui) segue funcionando sem
    qualquer alteração:

    - ``theme_icon_name``: nome de ícone do tema, quando o Module não traz um SVG.
    - ``widen_embedded``:  aplica ``widen_clamps()`` no widget embarcado (os
      módulos do Blue/Red foram feitos sob o shell, que alarga os clamps).
    - ``is_planned``:      módulo sem ``impl`` / ``status != "pronto"`` → cai na
      página de detalhe do Hub (sem tentar embarcar).
    - ``status_label``:    rótulo do status ("Planejado", "Pronto", …).
    """

    theme_icon_name: str = ""
    widen_embedded: bool = False
    is_planned: bool = False
    status_label: str = ""

    def is_embeddable(self) -> bool:
        """Blue/Red embarcam a GUI real sempre que têm ``impl`` — mesmo com a
        dependência externa faltando: a própria página do módulo exibe o aviso
        de instalação (a bolinha vermelha no rail sinaliza à parte). Difere do
        Hub, onde a tool só embarca se o backend estiver disponível
        (``ToolEntry.is_embeddable`` exige ``is_available``)."""
        return self.embedded_module is not None


def module_to_tool(mod: Module, section_key: str) -> ModuleToolEntry:
    """Converte um `Module` (Blue/Red) numa `ModuleToolEntry` renderizável pelo
    master-detail do VigiaOS.

    - **id namespaced** (``blue:siem``, ``red:recon``): não colide com ids do Hub
      nem entre produtos, e mantém únicos os nomes no Gtk.Stack de conteúdo.
    - **requires → available_fn** (bolinha verde/vermelha): pronto quando todas
      as dependências estão no PATH — mesma lógica do shell.
    - **impl + status "pronto" → embedded_module** (embarca a GUI real); senão
      ``is_planned=True`` (mostra a página "Planejado" do Hub).
    """
    icon = mod.icon or ""
    icon_is_file = icon.endswith(".svg") and os.path.isfile(icon)

    reqs = mod.requires

    def _available(_reqs: tuple = reqs) -> bool:
        return (not _reqs) or all(dep_installed(d) for d in _reqs)

    embeddable = bool(mod.impl) and mod.status == "pronto"

    return ModuleToolEntry(
        id=f"{section_key}:{mod.id}",
        name=mod.name,
        description=mod.summary,
        icon_path=Path(icon) if icon_is_file else _NO_ICON_FILE,
        exec_cmd=[],  # módulos Blue/Red não abrem via subprocess no VigiaOS
        long_description=mod.description,
        features=list(mod.features),
        available_fn=_available,
        embedded_module=mod.impl if embeddable else None,
        category=mod.category,
        wrapped_packages=list(mod.wraps),
        theme_icon_name="" if icon_is_file else icon,
        widen_embedded=True,
        is_planned=not embeddable,
        status_label=STATUS_LABEL.get(mod.status, mod.status),
    )
