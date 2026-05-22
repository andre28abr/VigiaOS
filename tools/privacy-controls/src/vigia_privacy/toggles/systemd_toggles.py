"""Toggles system-scope que controlam units systemd via pkexec.

Cada mudanca de estado chama 'pkexec systemctl enable/disable --now <unit>',
o que abre o dialogo grafico do polkit pedindo senha admin. Uma vez autenticado,
o systemd executa enable+start ou disable+stop atomicamente.

Read state nao precisa de privilegio (systemctl is-active sem sudo funciona).
"""

import shutil

from .base import systemd_unit_toggle

# ============================================================================
# Rede
# ============================================================================

FIREWALLD = systemd_unit_toggle(
    unit="firewalld",
    name="Firewall (firewalld)",
    description="Firewall padrao do Fedora. Quando OFF, todas as portas estao "
    "abertas para conexoes recebidas. Mantenha ON em redes nao-confiaveis.",
    category="Rede",
)

SSHD = systemd_unit_toggle(
    unit="sshd",
    name="Servidor SSH (sshd)",
    description="Permite conexoes SSH ENTRANTES. Mantenha OFF se voce nao "
    "precisa que outros computadores se conectem ao seu via SSH.",
    category="Rede",
)

# ============================================================================
# Anonimizacao
# ============================================================================

TOR = systemd_unit_toggle(
    unit="tor",
    name="Servico Tor",
    description="Roda o daemon Tor localmente (porta 9050). Apps podem usar "
    "como proxy SOCKS para anonimizar trafego.",
    category="Anonimizacao",
    # tor pode ter unit instalada mas binary faltando em algumas distros;
    # checa que o binario realmente esta no PATH
    extra_available_check=lambda: shutil.which("tor") is not None,
)
