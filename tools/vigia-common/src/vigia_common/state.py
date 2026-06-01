"""Persistência de estado em JSON — escrita atômica com permissão 0600 (LGPD).

Os arquivos de estado das ferramentas podem guardar achados sensíveis (paths
infectados, deployments, hashes de baseline). Este módulo centraliza a
*mecânica de filesystem* que estava duplicada em vários backends — a parte
chata e propensa a erro (dir pai 0700, escrita atômica, chmod 0600):

- `save_json_0600(path, data)` — cria o diretório pai 0700, escreve num arquivo
  temporário, faz chmod 0600 e troca atomicamente (`os.replace`). Nunca levanta:
  erro de I/O retorna False (e loga).
- `load_json(path, default=None)` — lê e parseia; arquivo ausente ou corrompido
  retorna `default`.

A validação de SHAPE (isinstance, campos esperados) fica com quem chama: este
helper resolve só o I/O. Assume que o diretório pai é dedicado às Vigia
(será `chmod 0700`) — todos os chamadores usam subdirs próprios
(`~/.config/vigia-*`, `~/.local/share/vigia-*`), nunca `~/.config` direto.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def save_json_0600(path, data: Any) -> bool:
    """Salva `data` como JSON em `path`, atômico e com modo 0600.

    - Diretório pai criado (e `chmod 0700`) se preciso.
    - Escreve em `<path>.tmp`, `chmod 0600`, e `os.replace` (atômico no mesmo fs).
    - Retorna True em sucesso; False (com log) em `OSError`.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        return True
    except OSError as e:
        print(f"[state] save falhou ({path}): {e}", flush=True)
        return False


def load_json(path, default: Any = None) -> Any:
    """Lê e parseia JSON de `path`. Retorna `default` se ausente/corrompido."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default
