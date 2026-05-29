"""Vigia Tool Installer — catalogo de security tools com 1-click rpm-ostree.

v0.2.0: nova aba Extensoes — recomendacoes FOSS pra navegador (uBlock
Origin, Privacy Badger, ClearURLs, LibRedirect, etc.). Detecta browsers
instalados (Firefox, Chrome, Brave, Chromium, Vivaldi, LibreWolf, ESR),
abre AMO/Web Store, mantem state local de marcacao, lock por categoria
(so 1 ad-blocker por browser).
"""

__version__ = "0.3.1"
__app_id__ = "br.com.vigia.ToolInstaller"

WRAPPED_PACKAGES = ["rpm-ostree", "xdg-open"]
