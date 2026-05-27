"""Tab rkhunter (Rootkit Hunter) — scanner mais completo."""

from __future__ import annotations

from .. import backend
from ._scan_view import ScanView


DESCRIPTION = (
    "<b>Rootkit Hunter (rkhunter)</b> roda 200+ checks: rootkits conhecidos, "
    "backdoors, sniffers, exploits locais, integridade de binarios via "
    "hash comparison, permissoes suspeitas, configuracoes inseguras "
    "(SSH, login.defs), processos escondidos.\n\n"
    "Demora mais (2-5min) mas eh mais detalhado. Apos um <tt>rpm-ostree "
    "upgrade</tt>, hashes podem mudar — use o botao <i>Atualizar hashes</i> "
    "(em breve) ou rode <tt>rkhunter --propupd</tt> manualmente."
)


class RkhunterTab(ScanView):
    def __init__(self) -> None:
        super().__init__(
            scanner_name="rkhunter",
            scanner_label="Rootkit Hunter",
            description=DESCRIPTION,
            install_pkg="rkhunter",
            scan_starter=backend.scan_rkhunter_async,
            installed_checker=backend.rkhunter_installed,
        )
