"""Testes do esqueleto dos produtos (VigiaRed / VigiaBlue) — dados puros.

Exercita a casca compartilhada `vigia_common.shell` (Module / ProductMeta /
agrupamento) e os registries dos dois produtos. Tudo puro: o GTK só é
importado dentro de `run_product`, que não é chamado aqui — roda headless.
"""

from __future__ import annotations

import importlib

import pytest

from vigia_common import shell

PRODUCTS = ["vigia_red", "vigia_blue"]


@pytest.fixture(params=PRODUCTS)
def reg(request):
    return importlib.import_module(f"{request.param}.registry")


class TestShellPure:
    def test_modules_by_category_respects_order(self):
        mods = [
            shell.Module("a", "A", "x", "i", "s"),
            shell.Module("b", "B", "y", "i", "s"),
            shell.Module("c", "C", "x", "i", "s"),
        ]
        grouped = shell.modules_by_category(mods, ["y", "x"])
        assert list(grouped.keys()) == ["y", "x"]
        assert [m.id for m in grouped["x"]] == ["a", "c"]

    def test_count_by_status(self):
        mods = [
            shell.Module(str(i), "N", "c", "i", "s", status=st)
            for i, st in enumerate(["planejado", "planejado", "em-dev"])
        ]
        assert shell.count_by_status(mods) == {"planejado": 2, "em-dev": 1}

    def test_unknown_category_dropped(self):
        mods = [shell.Module("a", "A", "zzz", "i", "s")]
        assert shell.modules_by_category(mods, ["x"]) == {}


class TestRegistries:
    def test_meta_basico(self, reg):
        assert reg.META.name.startswith("Vigia")
        assert reg.META.app_id.startswith("br.com.vigia.")
        assert reg.META.version
        assert reg.META.accent.startswith("#")

    def test_modulos_nao_vazio(self, reg):
        assert len(reg.MODULES) >= 5

    def test_ids_unicos(self, reg):
        ids = [m.id for m in reg.MODULES]
        assert len(ids) == len(set(ids))

    def test_categoria_valida_e_na_ordem(self, reg):
        for m in reg.MODULES:
            assert m.category in reg.CATEGORIES, m.category
            assert m.category in reg.ORDER, m.category

    def test_order_cobre_categories(self, reg):
        assert set(reg.ORDER) == set(reg.CATEGORIES)

    def test_campos_preenchidos(self, reg):
        for m in reg.MODULES:
            assert m.name and m.icon and m.summary
            assert m.status in shell.STATUS_LABEL

    def test_agrupamento_cobre_todos(self, reg):
        grouped = shell.modules_by_category(reg.MODULES, reg.ORDER)
        total = sum(len(v) for v in grouped.values())
        assert total == len(reg.MODULES)
