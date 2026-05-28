"""Fuzz tests pros parsers de journal/JSON do Reports (Etapa E — hardening)."""

from __future__ import annotations

from vigia_reports import backend


class TestParseJsonLinesFuzz:
    def test_only_dicts_survive(self):
        text = "\n".join([
            '{"a": 1}',       # dict -> mantido
            "42",             # numero -> descartado
            "[1, 2, 3]",      # lista -> descartada
            '"uma string"',   # string -> descartada
            "nao e json",     # malformado -> descartado
            "",               # vazia
            "   ",            # so espaco
            '{"b": 2}',       # dict -> mantido
        ])
        out = backend._parse_json_lines(text)
        assert isinstance(out, list)
        assert all(isinstance(d, dict) for d in out)
        assert len(out) == 2

    def test_empty_text(self):
        assert backend._parse_json_lines("") == []


class TestJournalParsersFuzz:
    # raw sempre e' list[dict] na pratica (vem do _parse_json_lines).
    # Aqui jogamos listas malucas pra garantir robustez a elementos errados.
    WEIRD_LISTS = [
        [],
        [1, 2, 3],
        ["str", None, 3.14],
        [{}],
        [{"MESSAGE": 123}],            # MESSAGE nao-string
        [{"MESSAGE": None}],
        [{"__REALTIME_TIMESTAMP": "abc", "MESSAGE": "x"}],  # ts nao-numerico
        [None, {"MESSAGE": "y"}],
        "string-iteravel-de-chars",    # iteravel mas nao-dicts -> tudo pulado
    ]

    def test_all_parsers_never_crash(self):
        parsers = [
            backend._parse_ssh_journal,
            backend._parse_sudo_journal,
            backend._parse_fail2ban_journal,
            backend._parse_pkexec_journal,
        ]
        for fn in parsers:
            for w in self.WEIRD_LISTS:
                out = fn(w)
                assert isinstance(out, list), f"{fn.__name__} quebrou com {w!r}"

    def test_ssh_parses_valid(self):
        raw = [{"MESSAGE": "Accepted password for andre from 192.0.2.1 port 22 ssh2",
                "__REALTIME_TIMESTAMP": "1700000000000000"}]
        out = backend._parse_ssh_journal(raw)
        assert len(out) == 1
        assert out[0]["type"] == "ssh_accept"
        assert out[0]["user"] == "andre"
