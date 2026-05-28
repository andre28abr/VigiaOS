"""Fuzz tests pros parsers JSON do Deployments Manager (Etapa E — hardening).

Objetivo: garantir que JSON corrompido OU valido-mas-de-formato-errado
(ex: lista no topo, campos com tipo trocado) NUNCA derruba o programa —
sempre cai num padrao seguro.
"""

from __future__ import annotations

from vigia_deployments import backend, state

# Bateria de payloads "malucos": malformados + JSON valido de formato errado.
FUZZ_JSON = [
    "",                                       # arquivo vazio
    "   ",                                     # so espacos
    "not json at all {{{",                    # lixo
    "{",                                       # truncado
    "null",                                    # JSON null
    "42",                                      # numero no topo
    "3.14",                                    # float
    '"uma string"',                           # string no topo
    "true",                                    # bool
    "[]",                                      # lista vazia
    "[1, 2, 3]",                              # lista de numeros
    '[{"x": 1}, "y", null]',                  # lista mista
    "{}",                                      # dict vazio
    '{"chave": "inesperada"}',                # dict sem as chaves certas
    '{"deployments": "nao-e-lista"}',         # campo com tipo errado
    '{"deployments": [1, 2, "x", null]}',     # lista de nao-dicts
    '{"deployments": [{"timestamp": "abc"}]}',  # campo numerico como string
    '{"deployments": [{"checksum": 123, "requested-packages": 5}]}',  # tipos trocados
    '{"a": {"b": {"c": [1, {"d": null}]}}}',  # aninhado profundo
]


class TestGetDeploymentsFuzz:
    def test_never_crashes_returns_list(self, monkeypatch):
        monkeypatch.setattr(backend, "rpmostree_available", lambda: True)
        for payload in FUZZ_JSON:
            monkeypatch.setattr(
                backend, "_run", lambda cmd, timeout=30, _p=payload: (0, _p, "")
            )
            out = backend.get_deployments()
            assert isinstance(out, list), f"payload quebrou: {payload!r}"

    def test_valid_deployment_still_parses(self, monkeypatch):
        """Sanidade: JSON bem-formado continua sendo parseado."""
        good = '{"deployments": [{"checksum": "abc123def", "booted": true, "osname": "fedora"}]}'
        monkeypatch.setattr(backend, "rpmostree_available", lambda: True)
        monkeypatch.setattr(backend, "_run", lambda cmd, timeout=30: (0, good, ""))
        out = backend.get_deployments()
        assert len(out) == 1
        assert out[0].osname == "fedora"
        assert out[0].booted is True


class TestStateLoadFuzz:
    def test_never_crashes_returns_state(self, tmp_path, monkeypatch):
        p = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", p)
        for payload in FUZZ_JSON:
            p.write_text(payload, encoding="utf-8")
            st = state._load()
            assert isinstance(st.labels, dict), f"labels quebrou: {payload!r}"
            assert isinstance(st.notes, dict), f"notes quebrou: {payload!r}"

    def test_wrong_inner_types_coerced(self, tmp_path, monkeypatch):
        p = tmp_path / "state.json"
        monkeypatch.setattr(state, "STATE_PATH", p)
        p.write_text('{"labels": "nao-dict", "notes": [1, 2]}', encoding="utf-8")
        st = state._load()
        assert st.labels == {}
        assert st.notes == {}
