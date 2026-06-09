"""Conversor minimo de Markdown para Pango markup.

Suporta apenas os subsets que precisamos nos textos das tools Vigia:
  - **negrito**      -> <b>negrito</b>
  - *italico*        -> <i>italico</i>
  - `codigo`         -> <tt>codigo</tt>
  - Paragrafos separados por linha em branco sao preservados
    (Gtk.Label com wrap=True faz o resto).

`md_to_pango` (inline) NAO suporta: headers, listas, links, tabelas. Para
descricoes curtas, use widgets separados (PreferencesGroup, ActionRow, etc.).
Para DOCUMENTOS inteiros (manuais) sem WebKit, use `md_to_pango_block`, que
trata blocos (titulos, listas, citacoes, codigo, tabelas) num Gtk.Label.

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


# ----------------------------------------------------------------------------
# Renderizacao de DOCUMENTO inteiro (manuais) -> Pango markup
#
# md_to_pango (acima) so' trata inline. Os manuais usam blocos (titulos,
# listas, citacoes, codigo, tabelas). Quando o WebKit nao esta disponivel,
# o Hub cai num fallback que precisa mostrar markdown LEGIVEL — e' o que
# md_to_pango_block faz: 1 doc markdown -> 1 string Pango pra um Gtk.Label.
# ----------------------------------------------------------------------------

def _escape_xml(s: str) -> str:
    """Escapa os 3 caracteres especiais de XML/Pango."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Formatacao inline (negrito/italico/codigo/links) de UMA linha/paragrafo.

    Recebe texto CRU (escapa aqui). Sempre devolve Pango markup VALIDO:
    tags balanceadas, XML escapado. NAO trata `_italico_` de proposito —
    os manuais tecnicos sao cheios de `snake_case` e isso quebraria.
    """
    s = _escape_xml(text)

    # inline code -> placeholder (nao deve sofrer bold/italic dentro)
    codes: list[str] = []

    def _stash(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00C{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", _stash, s)
    # links [texto](url) -> texto (url)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1 (\2)", s)
    # negrito antes de italico (evita colisao ** vs *)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<i>\1</i>", s)
    for i, c in enumerate(codes):
        s = s.replace(f"\x00C{i}\x00", f"<tt>{c}</tt>")
    return s


def md_to_pango_block(md: str) -> str:
    """Converte um documento Markdown INTEIRO para um unico Pango markup,
    pronto pra um Gtk.Label (use_markup + wrap).

    Trata blocos: titulos (#/##/###), listas (-, *, +, 1.), citacoes (>),
    regua (---), blocos de codigo (```), tabelas (| | -> linhas) e
    paragrafos (linhas consecutivas viram um paragrafo so, separadas por
    linha em branco). Garante markup VALIDO (XML escapado, tags balanceadas).
    """
    if not md:
        return ""

    out: list[str] = []
    pending: tuple[str, str, list[str]] | None = None  # (tipo, prefixo, linhas)
    in_code = False

    def flush() -> None:
        nonlocal pending
        if pending:
            _kind, prefix, lines = pending
            out.append(prefix + _inline(" ".join(lines)))
            pending = None

    for raw in md.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        # bloco de codigo cercado por ```
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code:
            out.append(f"<tt>{_escape_xml(raw)}</tt>")
            continue

        # linha em branco -> fim de paragrafo
        if not stripped:
            flush()
            if out and out[-1] != "":
                out.append("")
            continue

        # regua horizontal
        if re.fullmatch(r"[-*_]{3,}", stripped):
            flush()
            out.append('<span foreground="#9aa0a6">────────────────</span>')
            continue

        # titulo (# ate ######)
        m = re.match(r"(#{1,6})\s+(.+)", stripped)
        if m:
            flush()
            if out and out[-1] != "":
                out.append("")
            size = {1: "x-large", 2: "large", 3: "medium"}.get(
                len(m.group(1)), "medium")
            out.append(
                f'<span size="{size}" weight="bold">{_inline(m.group(2))}</span>')
            continue

        # citacao
        if stripped.startswith(">"):
            flush()
            txt = _inline(stripped.lstrip(">").strip())
            out.append(f'<span foreground="#9aa0a6"><i>{txt}</i></span>')
            continue

        # lista com marcador (continuacoes indentadas entram no mesmo item)
        m = re.match(r"([-*+])\s+(.+)", stripped)
        if m:
            flush()
            indent = (len(line) - len(line.lstrip(" "))) // 2
            pending = ("li", f'{"    " * indent}•  ', [m.group(2)])
            continue

        # lista numerada
        m = re.match(r"(\d+)\.\s+(.+)", stripped)
        if m:
            flush()
            pending = ("li", f"{m.group(1)}.  ", [m.group(2)])
            continue

        # linha de tabela (degrada: vira "celula │ celula")
        if stripped.startswith("|") or " | " in stripped:
            if re.fullmatch(r"[\s|:\-]+", stripped):  # separadora |---|
                continue
            flush()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("  │  ".join(_inline(c) for c in cells))
            continue

        # texto comum: continua o bloco pendente (paragrafo OU item de lista)
        # ou inicia um paragrafo novo
        if pending is not None:
            pending[2].append(stripped)
        else:
            pending = ("p", "", [stripped])

    flush()
    markup = "\n".join(out)
    markup = re.sub(r"\n{3,}", "\n\n", markup).strip("\n")
    return markup
