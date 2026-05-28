"""Fuzz tests pro parser de bundle do Activity Log GUI (Etapa E — hardening).

`_parse_bundle` recebe o JSON ja decodificado do `vigia-log`. Garante que
qualquer formato inesperado nao derruba a UI.
"""

from __future__ import annotations

from vigia_log_gui import backend


class TestParseBundleFuzz:
    def test_never_crashes(self):
        weird = [
            None, 42, 3.14, "string", True, [], [1, 2, 3], {},
            {"version": "abc"},                       # version nao-numerico
            {"sources": "nao-lista"},
            {"events": "nao-lista"},
            {"events": [1, 2, None]},                 # eventos nao-dict
            {"events": [{"timestamp": 123, "payload": "nao-dict"}]},
            {"correlations": "x"},
            {"correlations": [None, 1, "y"]},
            {"correlations": [{"contributing_count": "NaN"}]},
            {"events": [{}], "correlations": [{}]},    # dicts vazios
        ]
        for w in weird:
            b = backend._parse_bundle(w)
            assert b is not None, f"quebrou com: {w!r}"
            assert isinstance(b.events, list)
            assert isinstance(b.correlations, list)
            assert isinstance(b.sources, list)
            assert isinstance(b.version, int)

    def test_valid_bundle_parsed(self):
        data = {
            "version": 1,
            "generated_at": "2026-05-28",
            "sources": ["ssh"],
            "events": [{"timestamp": "t", "source": "ssh", "narrative": "login"}],
            "correlations": [{"kind": "brute", "contributing_count": 3}],
        }
        b = backend._parse_bundle(data)
        assert b.version == 1
        assert len(b.events) == 1
        assert b.events[0].narrative == "login"
        assert b.correlations[0].contributing_count == 3


class TestSafeInt:
    def test_coercions(self):
        assert backend._safe_int("5") == 5
        assert backend._safe_int(7) == 7
        assert backend._safe_int(3.9) == 3
        assert backend._safe_int("abc") == 0
        assert backend._safe_int(None) == 0
        assert backend._safe_int([], default=99) == 99
        assert backend._safe_int({"a": 1}, default=-1) == -1
