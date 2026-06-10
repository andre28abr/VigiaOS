"""Termo de uso do VigiaRed (Lei 12.737/2012).

O VigiaRed é uma suíte ofensiva (pentest). Por exigência legal e ética, nenhum
módulo deve rodar sem o usuário **aceitar explicitamente** que só vai usar contra
sistemas próprios ou com autorização formal por escrito.

O aceite é gravado UMA vez (0600) e destrava os módulos do Red. Puro o suficiente
pra testar: o caminho do arquivo é um atributo de módulo (pode ser trocado em teste).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from vigia_common.state import load_json, save_json_0600

# ~/.config/vigia-red/consent.json (0600)
CONSENT_FILE = Path.home() / ".config" / "vigia-red" / "consent.json"

LAW = "Lei 12.737/2012"


def is_accepted() -> bool:
    """True se o usuário já aceitou o termo de uso do VigiaRed."""
    data = load_json(CONSENT_FILE)
    return isinstance(data, dict) and bool(data.get("accepted"))


def accept() -> bool:
    """Grava o aceite (0600). Retorna True se salvou."""
    return save_json_0600(
        CONSENT_FILE,
        {
            "accepted": True,
            "accepted_at": datetime.now().isoformat(timespec="seconds"),
            "law": LAW,
        },
    )


def revoke() -> bool:
    """Revoga o aceite (volta a exibir o termo)."""
    return save_json_0600(CONSENT_FILE, {"accepted": False})
