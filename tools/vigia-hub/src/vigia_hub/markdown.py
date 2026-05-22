"""Conversor minimo de Markdown para Pango markup.

Suporta apenas os subsets que precisamos nos textos do Hub:
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
    """Converte markdown leve para Pango markup. Escapa XML primeiro."""
    if not md:
        return ""

    # 1. Escapa caracteres XML especiais. Faz isso ANTES de inserir nossos
    #    tags <b>/<i>/<tt> (que sao os unicos que devem permanecer literais).
    s = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 2. Inline code (com backticks). Faz antes de bold/italic porque
    #    podemos ter ** ou * dentro de codigo, e nao queremos formatar.
    s = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", s)

    # 3. Bold (**texto**). Faz antes de italic (que usa *) para nao colidir.
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)

    # 4. Italic (*texto*) — exige nao-* antes e depois para evitar conflito
    #    com o ** ja' processado.
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)

    return s
