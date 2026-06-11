"""Augmenta o `PATH` com diretórios de binários instalados pelo usuário.

**Por quê:** um app aberto pelo menu do GNOME herda um `PATH` enxuto e
costuma **não** incluir os diretórios onde ferramentas instaladas pelo usuário
caem:

- `~/.local/bin`  — `pipx` (theHarvester, wapiti)
- `~/go/bin`      — `go install` (**nuclei**)
- `~/.cargo/bin`  — `cargo` (ferramentas Rust)
- `/usr/local/bin`— instalações manuais
- `$GOPATH/bin`   — se `GOPATH` estiver definido

Sem isso, `shutil.which("nuclei")` falha **mesmo com o nuclei instalado**, e o
módulo aparece como "não instalado" (botão desabilitado → "nada acontece").

`ensure_user_bins_on_path()` é chamado 1× no startup do app (`do_activate`).
Como tudo roda no MESMO processo (módulos embarcados), augmentar o
`os.environ["PATH"]` aqui faz o `shutil.which` e os `subprocess` de TODOS os
módulos enxergarem essas ferramentas.

As funções de cálculo são puras (FS injetável) — testáveis sem tocar o disco.
"""

from __future__ import annotations

import os


def candidate_bin_dirs(home: str, environ: dict | None = None) -> list[str]:
    """Diretórios candidatos, em ordem estável, SEM checar se existem (puro)."""
    h = (home or "").rstrip("/")
    cands = [
        f"{h}/.local/bin",
        f"{h}/go/bin",
        f"{h}/.cargo/bin",
        "/usr/local/bin",
    ]
    gopath = (environ or {}).get("GOPATH")
    if gopath:
        cands.append(f"{gopath.rstrip('/')}/bin")
    return cands


def augmented_path(current: str, extra: list[str], *, exists=os.path.isdir) -> str:
    """Acrescenta ao FINAL do PATH os `extra` que existem e ainda não estão lá.

    Puro (FS injetável via `exists`). Mantém ordem; o sistema tem **precedência**
    (extras vão pro fim). Idempotente: rodar de novo não duplica nada.
    """
    parts = [p for p in (current or "").split(os.pathsep) if p]
    seen = set(parts)
    for d in extra:
        if d and d not in seen and exists(d):
            parts.append(d)
            seen.add(d)
    return os.pathsep.join(parts)


def ensure_user_bins_on_path() -> None:
    """Aplica `augmented_path` ao `os.environ['PATH']`. Idempotente; chamar no startup."""
    home = os.path.expanduser("~")
    extra = candidate_bin_dirs(home, os.environ)
    os.environ["PATH"] = augmented_path(os.environ.get("PATH", ""), extra)
