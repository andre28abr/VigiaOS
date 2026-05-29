"""Catalogo das ~40 Linux capabilities com descricao pt-BR e classe de risco.

Referencia: capabilities(7) man page.

Classificacao de risco e' opiniao informada por uso real em exploits:
- ALTO   : permite efetivamente bypass do modelo de seguranca (vira root)
- MEDIO  : permite acoes potencialmente perigosas, mas escopadas
- BAIXO  : especificas, usadas frequentemente por daemons normais
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Capability:
    name: str            # ex: "cap_net_raw"
    risk: str            # "alto" / "medio" / "baixo"
    short: str           # descricao 1-liner
    long: str            # paragrafo explicativo (pt-BR)


# Lista completa das capabilities do Linux 6.x.
# Cada uma tem nome canonico (lowercase com cap_ prefix) usado pelo getcap.
CAPABILITIES: list[Capability] = [
    Capability(
        name="cap_audit_control",
        risk="medio",
        short="Configurar regras do audit subsystem",
        long=(
            "Permite habilitar/desabilitar o kernel audit, adicionar regras "
            "e configurar limits. Útil para daemons de auditoria (auditd); "
            "perigoso se atacante puder desligar logging."
        ),
    ),
    Capability(
        name="cap_audit_read",
        risk="baixo",
        short="Ler logs do audit via multicast netlink",
        long=(
            "Permite ler audit logs em tempo real via netlink. Usado por "
            "ferramentas de monitoramento (ex: auditbeat, falco)."
        ),
    ),
    Capability(
        name="cap_audit_write",
        risk="baixo",
        short="Escrever no audit log",
        long=(
            "Permite enviar mensagens para o audit subsystem. Usado por "
            "daemons que geram eventos (sshd, sudo, login)."
        ),
    ),
    Capability(
        name="cap_block_suspend",
        risk="baixo",
        short="Impedir suspend do sistema",
        long=(
            "Permite manter o sistema acordado (epoll EPOLLWAKEUP). Usado "
            "por alguns daemons de notificação."
        ),
    ),
    Capability(
        name="cap_bpf",
        risk="medio",
        short="Carregar programas BPF",
        long=(
            "Permite operações BPF privilegiadas (carregar programas, criar "
            "maps). Necessário para ferramentas como bcc, bpftrace, cilium. "
            "Atacante com cap_bpf pode injetar código no kernel."
        ),
    ),
    Capability(
        name="cap_checkpoint_restore",
        risk="medio",
        short="Checkpoint/restore de processos (CRIU)",
        long=(
            "Necessário para CRIU (Checkpoint/Restore in Userspace). "
            "Permite congelar e restaurar processos com seu estado."
        ),
    ),
    Capability(
        name="cap_chown",
        risk="medio",
        short="Mudar UID/GID de qualquer arquivo",
        long=(
            "Permite chown arbitrário. Tradicionalmente reservado pro root. "
            "Atacante pode mudar dono de arquivos sensíveis (ex: /etc/passwd)."
        ),
    ),
    Capability(
        name="cap_dac_override",
        risk="alto",
        short="Bypass de permissões discricionárias",
        long=(
            "Ignora as checagens normais de permissão (rwx). Equivale a "
            "ler/escrever/executar qualquer arquivo. **Quase root** — "
            "qualquer binário com isso é SUSPEITO se não for um daemon "
            "conhecido."
        ),
    ),
    Capability(
        name="cap_dac_read_search",
        risk="medio",
        short="Bypass de permissões para LER",
        long=(
            "Versão reduzida do cap_dac_override: só leitura/listing, sem "
            "escrita. Usado por daemons de backup (ex: rsync) e indexadores."
        ),
    ),
    Capability(
        name="cap_fowner",
        risk="medio",
        short="Bypass de checagens 'owner' em operações de arquivo",
        long=(
            "Permite chmod, utimes, IS_IMMUTABLE em arquivos que não são "
            "seus. Usado por backup tools que precisam preservar metadata."
        ),
    ),
    Capability(
        name="cap_fsetid",
        risk="baixo",
        short="Setar SUID/SGID em arquivos",
        long=(
            "Permite manter SUID/SGID em arquivos após chown/write. Usado "
            "por package managers ao instalar binários SUID."
        ),
    ),
    Capability(
        name="cap_ipc_lock",
        risk="baixo",
        short="Lock memória (mlock)",
        long=(
            "Permite mlock(), mlockall() — manter páginas na RAM, prevenir "
            "swap. Usado por GPG (proteger chaves), bancos de dados."
        ),
    ),
    Capability(
        name="cap_ipc_owner",
        risk="baixo",
        short="Bypass IPC ownership checks",
        long=(
            "Permite operar em System V IPC objects de outros usuários."
        ),
    ),
    Capability(
        name="cap_kill",
        risk="medio",
        short="Enviar sinais para qualquer processo",
        long=(
            "Bypass das checagens normais (UID precisa bater) para "
            "signaling. Pode parar daemons críticos ou matar processos "
            "de outros users."
        ),
    ),
    Capability(
        name="cap_lease",
        risk="baixo",
        short="Lease em arquivos",
        long=(
            "Permite estabelecer leases (file_lock F_SETLEASE). Usado por "
            "Samba/NFS para notificar clientes de mudanças."
        ),
    ),
    Capability(
        name="cap_linux_immutable",
        risk="medio",
        short="Setar/limpar atributos immutable e append-only",
        long=(
            "chattr +i / +a. Usado para proteger logs (append-only) ou "
            "arquivos de config (immutable)."
        ),
    ),
    Capability(
        name="cap_mac_admin",
        risk="alto",
        short="Configurar MAC framework (AppArmor, SELinux)",
        long=(
            "Permite manipular políticas do Mandatory Access Control. "
            "Em SELinux/AppArmor isso é altamente sensível — atacante "
            "pode desligar o MAC."
        ),
    ),
    Capability(
        name="cap_mac_override",
        risk="alto",
        short="Bypass de checagens MAC",
        long=(
            "Ignora regras do AppArmor/SELinux. **Crítico** — derruba "
            "uma das principais camadas de defesa do sistema."
        ),
    ),
    Capability(
        name="cap_mknod",
        risk="medio",
        short="Criar nodes de device (mknod)",
        long=(
            "Permite criar character/block devices. Usado pelo udev. "
            "Atacante pode criar /dev/sdX e ler raw disk."
        ),
    ),
    Capability(
        name="cap_net_admin",
        risk="medio",
        short="Administração de rede",
        long=(
            "Configurar interfaces, firewall (iptables/nftables), routing, "
            "bind addresses, multicasting. Usado por NetworkManager, "
            "firewalld, OpenVPN, wireguard."
        ),
    ),
    Capability(
        name="cap_net_bind_service",
        risk="baixo",
        short="Bind em portas privilegiadas (<1024)",
        long=(
            "Permite escutar em portas 1-1023 sem ser root. Usado por "
            "httpd, sshd, postfix. **Baixo risco** — é justamente o que "
            "capabilities foi feito pra resolver."
        ),
    ),
    Capability(
        name="cap_net_broadcast",
        risk="baixo",
        short="Broadcast e multicast em sockets",
        long=(
            "Permite SO_BROADCAST e bind a sockets multicast. Usado por "
            "avahi, smbd."
        ),
    ),
    Capability(
        name="cap_net_raw",
        risk="medio",
        short="Sockets RAW (ping, traceroute, tcpdump)",
        long=(
            "Permite criar AF_PACKET e raw IP sockets. Necessário pra ping, "
            "traceroute, sniffer (tcpdump). Atacante pode sniff/spoof "
            "pacotes."
        ),
    ),
    Capability(
        name="cap_perfmon",
        risk="medio",
        short="perf_event_open e profiling do kernel",
        long=(
            "Permite usar perf events e bpf_trace_printk. Útil para "
            "profiling/observability. Atacante com perfmon pode extrair "
            "informação do kernel."
        ),
    ),
    Capability(
        name="cap_setfcap",
        risk="medio",
        short="Setar file capabilities (setcap)",
        long=(
            "Permite usar o `setcap` para adicionar capabilities em "
            "outros binários. Atacante pode escalar privilégios criando "
            "um binário com cap_sys_admin."
        ),
    ),
    Capability(
        name="cap_setgid",
        risk="alto",
        short="Mudar GID e supplementary groups",
        long=(
            "setgid arbitrário. Permite virar membro do grupo `wheel`, "
            "`root`, `disk`, etc. **Caminho clássico pra root**."
        ),
    ),
    Capability(
        name="cap_setpcap",
        risk="alto",
        short="Transferir capabilities entre processos",
        long=(
            "Permite remover capabilities do bounding set ou adicionar "
            "ao set permitido de outros processos. Pode ser usado pra "
            "escalar privilégios."
        ),
    ),
    Capability(
        name="cap_setuid",
        risk="alto",
        short="setuid arbitrário (virar qualquer usuário)",
        long=(
            "Permite setuid(0). **Equivalente a root**. Qualquer binário "
            "com cap_setuid é efetivamente SUID root — investigue se "
            "não é um daemon conhecido."
        ),
    ),
    Capability(
        name="cap_sys_admin",
        risk="alto",
        short="Capability 'coringa' — quase root",
        long=(
            "Inclui dezenas de operações: mount, umount, sethostname, "
            "swapon, ioperm, kexec, criar namespaces, manipular swap, "
            "etc. **Mais perigosa** das capabilities. Tem fama de ser "
            "'a new root' pelo poder agregado."
        ),
    ),
    Capability(
        name="cap_sys_boot",
        risk="alto",
        short="Reboot, kexec, hibernar",
        long=(
            "Permite reboot(), kexec_load(). Atacante pode reiniciar o "
            "sistema em outro kernel maliciosamente."
        ),
    ),
    Capability(
        name="cap_sys_chroot",
        risk="medio",
        short="chroot()",
        long=(
            "Permite chroot. Útil para sandboxes; atacante pode escapar "
            "chroot mal configurado pra ganhar mais acesso."
        ),
    ),
    Capability(
        name="cap_sys_module",
        risk="alto",
        short="Carregar/descarregar kernel modules",
        long=(
            "insmod, rmmod. **Máxima criticidade** — atacante carrega "
            "rootkit como módulo do kernel. Em sistemas hardened, esta "
            "cap não deveria estar disponível."
        ),
    ),
    Capability(
        name="cap_sys_nice",
        risk="baixo",
        short="Mudar nice/priority de processos",
        long=(
            "Permite setpriority em qualquer processo, RT scheduling. "
            "Usado por daemons de realtime audio."
        ),
    ),
    Capability(
        name="cap_sys_pacct",
        risk="baixo",
        short="Configurar process accounting",
        long="acct(2). Habilitar process accounting."
    ),
    Capability(
        name="cap_sys_ptrace",
        risk="alto",
        short="ptrace de qualquer processo",
        long=(
            "Permite ptrace() em processos de outros users. Atacante "
            "anexa em sshd e rouba senhas, ou injeta código em daemons "
            "privilegiados."
        ),
    ),
    Capability(
        name="cap_sys_rawio",
        risk="alto",
        short="Acesso direto a hardware (I/O ports, /dev/mem)",
        long=(
            "Permite ioperm, iopl, abrir /dev/mem, /dev/kmem. Atacante "
            "pode ler memória do kernel diretamente. Crítico."
        ),
    ),
    Capability(
        name="cap_sys_resource",
        risk="medio",
        short="Bypass de resource limits",
        long=(
            "Permite ignorar disk quotas, RLIMIT_*, IPC quotas. Pode "
            "consumir todos os recursos do sistema (DoS)."
        ),
    ),
    Capability(
        name="cap_sys_time",
        risk="medio",
        short="Mudar relógio do sistema",
        long=(
            "settimeofday, adjtime, RTC. Atacante pode dessincronizar o "
            "tempo (quebra TLS cert validation, kerberos)."
        ),
    ),
    Capability(
        name="cap_sys_tty_config",
        risk="baixo",
        short="Configurar TTY (vhangup)",
        long="Operações TTY privilegiadas (raras hoje em dia)."
    ),
    Capability(
        name="cap_syslog",
        risk="medio",
        short="syslog(2) com privileges",
        long=(
            "Permite ler kernel ring buffer (dmesg) mesmo com "
            "kernel.dmesg_restrict=1. Pode revelar info de kernel."
        ),
    ),
    Capability(
        name="cap_wake_alarm",
        risk="baixo",
        short="Setar alarme que tira do suspend",
        long="CLOCK_BOOTTIME_ALARM, CLOCK_REALTIME_ALARM.",
    ),
]


# Indice por nome (lookup rapido)
BY_NAME: dict[str, Capability] = {c.name: c for c in CAPABILITIES}


RISK_ORDER = {"alto": 0, "medio": 1, "baixo": 2}


def get_capability(name: str) -> Capability | None:
    """Lookup ignorando case e prefix 'cap_' opcional."""
    n = name.lower().strip()
    if not n.startswith("cap_"):
        n = "cap_" + n
    return BY_NAME.get(n)


def risk_for_cap(name: str) -> str:
    """Retorna 'alto'/'medio'/'baixo' ou 'desconhecida'."""
    c = get_capability(name)
    return c.risk if c else "desconhecida"
