"""Re-export de vigia_common.markdown para retro-compat.

A implementacao foi movida para `vigia_common.markdown` para ser
reusavel por outras tools. Codigo existente que faz
`from .markdown import md_to_pango` continua funcionando.

Tools novas devem importar direto:
    from vigia_common.markdown import md_to_pango
"""

from vigia_common.markdown import md_to_pango  # noqa: F401

try:
    from vigia_common.markdown import md_to_pango_block  # noqa: F401
except ImportError:  # vigia_common instalado e' antigo (sem a funcao nova)
    def md_to_pango_block(md: str) -> str:  # type: ignore[misc]
        """Fallback se o vigia-common carregado for antigo: faz ao menos o
        inline (negrito/italico/codigo). Rode `pip install -e` no vigia-common
        pro render completo de blocos. NUNCA deixa o import quebrar o app."""
        return md_to_pango(md or "")

__all__ = ["md_to_pango", "md_to_pango_block"]
