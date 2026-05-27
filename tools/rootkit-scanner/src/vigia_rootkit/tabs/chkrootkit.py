"""Tab chkrootkit — scanner classico, rapido."""

from __future__ import annotations

from .. import backend
from ._scan_view import ScanView


DESCRIPTION = (
    "<b>chkrootkit</b> verifica binarios do sistema procurando assinaturas "
    "conhecidas de rootkits. Roda dezenas de checks (LKMs suspeitos, "
    "/proc inconsistencias, suspicious files em <tt>/dev</tt>, etc.). "
    "Rapido (~30s) e bom como primeiro pente-fino.\n\n"
    "Eh complementar ao <b>Rootkit Hunter</b> — rode os dois pra "
    "cobertura cruzada."
)


class ChkrootkitTab(ScanView):
    def __init__(self) -> None:
        super().__init__(
            scanner_name="chkrootkit",
            scanner_label="chkrootkit",
            description=DESCRIPTION,
            install_pkg="chkrootkit",
            scan_starter=backend.scan_chkrootkit_async,
            installed_checker=backend.chkrootkit_installed,
        )
