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
            "e configurar limits. Util para daemons de auditoria (auditd); "
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
            "por alguns daemons de notificacao."
        ),
    ),
    Capability(
        name="cap_bpf",
        risk="medio",
        short="Carregar programas BPF",
        long=(
            "Permite operacoes BPF privilegiadas (carregar programas, criar "
            "maps). Necessario para ferramentas como bcc, bpftrace, cilium. "
            "Atacante com cap_bpf pode injetar codigo no kernel."
        ),
    ),
    Capability(
        name="cap_checkpoint_restore",
        risk="medio",
        short="Checkpoint/restore de processos (CRIU)",
        long=(
            "Necessario para CRIU (Checkpoint/Restore in Userspace). "
            "Permite congelar e restaurar processos com seu estado."
        ),
    ),
    Capability(
        name="cap_chown",
        risk="medio",
        short="Mudar UID/GID de qualquer arquivo",
        long=(
            "Permite chown arbitrario. Tradicionalmente reservado pro root. "
            "Atacante pode mudar dono de arquivos sensiveis (ex: /etc/passwd)."
        ),
    ),
    Capability(
        name="cap_dac_override",
        risk="alto",
        short="Bypass de permissoes discricionarias",
        long=(
            "Ignora as checagens normais de permissao (rwx). Equivale a "
            "ler/escrever/executar qualquer arquivo. **Quase root** — "
            "qualquer binario com isso e' SUSPEITO se nao for um daemon "
            "conhecido."
        ),
    ),
    Capability(
        name="cap_dac_read_search",
        risk="medio",
        short="Bypass de permissoes para LER",
        long=(
            "Versao reduzida do cap_dac_override: so leitura/listing, sem "
            "escrita. Usado por daemons de backup (ex: rsync) e indexadores."
        ),
    ),
    Capability(
        name="cap_fowner",
        risk="medio",
        short="Bypass de checagens 'owner' em operacoes de arquivo",
        long=(
            "Permite chmod, utimes, IS_IMMUTABLE em arquivos que nao sao "
            "seus. Usado por backup tools que precisam preservar metadata."
        ),
    ),
    Capability(
        name="cap_fsetid",
        risk="baixo",
        short="Setar SUID/SGID em arquivos",
        long=(
            "Permite manter SUID/SGID em arquivos apos chown/write. Usado "
            "por package managers ao instalar binarios SUID."
        ),
    ),
    Capability(
        name="cap_ipc_lock",
        risk="baixo",
        short="Lock memoria (mlock)",
        long=(
            "Permite mlock(), mlockall() — manter paginas na RAM, prevenir "
            "swap. Usado por GPG (proteger chaves), bancos de dados."
        ),
    ),
    Capability(
        name="cap_ipc_owner",
        risk="baixo",
        short="Bypass IPC ownership checks",
        long=(
            "Permite operar em System V IPC objects de outros usuarios."
        ),
    ),
    Capability(
        name="cap_kill",
        risk="medio",
        short="Enviar sinais para qualquer processo",
        long=(
            "Bypass das checagens normais (UID precisa bater) para "
            "signaling. Pode parar daemons criticos ou matar processos "
            "de outros users."
        ),
    ),
    Capability(
        name="cap_lease",
        risk="baixo",
        short="Lease em arquivos",
        long=(
            "Permite estabelecer leases (file_lock F_SETLEASE). Usado por "
            "Samba/NFS para notificar clientes de mudancas."
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
            "Permite manipular politicas do Mandatory Access Control. "
            "Em SELinux/AppArmor isso e' altamente sensivel — atacante "
            "pode desligar o MAC."
        ),
    ),
    Capability(
        name="cap_mac_override",
        risk="alto",
        short="Bypass de checagens MAC",
        long=(
            "Ignora regras do AppArmor/SELinux. **Critico** — derruba "
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
        short="Administracao de rede",
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
            "httpd, sshd, postfix. **Baixo risco** — e' justamente o que "
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
            "Permite criar AF_PACKET e raw IP sockets. Necessario pra ping, "
            "traceroute, sniffer (tcpdump). Atacante pode sniff/spoof "
            "pacotes."
        ),
    ),
    Capability(
        name="cap_perfmon",
        risk="medio",
        short="perf_event_open e profiling do kernel",
        long=(
            "Permite usar perf events e bpf_trace_printk. Util para "
            "profiling/observability. Atacante com perfmon pode extrair "
            "informacao do kernel."
        ),
    ),
    Capability(
        name="cap_setfcap",
        risk="medio",
        short="Setar file capabilities (setcap)",
        long=(
            "Permite usar o `setcap` para adicionar capabilities em "
            "outros binarios. Atacante pode escalar privilegios criando "
            "um binario com cap_sys_admin."
        ),
    ),
    Capability(
        name="cap_setgid",
        risk="alto",
        short="Mudar GID e supplementary groups",
        long=(
            "setgid arbitrario. Permite virar membro do grupo `wheel`, "
            "`root`, `disk`, etc. **Caminho classico pra root**."
        ),
    ),
    Capability(
        name="cap_setpcap",
        risk="alto",
        short="Transferir capabilities entre processos",
        long=(
            "Permite remover capabilities do bounding set ou adicionar "
            "ao set permitido de outros processos. Pode ser usado pra "
            "escalar privilegios."
        ),
    ),
    Capability(
        name="cap_setuid",
        risk="alto",
        short="setuid arbitrario (virar qualquer usuario)",
        long=(
            "Permite setuid(0). **Equivalente a root**. Qualquer binario "
            "com cap_setuid e' efetivamente SUID root — investigue se "
            "nao e' um daemon conhecido."
        ),
    ),
    Capability(
        name="cap_sys_admin",
        risk="alto",
        short="Capability 'coringa' — quase root",
        long=(
            "Inclui dezenas de operacoes: mount, umount, sethostname, "
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
            "Permite chroot. Util para sandboxes; atacante pode escapar "
            "chroot mal configurado pra ganhar mais acesso."
        ),
    ),
    Capability(
        name="cap_sys_module",
        risk="alto",
        short="Carregar/descarregar kernel modules",
        long=(
            "insmod, rmmod. **Maxima criticidade** — atacante carrega "
            "rootkit como modulo do kernel. Em sistemas hardened, esta "
            "cap nao deveria estar disponivel."
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
            "anexa em sshd e rouba senhas, ou injeta codigo em daemons "
            "privilegiados."
        ),
    ),
    Capability(
        name="cap_sys_rawio",
        risk="alto",
        short="Acesso direto a hardware (I/O ports, /dev/mem)",
        long=(
            "Permite ioperm, iopl, abrir /dev/mem, /dev/kmem. Atacante "
            "pode ler memoria do kernel diretamente. Critico."
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
        short="Mudar relogio do sistema",
        long=(
            "settimeofday, adjtime, RTC. Atacante pode dessincronizar o "
            "tempo (quebra TLS cert validation, kerberos)."
        ),
    ),
    Capability(
        name="cap_sys_tty_config",
        risk="baixo",
        short="Configurar TTY (vhangup)",
        long="Operacoes TTY privilegiadas (raras hoje em dia)."
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
