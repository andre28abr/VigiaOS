"""Vigia Capabilities Inspector — auditoria de Linux capabilities (getcap).

Linux capabilities sao permissoes granulares que substituem o tradicional
"tudo ou nada" do root. Esta tool audita quais binarios no sistema tem
capabilities elevadas — vetor classico de privilege escalation se um
binario inesperado tem cap_sys_admin, cap_setuid, etc.
"""

__version__ = "0.1.1"
__app_id__ = "br.com.vigia.CapabilitiesInspector"

WRAPPED_PACKAGES = ["libcap", "getcap"]
