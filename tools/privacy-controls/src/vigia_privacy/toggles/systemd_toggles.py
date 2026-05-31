"""Toggles system-scope que controlam units systemd via pkexec.

Cada mudanca de estado chama 'pkexec systemctl enable/disable --now <unit>',
o que abre o dialogo grafico do polkit pedindo senha admin. Uma vez autenticado,
o systemd executa enable+start ou disable+stop atomicamente.

Read state nao precisa de privilegio (systemctl is-active sem sudo funciona).
"""

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
