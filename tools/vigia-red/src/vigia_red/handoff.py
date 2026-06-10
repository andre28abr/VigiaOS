"""Passagem de alvo entre módulos do VigiaRed (ex.: Recon → Network Scanner).

Guarda um alvo "pendente" em memória (mesmo processo do app). O Recon grava um
IP/host descoberto; o Network Scanner, ao ser aberto, consome e pré-preenche o
campo de alvo. Não persiste em disco — é só um corredor entre as telas.
"""

from __future__ import annotations

_pending: str = ""


def set_scan_target(target: str) -> None:
    """Marca um alvo pra o Network Scanner pegar quando abrir."""
    global _pending
    _pending = (target or "").strip()


def take_scan_target() -> str:
    """Devolve e LIMPA o alvo pendente (consumo único)."""
    global _pending
    t, _pending = _pending, ""
    return t


def peek() -> str:
    """Espia o alvo pendente sem consumir (útil em teste)."""
    return _pending
