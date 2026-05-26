"""Conversor minimo de Markdown para Pango markup.

Suporta apenas os subsets que precisamos nos textos das tools Vigia:
  - **negrito**      -> <b>negrito</b>
  - *italico*        -> <i>italico</i>
  - `codigo`         -> <tt>codigo</tt>
  - Paragrafos separados por linha em branco sao preservados
    (Gtk.Label com wrap=True faz o resto).

Nao suportamos: headers, listas com -/*, links, tabelas, etc. Para esses
casos, use widgets separados (PreferencesGroup, ActionRow, etc.).

Pango docs: https://docs.gtk.org/Pango/pango_markup.html
"""

from __future__ import annotations

import re


def md_to_pango(md: str) -> str:
    """Converte markdown leve para Pango markup. Escapa XML primeiro.

    Bug fix (rev. 2): code blocks com ** ou * dentro nao devem virar
    bold/italic. Solucao: substitui code por placeholders antes de
    processar bold/italic, e restaura no final.
    """
    if not md:
        return ""

    # 1. Escapa caracteres XML especiais. Faz isso ANTES de inserir nossos
    #    tags <b>/<i>/<tt> (que sao os unicos que devem permanecer literais).
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 2. Inline code (com backticks). Substituido por placeholder
    #    \x00CODE<n>\x00 para que o conteudo nao seja afetado por
    #    bold/italic regex.
    code_blocks: list[str] = []

    def _code_repl(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CODE{len(code_blocks) - 1}\x00"

    s = re.sub(r"`([^`]+)`", _code_repl, s)

    # 3. Bold (**texto**). Faz antes de italic (que usa *) para nao colidir.
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

    # 4. Italic (*texto*) — exige nao-* antes e depois para evitar conflito
    #    com o ** ja' processado.
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)

    # 5. Restaura code blocks como <tt>...</tt>
    for i, content in enumerate(code_blocks):
        s = s.replace(f"\x00CODE{i}\x00", f"<tt>{content}</tt>")

    return s
