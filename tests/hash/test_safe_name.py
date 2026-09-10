"""hash_backend.safe_name — nomes com bytes fora do UTF-8 não estouram o JSON."""

from __future__ import annotations

import json

from vigia_integrity.hash_backend import safe_name


def test_nome_normal_intacto():
    assert safe_name("docs/relatório.pdf") == "docs/relatório.pdf"


def test_surrogate_vira_utf8_valido():
    raw = b"caf\xe9.pdf".decode("utf-8", "surrogateescape")  # como o FS entrega
    s = safe_name(raw)
    assert "\ufffd" in s
    json.dumps({s: "x"}, ensure_ascii=False).encode("utf-8")  # não levanta
