"""Vigia File Integrity — wrapper AIDE + hash ad-hoc.

v0.2.0: absorveu Hash Tools (mesma categoria: integridade de arquivos).

6 tabs:
- Status (AIDE)     — sistema completo, requer root
- Mudancas (AIDE)   — diff do ultimo check
- Hash              — calcula hash de arquivo
- Verificar         — compara hash esperado vs computado
- Baseline          — snapshot de diretorio + diff (sem root)
- Sobre

AIDE pra sistema-wide (`/etc`, `/usr`, `/boot`), hash ad-hoc pra
arquivos do usuario (downloads, documentos). Mesma logica de
'baseline + diff', escalas diferentes.
"""

__version__ = "0.2.1"
__app_id__ = "br.com.vigia.FileIntegrity"

WRAPPED_PACKAGES = ["aide", "coreutils"]
