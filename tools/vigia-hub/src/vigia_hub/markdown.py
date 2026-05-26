"""Re-export de vigia_common.markdown para retro-compat.

A implementacao foi movida para `vigia_common.markdown` para ser
reusavel por outras tools. Codigo existente que faz
`from .markdown import md_to_pango` continua funcionando.

Tools novas devem importar direto:
    from vigia_common.markdown import md_to_pango
"""

from vigia_common.markdown import md_to_pango  # noqa: F401

__all__ = ["md_to_pango"]
