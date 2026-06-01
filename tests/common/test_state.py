"""Testes da persistência de estado vigia_common.state.

Puro (não precisa gi). Usa tmp_path real — chmod/replace funcionam em
Linux e macOS. Verifica round-trip, permissões 0600/0700, atomicidade
(sem .tmp órfão) e os caminhos de erro (ausente/corrompido -> default).
"""

from __future__ import annotations

import json
import stat

from vigia_common import state


class TestSaveJson0600:
    def test_round_trip(self, tmp_path):
        p = tmp_path / "sub" / "estado.json"
        assert state.save_json_0600(p, {"a": 1, "b": [2, 3]}) is True
        assert state.load_json(p) == {"a": 1, "b": [2, 3]}

    def test_arquivo_tem_modo_0600(self, tmp_path):
        p = tmp_path / "dir" / "s.json"
        state.save_json_0600(p, {"x": 1})
        mode = stat.S_IMODE(p.stat().st_mode)
        assert mode == 0o600, oct(mode)

    def test_diretorio_pai_tem_modo_0700(self, tmp_path):
        p = tmp_path / "segredos" / "s.json"
        state.save_json_0600(p, {"x": 1})
        mode = stat.S_IMODE(p.parent.stat().st_mode)
        assert mode == 0o700, oct(mode)

    def test_cria_diretorios_aninhados(self, tmp_path):
        p = tmp_path / "a" / "b" / "c" / "s.json"
        assert state.save_json_0600(p, {"ok": True}) is True
        assert p.exists()

    def test_atomico_nao_deixa_tmp_orfao(self, tmp_path):
        p = tmp_path / "s.json"
        state.save_json_0600(p, {"x": 1})
        leftovers = list(tmp_path.glob("*.tmp"))
        assert leftovers == []

    def test_sobrescreve_conteudo_anterior(self, tmp_path):
        p = tmp_path / "s.json"
        state.save_json_0600(p, {"v": 1})
        state.save_json_0600(p, {"v": 2})
        assert state.load_json(p) == {"v": 2}

    def test_nao_ascii_preservado(self, tmp_path):
        # ensure_ascii=False — acentos gravados como UTF-8, não \uXXXX.
        p = tmp_path / "s.json"
        state.save_json_0600(p, {"nome": "André", "obs": "ção"})
        raw = p.read_text(encoding="utf-8")
        assert "André" in raw
        assert "\\u" not in raw

    def test_indentado(self, tmp_path):
        p = tmp_path / "s.json"
        state.save_json_0600(p, {"a": 1})
        assert "\n" in p.read_text()

    def test_falha_de_io_retorna_false(self, tmp_path, monkeypatch):
        # Simula OSError no replace -> retorna False, não levanta.
        import os as _os

        def boom(*a, **k):
            raise OSError("disco cheio")

        monkeypatch.setattr(_os, "replace", boom)
        assert state.save_json_0600(tmp_path / "s.json", {"x": 1}) is False


class TestLoadJson:
    def test_ausente_retorna_default(self, tmp_path):
        assert state.load_json(tmp_path / "nao-existe.json", default={}) == {}

    def test_ausente_default_none(self, tmp_path):
        assert state.load_json(tmp_path / "nada.json") is None

    def test_corrompido_retorna_default(self, tmp_path):
        p = tmp_path / "ruim.json"
        p.write_text("{ isto não é json valido :::")
        assert state.load_json(p, default={"fallback": True}) == {"fallback": True}

    def test_le_json_existente(self, tmp_path):
        p = tmp_path / "ok.json"
        p.write_text(json.dumps({"k": "v"}))
        assert state.load_json(p) == {"k": "v"}
