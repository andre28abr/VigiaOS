"""Testes das dependências dos módulos: shell.Dependency + registry requires.

Cobre os helpers puros do shell (dep_installed/dep_command/product_dependencies)
e verifica que a registry do VigiaBlue declara as deps externas corretamente.
Tudo headless (a parte de dados do shell não importa GTK).
"""

from __future__ import annotations

import pytest

from vigia_common import shell
from vigia_common.shell import (
    Dependency,
    Module,
    dep_command,
    dep_installed,
    product_dependencies,
)


# ============================================================
# dep_installed
# ============================================================


def test_dep_installed_true(monkeypatch):
    monkeypatch.setattr(shell.shutil, "which",
                        lambda b: "/usr/bin/yara" if b == "yara" else None)
    assert dep_installed(Dependency("YARA", ("yara",), "rpm", "yara")) is True


def test_dep_installed_any_of(monkeypatch):
    # instalada se QUALQUER um dos binários existir
    monkeypatch.setattr(shell.shutil, "which",
                        lambda b: "/x" if b == "vol.py" else None)
    dep = Dependency("Vol", ("vol", "vol.py", "volatility3"), "pip", "volatility3")
    assert dep_installed(dep) is True


def test_dep_installed_false(monkeypatch):
    monkeypatch.setattr(shell.shutil, "which", lambda _b: None)
    assert dep_installed(Dependency("X", ("x",), "rpm", "x")) is False


# ============================================================
# dep_command
# ============================================================


def test_dep_command_pip():
    dep = Dependency("Vol", ("vol",), "pip", "volatility3")
    assert dep_command(dep) == "pipx install volatility3"


def test_dep_command_source_uses_literal():
    dep = Dependency("core", ("vigia-log",), "source", install="cargo build x")
    assert dep_command(dep) == "cargo build x"


def test_dep_command_rpm_uses_install_hint(monkeypatch):
    monkeypatch.setattr(shell, "install_hint",
                        lambda *p, **k: "sudo dnf install " + " ".join(p))
    dep = Dependency("YARA", ("yara",), "rpm", "yara")
    assert dep_command(dep) == "sudo dnf install yara"


# ============================================================
# product_dependencies
# ============================================================


def test_product_dependencies_dedupe_and_users():
    d = Dependency("X", ("x",), "rpm", "x")
    mods = [
        Module("a", "A", "c", "i", "s", requires=(d,)),
        Module("b", "B", "c", "i", "s", requires=(d,)),
        Module("c", "C", "c", "i", "s"),
    ]
    res = product_dependencies(mods)
    assert len(res) == 1
    dep, users = res[0]
    assert dep.label == "X" and sorted(users) == ["A", "B"]


def test_product_dependencies_empty():
    assert product_dependencies([Module("a", "A", "c", "i", "s")]) == []


# ============================================================
# Registry do VigiaBlue
# ============================================================


@pytest.fixture
def blue():
    from vigia_blue import registry
    return {m.id: m for m in registry.MODULES}


def test_blue_tool_modules_declare_requires(blue):
    assert blue["yara"].requires[0].checks == ("yara",)
    assert blue["yara"].requires[0].kind == "rpm"
    assert blue["ids"].requires[0].package == "suricata"
    assert blue["memory"].requires[0].kind == "pip"
    assert blue["timeline"].requires[0].kind == "pip"
    assert blue["siem"].requires[0].kind == "source"
    assert blue["siem"].requires[0].install   # comando literal de build


def test_blue_selfcontained_modules_have_no_requires(blue):
    assert blue["intel"].requires == ()
    assert blue["playbooks"].requires == ()


def test_blue_pronto_deps_have_install_command(blue):
    for m in blue.values():
        if m.status == "pronto":
            for dep in m.requires:
                assert dep_command(dep).strip()


# ============================================================
# install/_deps.py — "auto-ler registries" (fonte única p/ o vigia-setup.sh)
# ============================================================


def test_deps_helper_reads_registry():
    """O helper lê a registry e emite as deps do Blue (campos separados por \\x1f,
    preservando o `package` vazio das deps `source`)."""
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    res = subprocess.run(
        [sys.executable, str(repo / "install" / "_deps.py")],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    rows = [ln.split("\x1f") for ln in res.stdout.splitlines() if ln]
    assert rows and all(len(r) == 6 for r in rows)   # 6 campos por linha

    by_pkg = {r[4]: r for r in rows if r[4]}
    assert by_pkg["yara"][0] == "Blue" and by_pkg["yara"][3] == "rpm"
    assert by_pkg["suricata"][3] == "rpm"
    assert by_pkg["volatility3"][3] == "pip"
    assert by_pkg["plaso"][3] == "pip"

    kinds = {r[3] for r in rows}
    assert "source" in kinds                          # vigia-log (package vazio)
    assert all(r[0] != "Red" for r in rows)           # Red ainda sem deps
