"""Vigia Dashboard — sistema em tempo real (CPU, RAM, disco, rede, processos)."""

__version__ = "0.4.2"
__app_id__ = "br.com.vigia.Dashboard"

# Sem deps externas — usa /proc do kernel.
WRAPPED_PACKAGES = ["procfs", "strace", "nethogs"]


# Cores semanticas para os graficos (multi-cor — feedback do user)
COLOR_CPU = (0.20, 0.83, 0.60)    # emerald-400 (#34d399)
COLOR_RAM = (0.98, 0.75, 0.14)    # amber-400 (#fbbf24)
COLOR_DISK = (0.13, 0.83, 0.93)   # cyan-400 (#22d3ee)
COLOR_NET = (0.65, 0.55, 0.98)    # violet-400 (#a78bfa)

# Cores de severidade
COLOR_OK = (0.20, 0.83, 0.60)     # emerald
COLOR_WARN = (0.98, 0.75, 0.14)   # amber
COLOR_ERR = (0.97, 0.44, 0.44)    # red-400 (#f87171)
COLOR_DIM = (0.55, 0.55, 0.58)    # zinc-500
