"""Testes para vigia_common.markdown.md_to_pango.

md_to_pango converte markdown leve (**bold**, *italic*, `code`) para
Pango markup. Eh usado em todos os textos longos das tabs Sobre,
descricoes do Hub, etc.
"""

from __future__ import annotations

import pytest

from vigia_common.markdown import md_to_pango


class TestEscaping:
    """Caracteres XML especiais devem ser escapados ANTES do parsing."""

    def test_amp_escaped(self):
        assert md_to_pango("a & b") == "a &amp; b"

    def test_lt_escaped(self):
        assert md_to_pango("a < b") == "a &lt; b"

    def test_gt_escaped(self):
        assert md_to_pango("a > b") == "a &gt; b"

    def test_multiple_specials(self):
        assert md_to_pango("&<>") == "&amp;&lt;&gt;"

    def test_escape_does_not_break_bold(self):
        # & antes de **bold** nao deve atrapalhar o bold
        result = md_to_pango("A & **B** C")
        assert result == "A &amp; <b>B</b> C"


class TestBold:
    def test_simple(self):
        assert md_to_pango("**hello**") == "<b>hello</b>"

    def test_in_sentence(self):
        assert md_to_pango("foo **bar** baz") == "foo <b>bar</b> baz"

    def test_multiple(self):
        result = md_to_pango("**a** and **b**")
        assert result == "<b>a</b> and <b>b</b>"

    def test_bold_with_special_chars_inside(self):
        # XML escape acontece ANTES do bold parse, entao &lt; ja virou &lt;
        result = md_to_pango("**a<b>**")
        # Apos escape: '**a&lt;b&gt;**' → <b>a&lt;b&gt;</b>
        assert result == "<b>a&lt;b&gt;</b>"

    def test_bold_does_not_match_single_asterisk(self):
        # Single * nao deve virar bold
        assert md_to_pango("*foo*") == "<i>foo</i>"


class TestItalic:
    def test_simple(self):
        assert md_to_pango("*hello*") == "<i>hello</i>"

    def test_in_sentence(self):
        assert md_to_pango("foo *bar* baz") == "foo <i>bar</i> baz"

    def test_italic_not_inside_bold(self):
        # LIMITACAO conhecida: **a*b*c** nao casa com bold inteiro porque
        # regex bold exige [^*]+ entre os **. Italic entao pega *b*.
        # Resultado documentado: '**a<i>b</i>c**'.
        # Workaround pro usuario: nao misturar bold com italic dentro.
        result = md_to_pango("**a*b*c**")
        assert result == "**a<i>b</i>c**"

    def test_italic_does_not_cross_newline(self):
        # *foo\nbar* nao deve virar italic (regex tem [^*\n])
        result = md_to_pango("*foo\nbar*")
        # Nao deve ter <i> em volta
        assert result == "*foo\nbar*"


class TestCode:
    def test_simple(self):
        assert md_to_pango("`code`") == "<tt>code</tt>"

    def test_in_sentence(self):
        assert md_to_pango("use `ls -la` here") == "use <tt>ls -la</tt> here"

    def test_code_with_asterisks_preserved(self):
        # ** ou * dentro de `code` NAO devem virar bold/italic
        # (code e' processado primeiro)
        result = md_to_pango("`**not bold**`")
        assert result == "<tt>**not bold**</tt>"

    def test_code_with_special_chars(self):
        # < dentro de code — deve ser escapado
        result = md_to_pango("`a<b`")
        assert result == "<tt>a&lt;b</tt>"


class TestEdgeCases:
    def test_empty_string(self):
        assert md_to_pango("") == ""

    def test_none_returns_empty(self):
        # Comportamento documentado: None → ""
        assert md_to_pango(None) == ""  # type: ignore[arg-type]

    def test_plain_text(self):
        assert md_to_pango("hello world") == "hello world"

    def test_multiline(self):
        result = md_to_pango("line 1\nline 2")
        assert result == "line 1\nline 2"

    def test_combined_styles(self):
        # **bold** + *italic* + `code` numa string
        result = md_to_pango("**B** and *I* and `C`")
        assert result == "<b>B</b> and <i>I</i> and <tt>C</tt>"


class TestRealWorldStrings:
    """Strings reais usadas no projeto, para garantir nao regressao."""

    def test_hub_description(self):
        # Inspirado nas descricoes do registry.py do Hub
        md = (
            "Frontend **GTK4** do `vigia-log` (parser Rust). Consolida "
            "`audit.log`, `systemd journal` e `fail2ban.log` numa "
            "**unica linha do tempo**."
        )
        result = md_to_pango(md)
        # Verifica que bold e code estao todos presentes
        assert "<b>GTK4</b>" in result
        assert "<tt>vigia-log</tt>" in result
        assert "<tt>audit.log</tt>" in result
        assert "<b>unica linha do tempo</b>" in result

    def test_dashboard_about_section(self):
        # Inspirado em tabs/about.py do Dashboard
        md = (
            "Dashboard de sistema em tempo real. Mostra **CPU**, "
            "**memoria**, **disco I/O**, **rede** e **processos** "
            "com graficos visuais."
        )
        result = md_to_pango(md)
        # 5 bolds esperados
        assert result.count("<b>") == 5
        assert result.count("</b>") == 5
