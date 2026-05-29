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
    description="Firewall padrão do Fedora. Quando OFF, todas as portas estão "
    "abertas para conexões recebidas. Mantenha ON em redes não-confiáveis.",
    category="Rede",
)

SSHD = systemd_unit_toggle(
    unit="sshd",
    name="Servidor SSH (sshd)",
    description="Permite conexões SSH ENTRANTES. Mantenha OFF se você não "
    "precisa que outros computadores se conectem ao seu via SSH.",
    category="Rede",
)

# ============================================================================
# Anonimizacao
# ============================================================================

TOR = systemd_unit_toggle(
    unit="tor",
    name="Serviço Tor",
    description="Roda o daemon Tor localmente (porta 9050). Apps podem usar "
    "como proxy SOCKS para anonimizar tráfego.",
    category="Anonimização",
    # tor pode ter unit instalada mas binary faltando em algumas distros;
    # checa que o binario realmente esta no PATH
    extra_available_check=lambda: shutil.which("tor") is not None,
)
