"""Testes do md_to_pango_block — conversor de manual (markdown -> Pango).

Usado no fallback da Ajuda quando o WebKit nao esta disponivel. O markup
gerado precisa ser SEMPRE valido (XML escapado, tags balanceadas) e legivel.
"""

from __future__ import annotations

from vigia_common.markdown import md_to_pango_block


def _balanced(markup: str) -> bool:
    """True se todas as tags Pango que emitimos estao balanceadas."""
    for tag in ("b", "i", "tt", "span"):
        if markup.count(f"<{tag}") != markup.count(f"</{tag}>"):
            return False
    return True


def test_empty_returns_empty():
    assert md_to_pango_block("") == ""
    assert md_to_pango_block(None) == ""  # type: ignore[arg-type]


def test_heading_levels_size_and_bold():
    out = md_to_pango_block("# Titulo\n## Sub\n### Menor")
    assert '<span size="x-large" weight="bold">Titulo</span>' in out
    assert '<span size="large" weight="bold">Sub</span>' in out
    assert '<span size="medium" weight="bold">Menor</span>' in out


def test_inline_bold_italic_code():
    out = md_to_pango_block("Tem **negrito**, *italico* e `codigo` aqui.")
    assert "<b>negrito</b>" in out
    assert "<i>italico</i>" in out
    assert "<tt>codigo</tt>" in out


def test_bullets_get_marker():
    out = md_to_pango_block("- um\n- dois")
    assert "•  um" in out
    assert "•  dois" in out


def test_numbered_list_preserved():
    out = md_to_pango_block("1. primeiro\n2. segundo")
    assert "1.  primeiro" in out
    assert "2.  segundo" in out


def test_blockquote_italic():
    out = md_to_pango_block("> uma dica importante")
    assert "<i>uma dica importante</i>" in out


def test_code_fence_is_monospace_no_bold():
    md = "```\nx = a ** b\n```"
    out = md_to_pango_block(md)
    assert "<tt>x = a ** b</tt>" in out
    # ** dentro de code NAO vira bold
    assert "<b>" not in out


def test_paragraph_lines_are_merged():
    # duas linhas consecutivas (soft-wrap do fonte) viram UM paragrafo
    out = md_to_pango_block("linha um\nlinha dois\n\noutro paragrafo")
    assert "linha um linha dois" in out
    assert "outro paragrafo" in out


def test_xml_is_escaped():
    out = md_to_pango_block("perigo <script>alert(1)</script> & cia")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "&amp;" in out


def test_snake_case_not_italicized():
    # underscores de snake_case NAO podem virar italico (quebraria tecnico)
    out = md_to_pango_block("Veja vigia_common_shell e dep_installed agora.")
    assert "<i>" not in out
    assert "vigia_common_shell" in out


def test_table_row_renders_cells_separator_skipped():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    out = md_to_pango_block(md)
    assert "A" in out and "B" in out
    assert "1" in out and "2" in out
    # a linha separadora |---|---| nao aparece
    assert "---" not in out


def test_horizontal_rule():
    out = md_to_pango_block("antes\n\n---\n\ndepois")
    assert "─" in out  # vira uma regua de box-drawing


def test_bullet_continuation_merges_into_item():
    # bullet cujo texto quebra em 2 linhas no fonte vira UM item so
    md = "- primeira parte e\n  continuacao do mesmo item\n- outro"
    out = md_to_pango_block(md)
    assert "•  primeira parte e continuacao do mesmo item" in out
    assert "•  outro" in out


def test_output_is_always_balanced_markup():
    sample = (
        "# Manual\n\nUm **negrito** e *ital* com `code`.\n\n"
        "- item <tag> com & especial\n- outro *com ital*\n\n"
        "> citacao **forte**\n\n## Fim\n"
    )
    out = md_to_pango_block(sample)
    assert _balanced(out)
    assert "<tag>" not in out  # escapado
