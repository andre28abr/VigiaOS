"""Descricoes pt-BR para os SELinux booleans mais comuns.

Quando `semanage boolean -l` retorna descricao em ingles, usamos ela.
Quando retorna vazio (versoes mais novas do SELinux estao removendo
descricoes do semanage), caimos neste dict para os booleans frequentes.

Cobertura: ~60 dos booleans mais comuns em Fedora/RHEL.
Para os ~250 restantes, fica 'Sem descricao disponivel'.
"""

BOOLEAN_DESCRIPTIONS_PT: dict[str, str] = {
    # ========== Apache / httpd ==========
    "httpd_can_network_connect": "Permite o Apache fazer conexões de saída pela rede (proxy reverso, requests externos).",
    "httpd_can_network_connect_db": "Permite o Apache conectar a bancos de dados em outros hosts.",
    "httpd_can_network_relay": "Permite o Apache atuar como relay/proxy HTTP.",
    "httpd_can_sendmail": "Permite o Apache enviar emails via sendmail/postfix.",
    "httpd_enable_cgi": "Habilita execução de scripts CGI no Apache.",
    "httpd_enable_homedirs": "Permite o Apache servir conteúdo de ~/public_html dos usuários.",
    "httpd_use_nfs": "Permite o Apache acessar arquivos em shares NFS montados.",
    "httpd_use_cifs": "Permite o Apache acessar arquivos em shares CIFS/Samba montados.",
    "httpd_unified": "Roda o Apache em domínio unificado (menos isolamento, mais compatibilidade).",
    "httpd_anon_write": "Permite o Apache escrever em diretórios públicos anônimos.",
    "httpd_builtin_scripting": "Permite scripts builtin (mod_php, mod_python) no Apache.",
    "httpd_run_stickshift": "Permite o Apache rodar em modo OpenShift/Stickshift.",
    "httpd_setrlimit": "Permite o Apache ajustar limites de recursos.",
    "httpd_tty_comm": "Permite o Apache se comunicar com terminais (raro).",
    "httpd_use_fusefs": "Permite o Apache acessar sistemas de arquivos FUSE.",

    # ========== SSH ==========
    "ssh_chroot_rw_homedirs": "Permite SSH com chroot acessar home dirs em leitura/escrita.",
    "ssh_keysign": "Permite uso de chaves SSH para autenticação host-based.",
    "ssh_sysadm_login": "Permite login SSH como usuário sysadm (privilegiado).",

    # ========== Samba / CIFS ==========
    "samba_enable_home_dirs": "Permite Samba compartilhar diretórios home dos usuários.",
    "samba_export_all_ro": "Permite Samba exportar qualquer diretório (somente leitura).",
    "samba_export_all_rw": "Permite Samba exportar qualquer diretório (leitura/escrita) — risco alto.",
    "samba_create_home_dirs": "Permite Samba criar home dirs ao primeiro login.",
    "samba_share_nfs": "Permite Samba compartilhar diretórios montados via NFS.",
    "samba_share_fusefs": "Permite Samba compartilhar diretórios em sistemas FUSE.",
    "samba_run_unconfined": "Permite Samba rodar scripts unconfined (perigoso).",
    "use_samba_home_dirs": "Permite uso de home directories montadas via Samba.",

    # ========== FTP ==========
    "ftpd_anon_write": "Permite FTP anônimo escrever em diretórios públicos.",
    "ftpd_full_access": "Permite o serviço FTP acessar TODO o sistema de arquivos.",
    "ftpd_use_cifs": "Permite FTP acessar shares CIFS/Samba.",
    "ftpd_use_nfs": "Permite FTP acessar shares NFS.",
    "ftpd_use_passive_mode": "Permite modo passivo no FTP (cliente conecta de volta).",
    "ftpd_connect_db": "Permite FTP conectar a bancos de dados.",

    # ========== NFS ==========
    "nfs_export_all_ro": "Permite NFS exportar qualquer diretório (somente leitura).",
    "nfs_export_all_rw": "Permite NFS exportar qualquer diretório (leitura/escrita) — risco alto.",
    "use_nfs_home_dirs": "Permite uso de home directories montadas via NFS.",

    # ========== Mail ==========
    "postfix_local_write_mail_spool": "Permite Postfix escrever no spool de email local.",
    "sendmail_can_network_connect_db": "Permite Sendmail conectar a bancos de dados externos.",
    "exim_can_connect_db": "Permite Exim conectar a bancos de dados externos.",
    "exim_read_user_files": "Permite Exim ler arquivos dos usuários.",
    "exim_manage_user_files": "Permite Exim gerenciar (criar/deletar) arquivos dos usuários.",

    # ========== Cron ==========
    "cron_can_relabel": "Permite cron mudar labels SELinux de arquivos.",
    "cron_userdomain_transition": "Permite cron transitionar para o domínio do usuário.",
    "cron_system_cronjob_use_shares": "Permite cron jobs do sistema usarem shares de rede.",

    # ========== Virtualizacao ==========
    "virt_use_nfs": "Permite VMs e containers acessarem shares NFS.",
    "virt_use_samba": "Permite VMs e containers acessarem shares Samba.",
    "virt_use_fusefs": "Permite VMs acessarem sistemas FUSE.",
    "virt_sandbox_use_audit": "Permite sandboxes virtuais acessarem o subsistema de audit.",
    "virt_sandbox_use_netlink": "Permite sandboxes virtuais usarem sockets netlink.",
    "virt_use_usb": "Permite VMs acessarem dispositivos USB do host.",

    # ========== Mozilla / browsers ==========
    "mozilla_plugin_can_network_connect": "Permite plugins do Mozilla fazerem conexões de rede.",
    "mozilla_plugin_use_bluejeans": "Permite plugins do Mozilla usarem BlueJeans (vídeo call).",
    "mozilla_read_content": "Permite Mozilla ler conteúdo do usuário fora do home.",

    # ========== Daemons gerais ==========
    "daemons_dump_core": "Permite daemons gerarem core dumps em caso de crash.",
    "daemons_enable_cluster_mode": "Habilita modo cluster para daemons (HA).",
    "daemons_use_tcp_wrapper": "Permite daemons usarem TCP wrappers (tcpd).",

    # ========== User SELinux ==========
    "selinuxuser_execheap": "Permite usuários SELinux alocarem memória executável no heap (perigoso).",
    "selinuxuser_execmod": "Permite usuários SELinux fazer relocações em segmento texto de libs.",
    "selinuxuser_execstack": "Permite usuários SELinux terem stack executável (perigoso).",
    "selinuxuser_postgresql_connect_enabled": "Permite usuários SELinux conectarem a PostgreSQL.",
    "selinuxuser_mysql_connect_enabled": "Permite usuários SELinux conectarem a MySQL.",
    "selinuxuser_ping": "Permite usuários SELinux usarem ping.",
    "selinuxuser_share_music": "Permite usuários compartilharem música via apps.",
    "selinuxuser_tcp_server": "Permite usuários SELinux rodarem servidores TCP.",
    "selinuxuser_udp_server": "Permite usuários SELinux rodarem servidores UDP.",
    "selinuxuser_use_ssh_chroot": "Permite usuários SELinux usarem SSH com chroot.",

    # ========== X Server ==========
    "xserver_clients_write_xshm": "Permite clientes X11 escreverem em shared memory.",
    "xserver_object_manager": "Habilita object manager do XServer (controle granular).",

    # ========== Modo seguro ==========
    "secure_mode": "Modo seguro: restringe transições de domínio adicionais.",
    "secure_mode_insmod": "Modo seguro para inserção de módulos do kernel (impede insmod).",
    "secure_mode_policyload": "Restringe load de novas SELinux policies em runtime.",

    # ========== Boot / sistema ==========
    "allow_console_login": "Permite login direto via console (necessário em mainframe IBM Z).",
    "allow_execheap": "Permite alocar memória executável no heap (perigoso — RWX).",
    "allow_execmem": "Permite alocar memória executável (alguns JITs precisam).",
    "allow_execmod": "Permite relocações em segmento texto de bibliotecas (texto compartilhado).",
    "allow_execstack": "Permite stack executável (perigoso — exploits clássicos).",
    "allow_ypbind": "Permite uso de NIS/YP (yellow pages, sistema legacy).",

    # ========== Audit / ABRT ==========
    "abrt_anon_write": "Permite o ABRT escrever em diretórios públicos anônimos.",
    "abrt_handle_event": "Permite o ABRT rodar handlers de eventos.",
    "abrt_upload_watch_anon_write": "Permite watcher do ABRT escrever em uploads anônimos.",

    # ========== Misc comuns ==========
    "tor_can_network_relay": "Permite Tor atuar como relay de rede (relay/exit node).",
    "tor_bind_all_unreserved_ports": "Permite Tor bindar em portas não-reservadas.",
    "tftp_anon_write": "Permite TFTP anônimo escrever (boot servers PXE).",
    "tftp_home_dir": "Permite TFTP servir conteúdo de home directories.",
    "fenced_can_network_connect": "Permite fenced (cluster fencing) fazer conexões de rede.",
    "fenced_can_ssh": "Permite fenced usar SSH para STONITH.",
    "gluster_anon_write": "Permite GlusterFS aceitar escritas anônimas.",
    "polipo_connect_all_unreserved": "Permite Polipo (proxy HTTP) conectar a portas não-reservadas.",
    "pcp_bind_all_unreserved_ports": "Permite PCP (Performance Co-Pilot) bindar em portas não-reservadas.",
}
