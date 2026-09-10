"""Manuais dos produtos Red/Blue — helper puro + cobertura.

Os manuais de módulo vivem em `docs/manuals/<kind>/<produto>-<módulo>.md`
(mesma pasta dos manuais do Hub), lidos tanto pela aba Ajuda do VigiaOS
(`vigia_hub.manuals.MANUAL_ENTRIES`) quanto pela casca standalone
(`vigia_common.shell.find_product_manual`). Puro: sem GTK.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vigia_common import shell

REPO = Path(__file__).resolve().parents[2]
MANUALS = REPO / "docs" / "manuals"


class TestFindProductManual:
    def test_acha_arquivo_na_convencao(self, tmp_path):
        (tmp_path / "leigo").mkdir()
        f = tmp_path / "leigo" / "blue-yara.md"
        f.write_text("# YARA\n")
        assert shell.find_product_manual("blue", "yara", "leigo", dirs=[tmp_path]) == f

    def test_none_quando_nao_existe(self, tmp_path):
        assert shell.find_product_manual("red", "xyz", "tecnico", dirs=[tmp_path]) is None

    def test_primeiro_diretorio_vence(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        for d in (a, b):
            (d / "tecnico").mkdir(parents=True)
            (d / "tecnico" / "red-recon.md").write_text(d.name)
        assert shell.find_product_manual("red", "recon", "tecnico", dirs=[a, b]) == a / "tecnico" / "red-recon.md"

    def test_load_devolve_placeholder_sem_arquivo(self, monkeypatch):
        monkeypatch.setattr(shell, "manual_dirs", lambda: [])
        txt = shell.load_product_manual("blue", "nada", "leigo")
        assert "em preparação" in txt and "blue-nada.md" in txt

    def test_manual_dirs_inclui_repo_em_modo_dev(self):
        assert MANUALS in shell.manual_dirs()


def _ready_modules(product):
    if product == "blue":
        from vigia_blue.registry import MODULES
    else:
        from vigia_red.registry import MODULES
    return [m for m in MODULES if m.status == "pronto"]


@pytest.mark.parametrize("product", ["blue", "red"])
@pytest.mark.parametrize("kind", ["leigo", "tecnico"])
def test_todo_modulo_pronto_tem_manual(product, kind):
    faltando = [m.id for m in _ready_modules(product)
                if shell.find_product_manual(product, m.id, kind, dirs=[MANUALS]) is None]
    assert not faltando, f"sem manual {kind}: {faltando}"


def test_sumario_do_hub_aponta_para_arquivos_existentes():
    from vigia_hub.manuals import MANUAL_ENTRIES
    faltando = [e.tool_id for e in MANUAL_ENTRIES
                if not (MANUALS / "tecnico" / f"{e.tool_id}.md").is_file()
                or not (MANUALS / "leigo" / f"{e.tool_id}.md").is_file()]
    assert not faltando, f"entradas do sumário sem .md: {faltando}"
