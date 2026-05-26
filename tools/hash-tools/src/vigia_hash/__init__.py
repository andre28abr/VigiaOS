"""Vigia Hash Tools — calculo e verificacao de hashes com UI GTK4."""

__version__ = "0.1.1"
__app_id__ = "br.com.vigia.HashTools"

# Em v0.1 usamos hashlib do Python (stdlib). Sem deps externas.
# v0.2 vai adicionar hashdeep para paralelizar diretorios grandes —
# mas hashdeep foi removido dos repos do Fedora recente, entao em
# breve sera substituido por md5deep (que vem com hashdeep embutido)
# ou implementacao em Python puro com multiprocessing.
WRAPPED_PACKAGES = ["coreutils"]
