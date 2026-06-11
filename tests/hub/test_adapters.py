"""Testes do adaptador Module → ToolEntry (vigia_hub.adapters).

Puro, sem GTK — roda em qualquer ambiente. Garante que os módulos do
VigiaBlue/VigiaRed são traduzidos corretamente para o master-detail do VigiaOS.
"""

from __future__ import annotations

from pathlib import Path

from vigia_common.shell import Dependency, Module

from vigia_hub.adapters import _NO_ICON_FILE, ModuleToolEntry, module_to_tool
from vigia_hub.registry import ToolEntry

# Binários: um que sempre existe no PATH e um que nunca existe.
_PRESENT_BIN = "sh"
_MISSING_BIN = "definitely-not-a-real-binary-xyzzy-9000"


def _mod(**kw) -> Module:
    """Module com defaults sensatos; sobrescreve com kwargs."""
    base = dict(id="siem", name="Vigia SIEM", category="detection",
                icon="view-list-symbolic", summary="resumo curto")
    base.update(kw)
    return Module(**base)


# --------------------------------------------------------------------------- #
# Identidade / namespacing
# --------------------------------------------------------------------------- #

def test_id_is_namespaced_by_section():
    assert module_to_tool(_mod(id="siem"), "blue").id == "blue:siem"
    assert module_to_tool(_mod(id="recon"), "red").id == "red:recon"


def test_returns_moduletoolentry_subclass():
    te = module_to_tool(_mod(), "blue")
    assert isinstance(te, ModuleToolEntry)
    assert isinstance(te, ToolEntry)  # é uma ToolEntry pro master-detail do Hub


# --------------------------------------------------------------------------- #
# Mapeamento de campos
# --------------------------------------------------------------------------- #

def test_field_mapping():
    mod = _mod(
        name="Vigia SIEM",
        summary="linha da sidebar",
        description="parágrafo do detalhe",
        features=["a", "b"],
        wraps=["vigia-log"],
        category="detection",
    )
    te = module_to_tool(mod, "blue")
    assert te.name == "Vigia SIEM"
    assert te.description == "linha da sidebar"        # summary → description
    assert te.long_description == "parágrafo do detalhe"  # description → long_description
    assert te.features == ["a", "b"]
    assert te.wrapped_packages == ["vigia-log"]
    assert te.category == "detection"
    assert te.exec_cmd == []                            # não abre via subprocess


def test_features_and_wraps_are_copies():
    mod = _mod(features=["x"], wraps=["y"])
    te = module_to_tool(mod, "blue")
    te.features.append("z")
    te.wrapped_packages.append("w")
    assert mod.features == ["x"]      # original (frozen list) intacto
    assert mod.wraps == ["y"]


# --------------------------------------------------------------------------- #
# Embed vs. placeholder (impl + status)
# --------------------------------------------------------------------------- #

def test_pronto_with_impl_is_embeddable():
    te = module_to_tool(_mod(status="pronto", impl="vigia_blue.modules.siem.page"),
                        "blue")
    assert te.embedded_module == "vigia_blue.modules.siem.page"
    assert te.is_planned is False
    assert te.widen_embedded is True
    assert te.status_label == "Pronto"


def test_planejado_without_impl_is_placeholder():
    te = module_to_tool(_mod(id="recon", status="planejado", impl=None), "red")
    assert te.embedded_module is None
    assert te.is_planned is True
    assert te.status_label == "Planejado"


def test_em_dev_without_pronto_is_placeholder():
    # status != "pronto" não embarca, mesmo com impl definido.
    te = module_to_tool(_mod(status="em-dev", impl="x.y.page"), "blue")
    assert te.embedded_module is None
    assert te.is_planned is True
    assert te.status_label == "Em desenvolvimento"


def test_blue_embeds_even_with_missing_dependency():
    # Diferente do Hub: um módulo "pronto" embarca mesmo com dep faltando —
    # a própria GUI do módulo mostra o aviso. is_embeddable ignora disponibilidade.
    dep = Dependency(label="YARA", checks=(_MISSING_BIN,))
    te = module_to_tool(
        _mod(status="pronto", impl="vigia_blue.modules.yara.page", requires=(dep,)),
        "blue")
    assert te.is_available() is False     # bolinha vermelha
    assert te.is_embeddable() is True     # mas embarca assim mesmo


# --------------------------------------------------------------------------- #
# Disponibilidade (bolinha verde/vermelha) ← requires
# --------------------------------------------------------------------------- #

def test_available_when_no_requires():
    te = module_to_tool(_mod(requires=()), "blue")
    assert te.is_available() is True


def test_available_when_all_deps_present():
    dep = Dependency(label="Shell", checks=(_PRESENT_BIN,))
    te = module_to_tool(_mod(requires=(dep,)), "blue")
    assert te.is_available() is True


def test_unavailable_when_a_dep_missing():
    dep_ok = Dependency(label="Shell", checks=(_PRESENT_BIN,))
    dep_no = Dependency(label="Faltante", checks=(_MISSING_BIN,))
    te = module_to_tool(_mod(requires=(dep_ok, dep_no)), "blue")
    assert te.is_available() is False


def test_dep_satisfied_if_any_check_present():
    # dep_installed = any(which(b) for b in checks)
    dep = Dependency(label="Multi", checks=(_MISSING_BIN, _PRESENT_BIN))
    te = module_to_tool(_mod(requires=(dep,)), "blue")
    assert te.is_available() is True


# --------------------------------------------------------------------------- #
# Ícone: nome-de-tema vs. arquivo SVG
# --------------------------------------------------------------------------- #

def test_theme_icon_name_when_not_a_file():
    te = module_to_tool(_mod(icon="system-search-symbolic"), "blue")
    assert te.theme_icon_name == "system-search-symbolic"
    # icon_path cai no sentinela e is_file() não levanta exceção
    assert te.icon_path == _NO_ICON_FILE
    assert te.icon_path.is_file() is False


def test_icon_path_when_svg_file_exists(tmp_path: Path):
    svg = tmp_path / "mod.svg"
    svg.write_text("<svg/>")
    te = module_to_tool(_mod(icon=str(svg)), "blue")
    assert te.icon_path == svg
    assert te.icon_path.is_file() is True
    assert te.theme_icon_name == ""


def test_empty_icon_is_safe():
    te = module_to_tool(_mod(icon=""), "blue")
    assert te.theme_icon_name == ""
    assert te.icon_path.is_file() is False


# --------------------------------------------------------------------------- #
# O ToolEntry "puro" do Hub não tem os campos extras — getattr-fallback do
# VigiaOS precisa funcionar (documenta o contrato usado no master-detail).
# --------------------------------------------------------------------------- #

def test_plain_toolentry_lacks_moduleonly_attrs():
    te = ToolEntry(id="dash", name="Dash", description="d",
                   icon_path=Path("/x"), exec_cmd=["vigia-dashboard"])
    # theme_icon_name virou campo legítimo de ToolEntry (default "") — usado
    # por built-ins (ex: checkup) e pelo fallback de ícone do adapter.
    assert te.theme_icon_name == ""
    # widen_embedded/is_planned seguem exclusivos da ModuleToolEntry (Blue/Red).
    assert getattr(te, "widen_embedded", False) is False
    assert getattr(te, "is_planned", False) is False


# --------------------------------------------------------------------------- #
# Integração: os registries REAIS do Blue/Red adaptam sem erro (o que a seção
# do VigiaOS faz em _build_blue_red_section).
# --------------------------------------------------------------------------- #

def test_adapts_real_blue_registry():
    from vigia_blue.registry import MODULES
    tools = [module_to_tool(m, "blue") for m in MODULES]
    assert len(tools) == len(MODULES)
    assert all(t.id.startswith("blue:") for t in tools)
    # VigiaBlue está completo: todos "pronto" → embarcáveis.
    assert all(t.embedded_module for t in tools)
    assert not any(t.is_planned for t in tools)


def test_adapts_real_red_registry():
    from vigia_red.registry import MODULES
    tools = [module_to_tool(m, "red") for m in MODULES]
    assert len(tools) == len(MODULES)
    assert all(t.id.startswith("red:") for t in tools)
    # Recon (OSINT), Network Scanner (nmap), Vuln Scanner (nuclei) e Web Scanner
    # (wapiti) são os módulos reais; o resto é esqueleto.
    real = {"red:recon", "red:netscan", "red:vuln", "red:web"}
    for t in tools:
        if t.id in real:
            assert not t.is_planned
            assert t.embedded_module
        else:
            assert t.is_planned
            assert not t.embedded_module
