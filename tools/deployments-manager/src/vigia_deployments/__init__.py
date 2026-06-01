"""Vigia Deployments Manager — GUI pra rpm-ostree deployments.

v0.1.0: gerencia os "snapshots" que aparecem no GRUB boot menu.

Features:
- Lista todos os deployments (booted/rollback/staged/pinned)
- Rollback pro deployment anterior (pkexec)
- Pin/unpin (preserva deployment quando upgrade roda)
- Cleanup all (limpa pending + rollback + cached refs num pkexec)
- Labels customizados + notas multilinha (LGPD/audit)
- Alerta de /boot cheio
- Sobre tab com manual didatico
"""

__version__ = "0.1.2"
__app_id__ = "br.com.vigia.DeploymentsManager"

WRAPPED_PACKAGES = ["rpm-ostree"]
