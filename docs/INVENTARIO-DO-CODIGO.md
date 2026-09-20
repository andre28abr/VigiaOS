# Inventário do código: Vigia-SO

> Gerado por `raiz/maquina/inventario.py` em 2026-09-20, direto do código. Não editar à mão: regenerar ao fechar um bloco de trabalho. Serve de mapa para quem vai mexer no projeto; a explicação do porquê está no README, no CLAUDE.md e nos docs do repositório. Testes são contados por função declarada; o pytest e o cargo podem reportar mais execuções por causa de parametrização.

## Resumo

| Linguagem | Números |
|---|---|
| Python | 270 módulos, 1803 funções, 0 rotas, 0 modelos, 1338 testes em 96 arquivos |
| Rust | 9 arquivos, 23 funções públicas, 0 comandos Tauri, 28 testes |

## Python

### Módulos

| Arquivo | O que é (docstring) | Classes | Funções | Linhas |
|---|---|---|---|---|
| `install/_deps.py` | Lê as registries dos produtos do shell (VigiaBlue / VigiaRed) e emite as | 0 | 1 | 53 |
| `tools/activity-log-gui/src/vigia_log_gui/__init__.py` | Vigia Activity Log GUI — frontend GTK4 do vigia-log (Rust engine). | 0 | 0 | 8 |
| `tools/activity-log-gui/src/vigia_log_gui/__main__.py` | Entry point: `python -m vigia_log_gui` ou `vigia-log-gui`. | 0 | 1 | 17 |
| `tools/activity-log-gui/src/vigia_log_gui/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/activity-log-gui/src/vigia_log_gui/backend.py` | Backend do Activity Log GUI: chama `vigia-log --output json-bundle` e parseia. | 3 | 7 | 202 |
| `tools/activity-log-gui/src/vigia_log_gui/glossary.py` | Glossário do Activity Log — traduz eventos técnicos pra linguagem comum. | 2 | 5 | 202 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/__init__.py` |  | 0 | 0 | 10 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 2 | 52 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/about.py` | Aba Sobre — manual didatico do Vigia Activity Log. | 1 | 1 | 92 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/correlations.py` | Tab Correlations: padroes cross-source detectados. | 1 | 3 | 120 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/sources.py` | Aba Fontes: explica cada log padrão do Fedora + botão 'ver só este'. | 1 | 2 | 79 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/status.py` | Tab Status: info da ultima coleta + sources disponiveis. | 1 | 2 | 192 |
| `tools/activity-log-gui/src/vigia_log_gui/tabs/timeline.py` | Tab Timeline: lista de eventos cronologicos com filtros + search. | 1 | 9 | 279 |
| `tools/activity-log-gui/src/vigia_log_gui/window.py` | Janela principal — 3 tabs (Status + Timeline + Correlations). | 2 | 10 | 194 |
| `tools/antivirus/src/vigia_antivirus/__init__.py` | Vigia Antivirus — wrapper ClamAV com UI GTK4. | 0 | 0 | 7 |
| `tools/antivirus/src/vigia_antivirus/__main__.py` | Entry point: `python -m vigia_antivirus` ou `vigia-antivirus`. | 0 | 1 | 17 |
| `tools/antivirus/src/vigia_antivirus/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/antivirus/src/vigia_antivirus/backend.py` | Backend ClamAV. | 3 | 13 | 418 |
| `tools/antivirus/src/vigia_antivirus/tabs/__init__.py` |  | 0 | 0 | 6 |
| `tools/antivirus/src/vigia_antivirus/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/antivirus/src/vigia_antivirus/tabs/about.py` | Aba Sobre — manual didatico do Vigia Antivirus. | 1 | 1 | 132 |
| `tools/antivirus/src/vigia_antivirus/tabs/database.py` | Tab Base de dados: info da base + freshclam update + scans recentes. | 1 | 7 | 292 |
| `tools/antivirus/src/vigia_antivirus/tabs/scan.py` | Tab Scan: roda clamscan com streaming colorido num terminal. | 1 | 18 | 452 |
| `tools/antivirus/src/vigia_antivirus/window.py` | Janela principal — orquestra 3 tabs (Scan + Base de dados + Sobre). | 1 | 3 | 76 |
| `tools/capabilities-inspector/src/vigia_caps/__init__.py` | Vigia Capabilities Inspector — auditoria de Linux capabilities (getcap). | 0 | 0 | 13 |
| `tools/capabilities-inspector/src/vigia_caps/__main__.py` | Entry point: `python -m vigia_caps` ou `vigia-caps`. | 0 | 1 | 17 |
| `tools/capabilities-inspector/src/vigia_caps/app.py` | Application root. | 1 | 2 | 28 |
| `tools/capabilities-inspector/src/vigia_caps/backend.py` | Backend `getcap`. | 1 | 6 | 166 |
| `tools/capabilities-inspector/src/vigia_caps/capabilities.py` | Catalogo das ~40 Linux capabilities com descricao pt-BR e classe de risco. | 1 | 2 | 425 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/__init__.py` |  | 0 | 0 | 7 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 3 | 51 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/about.py` | Aba Sobre — manual didatico. | 1 | 1 | 110 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/binaries.py` | Tab Binarios: lista filtravel dos binarios com capabilities. | 1 | 9 | 255 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/catalog.py` | Tab Catalogo: lista das ~40 capabilities do Linux com descricao pt-BR. | 1 | 5 | 153 |
| `tools/capabilities-inspector/src/vigia_caps/tabs/overview.py` | Tab Visao Geral: hero + KPIs do scan. | 1 | 9 | 263 |
| `tools/capabilities-inspector/src/vigia_caps/window.py` | Janela principal — 4 tabs (Visao Geral + Binarios + Capabilities + Sobre). | 2 | 5 | 83 |
| `tools/dashboard/src/vigia_dashboard/__init__.py` | Vigia Dashboard — sistema em tempo real (CPU, RAM, disco, rede, processos). | 0 | 0 | 21 |
| `tools/dashboard/src/vigia_dashboard/__main__.py` | Entry point: `python -m vigia_dashboard` ou `vigia-dashboard`. | 0 | 1 | 17 |
| `tools/dashboard/src/vigia_dashboard/alerts.py` | Sistema de alertas configuraveis (v0.2). | 4 | 10 | 342 |
| `tools/dashboard/src/vigia_dashboard/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/dashboard/src/vigia_dashboard/backend.py` | Backend Dashboard: le /proc, /sys e processos. | 10 | 26 | 1010 |
| `tools/dashboard/src/vigia_dashboard/graphs.py` | Widgets de grafico via Cairo + Gtk.DrawingArea. | 4 | 12 | 340 |
| `tools/dashboard/src/vigia_dashboard/net_bandwidth.py` | Banda de rede por processo via `nethogs` (snapshot pontual). | 2 | 4 | 149 |
| `tools/dashboard/src/vigia_dashboard/proc_inspect.py` | Inspecao de processo via `strace -c` (resumo de syscalls). | 2 | 3 | 133 |
| `tools/dashboard/src/vigia_dashboard/tabs/__init__.py` |  | 0 | 0 | 12 |
| `tools/dashboard/src/vigia_dashboard/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/dashboard/src/vigia_dashboard/tabs/about.py` | Aba Sobre — manual didatico do Vigia Dashboard. | 1 | 1 | 186 |
| `tools/dashboard/src/vigia_dashboard/tabs/alerts.py` | Tab Alertas (v0.2): regras configuraveis + historico de disparos. | 1 | 17 | 493 |
| `tools/dashboard/src/vigia_dashboard/tabs/network.py` | Tab Rede: banda por processo (nethogs) — quem está usando a rede. | 1 | 5 | 152 |
| `tools/dashboard/src/vigia_dashboard/tabs/overview.py` | Tab Visao Geral: KPI cards + sparklines de CPU, RAM, Rede. | 1 | 10 | 417 |
| `tools/dashboard/src/vigia_dashboard/tabs/processes.py` | Tab Processos: top processos com filtros + sort + kill. | 1 | 17 | 488 |
| `tools/dashboard/src/vigia_dashboard/tabs/resources.py` | Tab Recursos: graficos detalhados de CPU, RAM, Disco, Rede. | 1 | 9 | 392 |
| `tools/dashboard/src/vigia_dashboard/window.py` | Janela principal — orquestra 6 tabs (v0.4: +Rede). | 1 | 7 | 185 |
| `tools/dns-manager/src/vigia_dns/__init__.py` | Vigia DNS Manager — DNS encriptado via dnscrypt-proxy. | 0 | 0 | 23 |
| `tools/dns-manager/src/vigia_dns/__main__.py` | Entry point: `python -m vigia_dns` ou `vigia-dns`. | 0 | 1 | 17 |
| `tools/dns-manager/src/vigia_dns/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/dns-manager/src/vigia_dns/dnscrypt_backend.py` | Backend dnscrypt-proxy — v0.4.0 (enxugado). | 1 | 12 | 347 |
| `tools/dns-manager/src/vigia_dns/dnscrypt_catalog.py` | Catalogo de servers dnscrypt-proxy curados. | 1 | 4 | 223 |
| `tools/dns-manager/src/vigia_dns/migration.py` | Setup helpers — v0.3.0 (dnscrypt-only). | 0 | 5 | 200 |
| `tools/dns-manager/src/vigia_dns/tabs/__init__.py` |  | 0 | 0 | 6 |
| `tools/dns-manager/src/vigia_dns/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/dns-manager/src/vigia_dns/tabs/about.py` | Aba Sobre — manual didatico do Vigia DNS Manager. | 1 | 1 | 145 |
| `tools/dns-manager/src/vigia_dns/tabs/resolvers.py` | Tab Provedores (v0.3.0 — dnscrypt-only). | 1 | 10 | 324 |
| `tools/dns-manager/src/vigia_dns/tabs/status.py` | Tab Status (v0.3.0 — dnscrypt-only). | 1 | 12 | 390 |
| `tools/dns-manager/src/vigia_dns/window.py` | Janela principal — 3 tabs (Status, Provedores, Sobre). | 1 | 5 | 99 |
| `tools/file-integrity/src/vigia_integrity/__init__.py` | Vigia File Integrity — wrapper AIDE + hash ad-hoc. | 0 | 0 | 22 |
| `tools/file-integrity/src/vigia_integrity/__main__.py` | Entry point: `python -m vigia_integrity` ou `vigia-integrity`. | 0 | 1 | 17 |
| `tools/file-integrity/src/vigia_integrity/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/file-integrity/src/vigia_integrity/backend.py` | Backend AIDE. | 3 | 23 | 542 |
| `tools/file-integrity/src/vigia_integrity/hash_backend.py` | Backend hash. | 2 | 13 | 432 |
| `tools/file-integrity/src/vigia_integrity/tabs/__init__.py` |  | 0 | 0 | 16 |
| `tools/file-integrity/src/vigia_integrity/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 2 | 46 |
| `tools/file-integrity/src/vigia_integrity/tabs/about.py` | Tab Sobre: explica o AIDE + paths monitorados (read-only). Aba didatica. | 1 | 3 | 153 |
| `tools/file-integrity/src/vigia_integrity/tabs/baseline.py` | Tab Baseline: cria snapshot de diretorio + compara contra estado atual. | 1 | 13 | 406 |
| `tools/file-integrity/src/vigia_integrity/tabs/changes.py` | Tab Mudancas: lista de arquivos divergentes do baseline. | 1 | 8 | 205 |
| `tools/file-integrity/src/vigia_integrity/tabs/hash_tab.py` | Tab Hash: calcula hash de arquivo. | 1 | 5 | 188 |
| `tools/file-integrity/src/vigia_integrity/tabs/status.py` | Tab Status: estado do baseline + acoes principais + controle de perfil. | 1 | 17 | 384 |
| `tools/file-integrity/src/vigia_integrity/tabs/verify.py` | Tab Verificar: compara hash conhecido vs computado. | 1 | 4 | 220 |
| `tools/file-integrity/src/vigia_integrity/window.py` | Janela principal — orquestra 3 tabs (Status + Mudancas + Sobre). | 2 | 6 | 122 |
| `tools/firewall-gui/src/vigia_firewall/__init__.py` | Vigia Firewall GUI — gerenciador moderno de firewalld em GTK4. | 0 | 0 | 7 |
| `tools/firewall-gui/src/vigia_firewall/__main__.py` | Entry point: `python -m vigia_firewall` ou `vigia-firewall` apos pip install. | 0 | 1 | 17 |
| `tools/firewall-gui/src/vigia_firewall/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/firewall-gui/src/vigia_firewall/backend.py` | Operacoes firewalld via firewall-cmd. | 2 | 23 | 237 |
| `tools/firewall-gui/src/vigia_firewall/tabs/__init__.py` |  | 0 | 0 | 6 |
| `tools/firewall-gui/src/vigia_firewall/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/firewall-gui/src/vigia_firewall/tabs/about.py` | Aba Sobre — manual didatico do Vigia Firewall Manager. | 1 | 1 | 95 |
| `tools/firewall-gui/src/vigia_firewall/tabs/status.py` | Tab Status: estado do daemon firewalld + zona default + active zones. | 2 | 10 | 217 |
| `tools/firewall-gui/src/vigia_firewall/tabs/zones.py` | Tab Zones: edita services + ports em uma zona selecionada. | 1 | 23 | 365 |
| `tools/firewall-gui/src/vigia_firewall/window.py` | Janela principal — thin orchestrator das 2 tabs (Status + Zones). | 1 | 3 | 73 |
| `tools/hardening-checks/src/vigia_hardening/__init__.py` | Vigia Hardening Checks — wrapper grafico do Lynis. | 0 | 0 | 7 |
| `tools/hardening-checks/src/vigia_hardening/__main__.py` | Entry point: `python -m vigia_hardening` ou `vigia-hardening` apos pip install. | 0 | 1 | 17 |
| `tools/hardening-checks/src/vigia_hardening/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/hardening-checks/src/vigia_hardening/backend.py` | Backend: roda Lynis e parseia o report. | 2 | 11 | 319 |
| `tools/hardening-checks/src/vigia_hardening/tabs/__init__.py` |  | 0 | 0 | 8 |
| `tools/hardening-checks/src/vigia_hardening/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 3 | 62 |
| `tools/hardening-checks/src/vigia_hardening/tabs/about.py` | Aba Sobre — manual didatico do Vigia Hardening Checks. | 1 | 1 | 97 |
| `tools/hardening-checks/src/vigia_hardening/tabs/categories.py` | Tab Categorias: agrupa findings por categoria do Lynis. | 1 | 5 | 120 |
| `tools/hardening-checks/src/vigia_hardening/tabs/overview.py` | Tab Overview: Hardening Index + botao 'Executar auditoria'. | 1 | 9 | 316 |
| `tools/hardening-checks/src/vigia_hardening/tabs/suggestions.py` | Tab Suggestions: lista de melhorias sugeridas pelo Lynis. | 1 | 1 | 16 |
| `tools/hardening-checks/src/vigia_hardening/tabs/warnings.py` | Tab Warnings: lista de findings criticos do Lynis. | 2 | 11 | 209 |
| `tools/hardening-checks/src/vigia_hardening/window.py` | Janela principal — orquestra 4 tabs e mantem o LynisReport corrente. | 2 | 8 | 127 |
| `tools/netmon-gui/src/vigia_netmon/__init__.py` | Vigia Network Monitor — visualizador de conexoes TCP/UDP em tempo real. | 0 | 0 | 7 |
| `tools/netmon-gui/src/vigia_netmon/__main__.py` | Entry point: `python -m vigia_netmon` ou `vigia-netmon` apos pip install. | 0 | 1 | 17 |
| `tools/netmon-gui/src/vigia_netmon/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/netmon-gui/src/vigia_netmon/backend.py` | Parser para output do `ss` (socket statistics). | 1 | 7 | 120 |
| `tools/netmon-gui/src/vigia_netmon/humanize.py` | Humaniza o output do `ss`: estados em PT-BR, glossário de portas, detecção | 0 | 6 | 136 |
| `tools/netmon-gui/src/vigia_netmon/tabs/__init__.py` |  | 0 | 0 | 6 |
| `tools/netmon-gui/src/vigia_netmon/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 33 |
| `tools/netmon-gui/src/vigia_netmon/tabs/about.py` | Aba Sobre — manual didatico do Vigia Network Monitor. | 1 | 1 | 94 |
| `tools/netmon-gui/src/vigia_netmon/tabs/connections.py` | Tab Conexões: "quem está usando a minha internet" — agrupado por app, com | 1 | 19 | 326 |
| `tools/netmon-gui/src/vigia_netmon/tabs/listening.py` | Tab Escutando: o que do SEU PC está aberto pra rede (servidores ativos), | 1 | 5 | 74 |
| `tools/netmon-gui/src/vigia_netmon/window.py` | Janela principal — thin orchestrator das 2 tabs (Connections + Listening). | 1 | 3 | 73 |
| `tools/privacy-controls/src/vigia_privacy/__init__.py` | Vigia Privacy Controls — painel de controles de privacidade para GNOME (Fedora Workstation). | 0 | 0 | 8 |
| `tools/privacy-controls/src/vigia_privacy/__main__.py` | Entry point: `python -m vigia_privacy` ou `vigia-privacy` (depois de pip install). | 0 | 1 | 17 |
| `tools/privacy-controls/src/vigia_privacy/about.py` | Aba Sobre — manual didatico do Vigia Privacy Controls. | 1 | 1 | 83 |
| `tools/privacy-controls/src/vigia_privacy/app.py` | Application root (Adw.Application). | 1 | 2 | 29 |
| `tools/privacy-controls/src/vigia_privacy/toggles/__init__.py` | Registro de todos os toggles disponiveis na UI. | 0 | 0 | 43 |
| `tools/privacy-controls/src/vigia_privacy/toggles/base.py` | Base abstrata para toggles de privacidade. | 1 | 11 | 170 |
| `tools/privacy-controls/src/vigia_privacy/toggles/bluetooth.py` | Toggle: power do adapter Bluetooth (via bluetoothctl). | 0 | 4 | 60 |
| `tools/privacy-controls/src/vigia_privacy/toggles/dconf_toggles.py` | Toggles user-scope via dconf. | 0 | 0 | 118 |
| `tools/privacy-controls/src/vigia_privacy/toggles/systemd_toggles.py` | Toggles system-scope que controlam units systemd via pkexec. | 0 | 0 | 31 |
| `tools/privacy-controls/src/vigia_privacy/window.py` | Janela principal com painel de toggles agrupados por categoria. | 1 | 11 | 230 |
| `tools/reports/src/vigia_reports/__init__.py` | Vigia Reports — geracao de relatorios HTML (preparados pra PDF) a partir de logs do sistema. | 0 | 0 | 7 |
| `tools/reports/src/vigia_reports/__main__.py` | Entry point: `python -m vigia_reports` ou `vigia-reports`. | 0 | 1 | 20 |
| `tools/reports/src/vigia_reports/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/reports/src/vigia_reports/backend.py` | Coletores de dados para os relatorios. | 1 | 36 | 751 |
| `tools/reports/src/vigia_reports/charts.py` | Gráficos SVG nativos para os relatórios — sem JS, sem deps, sem rede. | 0 | 6 | 187 |
| `tools/reports/src/vigia_reports/cli.py` | Modo headless: gera um relatório sem abrir a GUI. | 0 | 2 | 50 |
| `tools/reports/src/vigia_reports/compliance.py` | Checagens de postura para o relatório de Conformidade LGPD. | 0 | 13 | 209 |
| `tools/reports/src/vigia_reports/config.py` | Identidade do escritório nos relatórios (nome, logo, responsável). | 0 | 4 | 73 |
| `tools/reports/src/vigia_reports/renderer.py` | Renderer Jinja2 → HTML. | 0 | 10 | 249 |
| `tools/reports/src/vigia_reports/scheduler.py` | Agendamento automático via **systemd user timer** (sem root). | 0 | 8 | 100 |
| `tools/reports/src/vigia_reports/system_health.py` | Leitura consolidada da saúde do sistema para o relatório homônimo. | 0 | 15 | 229 |
| `tools/reports/src/vigia_reports/tabs/__init__.py` |  | 0 | 0 | 7 |
| `tools/reports/src/vigia_reports/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/reports/src/vigia_reports/tabs/about.py` | Aba Sobre — manual didatico do Vigia Reports. | 1 | 1 | 98 |
| `tools/reports/src/vigia_reports/tabs/generate.py` | Tab Gerar: formulario com template + periodo + modo admin + botao 'Gerar'. | 1 | 9 | 203 |
| `tools/reports/src/vigia_reports/tabs/library.py` | Tab Biblioteca: lista de relatorios HTML ja gerados. | 1 | 9 | 232 |
| `tools/reports/src/vigia_reports/tabs/settings.py` | Tab Configurações: identidade do escritório (branding) nos relatórios. | 1 | 9 | 181 |
| `tools/reports/src/vigia_reports/window.py` | Janela principal — orquestra 2 tabs (Gerar + Biblioteca). | 2 | 4 | 78 |
| `tools/rootkit-scanner/src/vigia_rootkit/__init__.py` | Vigia Rootkit Scanner — wrapper chkrootkit + rkhunter com UI GTK4. | 0 | 0 | 12 |
| `tools/rootkit-scanner/src/vigia_rootkit/__main__.py` | Entry point: `python -m vigia_rootkit` ou `vigia-rootkit`. | 0 | 1 | 17 |
| `tools/rootkit-scanner/src/vigia_rootkit/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/rootkit-scanner/src/vigia_rootkit/backend.py` | Backend rootkit scanners — wrappa chkrootkit + rkhunter via pkexec. | 3 | 14 | 368 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/__init__.py` |  | 0 | 0 | 7 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/about.py` | Aba Sobre — manual didatico. | 1 | 1 | 73 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/chkrootkit.py` | Tab chkrootkit — scan rapido de rootkits. | 1 | 13 | 397 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/history.py` | Tab Historico — lista scans anteriores em formato PreferencesPage. | 1 | 6 | 120 |
| `tools/rootkit-scanner/src/vigia_rootkit/tabs/rkhunter.py` | Tab Rootkit Hunter (rkhunter) — scan completo. | 1 | 13 | 362 |
| `tools/rootkit-scanner/src/vigia_rootkit/window.py` | Janela principal — 4 tabs (chkrootkit, rkhunter, Historico, Sobre). | 1 | 3 | 71 |
| `tools/selinux-gui/src/vigia_selinux/__init__.py` | Vigia SELinux GUI — gerenciador moderno de SELinux em GTK4 + libadwaita. | 0 | 0 | 7 |
| `tools/selinux-gui/src/vigia_selinux/__main__.py` | Entry point: `python -m vigia_selinux` ou `vigia-selinux` apos pip install. | 0 | 1 | 17 |
| `tools/selinux-gui/src/vigia_selinux/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/selinux-gui/src/vigia_selinux/backend.py` | Operacoes SELinux invocadas via subprocess. | 4 | 19 | 417 |
| `tools/selinux-gui/src/vigia_selinux/descriptions.py` | Descricoes pt-BR para os SELinux booleans mais comuns. | 0 | 0 | 132 |
| `tools/selinux-gui/src/vigia_selinux/tabs/__init__.py` | Tabs do Vigia SELinux GUI. | 0 | 0 | 24 |
| `tools/selinux-gui/src/vigia_selinux/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/selinux-gui/src/vigia_selinux/tabs/about.py` | Aba Sobre — manual didatico do Vigia SELinux Manager. | 1 | 1 | 100 |
| `tools/selinux-gui/src/vigia_selinux/tabs/booleans.py` | Tab Booleans: lista pesquisavel de SELinux booleans com descricoes pt-BR. | 1 | 9 | 153 |
| `tools/selinux-gui/src/vigia_selinux/tabs/denials.py` | Tab Denials: lista de AVC denials recentes + audit2allow. | 1 | 10 | 184 |
| `tools/selinux-gui/src/vigia_selinux/tabs/files.py` | Tab Files: restorecon para um path. | 1 | 4 | 127 |
| `tools/selinux-gui/src/vigia_selinux/tabs/network.py` | Tab Network: lista de port mappings SELinux (read-only v0.1). | 1 | 5 | 117 |
| `tools/selinux-gui/src/vigia_selinux/tabs/processes.py` | Tab Processes: contextos SELinux de processos rodando (read-only). | 1 | 5 | 114 |
| `tools/selinux-gui/src/vigia_selinux/tabs/status.py` | Tab Status: modo runtime, modo persistente, info de policy. | 2 | 10 | 225 |
| `tools/selinux-gui/src/vigia_selinux/window.py` | Janela principal — thin orchestrator que monta as 6 tabs. | 1 | 3 | 87 |
| `tools/tool-installer/src/vigia_installer/__init__.py` | Vigia Tool Installer — catalogo de security tools com 1-click dnf. | 0 | 0 | 17 |
| `tools/tool-installer/src/vigia_installer/__main__.py` | Entry point: `python -m vigia_installer` ou `vigia-installer`. | 0 | 1 | 17 |
| `tools/tool-installer/src/vigia_installer/app.py` | Application root (Adw.Application). | 1 | 2 | 28 |
| `tools/tool-installer/src/vigia_installer/backend.py` | Backend de pacotes do Tool Installer (Fedora Workstation, dnf). | 1 | 14 | 232 |
| `tools/tool-installer/src/vigia_installer/catalog.py` | Catalogo curado de security tools para Fedora Workstation. | 1 | 2 | 259 |
| `tools/tool-installer/src/vigia_installer/tabs/__init__.py` |  | 0 | 0 | 5 |
| `tools/tool-installer/src/vigia_installer/tabs/_helpers.py` | Helpers especificos desta tool. | 0 | 1 | 34 |
| `tools/tool-installer/src/vigia_installer/tabs/about.py` | Aba Sobre — manual didatico do Vigia Tool Installer. | 1 | 1 | 72 |
| `tools/tool-installer/src/vigia_installer/tabs/updates.py` | Tab Atualizacoes: checa e aplica updates do sistema (dnf). | 1 | 14 | 321 |
| `tools/tool-installer/src/vigia_installer/window.py` | Janela principal de Atualizações (abas no Adw.ViewStack). | 2 | 4 | 76 |
| `tools/vigia-blue/src/vigia_blue/__init__.py` | VigiaBlue — Suíte defensiva (blue team / SOC) — ecossistema VigiaOS. Esqueleto do ecossistema VigiaOS. | 0 | 0 | 5 |
| `tools/vigia-blue/src/vigia_blue/__main__.py` | Entry point: `vigia-blue` — abre o VigiaOS na seção Blue. | 0 | 1 | 28 |
| `tools/vigia-blue/src/vigia_blue/modules/__init__.py` | Módulos do VigiaBlue (backends + GUI por módulo). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/ids/__init__.py` | Vigia IDS — painel de alertas de intrusão de rede (Suricata eve.json). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/ids/backend.py` | Backend do Vigia IDS — painel para o IDS de rede Suricata. | 3 | 20 | 507 |
| `tools/vigia-blue/src/vigia_blue/modules/ids/page.py` | GUI do Vigia IDS — abas Alertas / Histórico / Sobre. | 2 | 23 | 424 |
| `tools/vigia-blue/src/vigia_blue/modules/intel/__init__.py` | Vigia Intel — base local de IOCs + checagem de indicadores (offline-first). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/intel/backend.py` | Backend do Vigia Intel — inteligência de ameaças local (offline-first). | 2 | 12 | 244 |
| `tools/vigia-blue/src/vigia_blue/modules/intel/page.py` | GUI do Vigia Intel — abas Verificar / IOCs / Sobre. | 2 | 16 | 349 |
| `tools/vigia-blue/src/vigia_blue/modules/memory/__init__.py` | Vigia Memory — forense de dumps de memória RAM (Volatility 3). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/memory/backend.py` | Backend do Vigia Memory — forense de memória RAM com o Volatility 3. | 4 | 22 | 456 |
| `tools/vigia-blue/src/vigia_blue/modules/memory/page.py` | GUI do Vigia Memory — abas Análise / Sobre. | 1 | 22 | 435 |
| `tools/vigia-blue/src/vigia_blue/modules/playbooks/__init__.py` | Vigia Playbooks — roteiros guiados de resposta a incidentes + trilha (LGPD). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/playbooks/backend.py` | Backend do Vigia Playbooks — resposta a incidentes guiada (com trilha LGPD). | 4 | 15 | 309 |
| `tools/vigia-blue/src/vigia_blue/modules/playbooks/page.py` | GUI do Vigia Playbooks — abas Playbooks / Histórico / Sobre. | 3 | 8 | 227 |
| `tools/vigia-blue/src/vigia_blue/modules/siem/__init__.py` | Vigia SIEM — detecção e triagem de eventos de segurança (camada sobre o core). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/siem/backend.py` | Backend do Vigia SIEM — detecção e triagem de eventos de segurança. | 4 | 34 | 759 |
| `tools/vigia-blue/src/vigia_blue/modules/siem/page.py` | GUI do Vigia SIEM — abas Alertas / Regras / Histórico / Sobre. | 2 | 18 | 372 |
| `tools/vigia-blue/src/vigia_blue/modules/timeline/__init__.py` | Vigia Timeline — super-timeline forense de eventos (plaso / log2timeline). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/timeline/backend.py` | Backend do Vigia Timeline — super-timeline forense com o plaso. | 2 | 11 | 242 |
| `tools/vigia-blue/src/vigia_blue/modules/timeline/page.py` | GUI do Vigia Timeline — abas Linha do tempo / Sobre. | 1 | 18 | 275 |
| `tools/vigia-blue/src/vigia_blue/modules/yara/__init__.py` | Vigia YARA — caça a malware por regras YARA (1º módulo real do VigiaBlue). | 0 | 0 | 2 |
| `tools/vigia-blue/src/vigia_blue/modules/yara/backend.py` | Backend do Vigia YARA — caça a malware por regras YARA. | 3 | 14 | 344 |
| `tools/vigia-blue/src/vigia_blue/modules/yara/page.py` | GUI do Vigia YARA — abas Scan / Histórico / Sobre. | 2 | 21 | 409 |
| `tools/vigia-blue/src/vigia_blue/registry.py` | Registro de módulos do VigiaBlue (blue team / SOC / defesa). | 0 | 0 | 161 |
| `tools/vigia-common/src/vigia_common/__init__.py` | Constantes de layout padronizadas (Spacing/margens). | 0 | 0 | 24 |
| `tools/vigia-common/src/vigia_common/badges.py` | Helper para renderizar sub-bar de WRAPPED_PACKAGES. | 0 | 1 | 44 |
| `tools/vigia-common/src/vigia_common/events.py` | Banco de eventos do VigiaOS — fonte da verdade pra a Central de Relatórios. | 1 | 15 | 431 |
| `tools/vigia-common/src/vigia_common/helpers.py` | Helpers de UI compartilhados entre as tools do VigiaOS. | 0 | 8 | 134 |
| `tools/vigia-common/src/vigia_common/markdown.py` | Conversor minimo de Markdown para Pango markup. | 0 | 7 | 206 |
| `tools/vigia-common/src/vigia_common/notices.py` | Itens do sininho de notificações do rail — modelo puro + builders. | 1 | 1 | 40 |
| `tools/vigia-common/src/vigia_common/notifications.py` | Notificacoes desktop nativas (GNOME Shell) via Gio.Notification. | 0 | 4 | 125 |
| `tools/vigia-common/src/vigia_common/notifications_bell.py` | Sininho de notificações do rail (botão + bolinha vermelha + popover). | 1 | 3 | 111 |
| `tools/vigia-common/src/vigia_common/notify.py` | Notificações de desktop (Gio.Notification) — wrapper fino e à prova de erro. | 0 | 1 | 38 |
| `tools/vigia-common/src/vigia_common/platform.py` | Plataforma: Fedora Workstation (dnf). | 0 | 3 | 33 |
| `tools/vigia-common/src/vigia_common/posture.py` | Postura de segurança do sistema — checagens pro painel "Tudo certo?" e pro | 1 | 13 | 232 |
| `tools/vigia-common/src/vigia_common/proc.py` | Execução de subprocessos — wrapper único e seguro. | 0 | 3 | 75 |
| `tools/vigia-common/src/vigia_common/scheduler.py` | Agendamento via **systemd user timer** (sem root, escopo do usuário). | 0 | 5 | 79 |
| `tools/vigia-common/src/vigia_common/shell.py` | Shell de produto Vigia — launcher GTK4 reutilizável (rail + sidebar + conteúdo). | 3 | 33 | 854 |
| `tools/vigia-common/src/vigia_common/state.py` | Persistência de estado em JSON — escrita atômica com permissão 0600 (LGPD). | 0 | 2 | 60 |
| `tools/vigia-hub/src/vigia_hub/__init__.py` | VigiaOS — app unificado (Início + Hub + Red + Blue + Relatórios numa janela só). | 0 | 0 | 5 |
| `tools/vigia-hub/src/vigia_hub/__main__.py` | Entry point do VigiaOS: `vigia-os` (ou `vigia-hub`, `python -m vigia_hub`). | 0 | 1 | 42 |
| `tools/vigia-hub/src/vigia_hub/adapters.py` | Adaptador Module → ToolEntry para o VigiaOS. | 1 | 3 | 95 |
| `tools/vigia-hub/src/vigia_hub/app.py` | Application root (Adw.Application). | 1 | 21 | 310 |
| `tools/vigia-hub/src/vigia_hub/auth.py` | Autenticacao via pkexec pro lock do Hub (v0.5.9 — refatorado). | 0 | 5 | 144 |
| `tools/vigia-hub/src/vigia_hub/backup.py` | Backup / restauracao das configuracoes e dados do VigiaOS (.zip). | 1 | 10 | 330 |
| `tools/vigia-hub/src/vigia_hub/binpath.py` | Augmenta o `PATH` com diretórios de binários instalados pelo usuário. | 0 | 3 | 64 |
| `tools/vigia-hub/src/vigia_hub/checkup.py` | Painel "Tudo Certo?" — checkup de segurança do PC, embarcado no VigiaOS. | 1 | 7 | 180 |
| `tools/vigia-hub/src/vigia_hub/cli.py` | CLI `vigia` — status e backup/restore da suite pela linha de comando. | 0 | 6 | 112 |
| `tools/vigia-hub/src/vigia_hub/idle.py` | Monitor de inatividade pra auto-lock do Hub. | 1 | 7 | 137 |
| `tools/vigia-hub/src/vigia_hub/logging_setup.py` | Setup de logging do Vigia Hub. | 0 | 2 | 51 |
| `tools/vigia-hub/src/vigia_hub/manuals.py` | Carregamento e renderizacao dos manuais (.md) das tools. | 1 | 7 | 430 |
| `tools/vigia-hub/src/vigia_hub/markdown.py` | Re-export de vigia_common.markdown para retro-compat. | 0 | 1 | 23 |
| `tools/vigia-hub/src/vigia_hub/registry.py` | Registry das ferramentas do VigiaOS. | 1 | 3 | 592 |
| `tools/vigia-hub/src/vigia_hub/reports_html.py` | Geração do relatório HTML do VigiaOS — PURO (sem GTK), testável. | 0 | 3 | 119 |
| `tools/vigia-hub/src/vigia_hub/reports_view.py` | Seção Relatórios do VigiaOS — visão por período do banco de eventos. | 1 | 14 | 277 |
| `tools/vigia-hub/src/vigia_hub/scan.py` | vigia-scan — varredura de vírus (ClamAV) das pastas do usuário. | 0 | 5 | 81 |
| `tools/vigia-hub/src/vigia_hub/settings.py` | Settings do Hub — persistencia local + autostart XDG. | 1 | 7 | 186 |
| `tools/vigia-hub/src/vigia_hub/status.py` | Status agregado do VigiaOS — fonte unica de verdade. | 4 | 15 | 368 |
| `tools/vigia-hub/src/vigia_hub/theme.py` | Integracao com o tema do GNOME (Adw.StyleManager). | 0 | 7 | 189 |
| `tools/vigia-hub/src/vigia_hub/tray/__init__.py` | Tray icon do Vigia Hub. | 0 | 0 | 39 |
| `tools/vigia-hub/src/vigia_hub/tray/checks.py` | Detecta se o tray icon pode funcionar. | 1 | 5 | 147 |
| `tools/vigia-hub/src/vigia_hub/tray/indicator.py` | Standalone tray icon (GTK3 + AyatanaAppIndicator3). | 0 | 6 | 233 |
| `tools/vigia-hub/src/vigia_hub/tray/manager.py` | Gerencia o subprocess do tray icon a partir do Hub (GTK4). | 1 | 6 | 114 |
| `tools/vigia-hub/src/vigia_hub/window.py` | Janela principal do Hub — 3 painéis: | 1 | 91 | 2258 |
| `tools/vigia-red/src/vigia_red/__init__.py` | VigiaRed — Suíte ofensiva (pentest / red team) — ecossistema VigiaOS. Esqueleto do ecossistema VigiaOS. | 0 | 0 | 5 |
| `tools/vigia-red/src/vigia_red/__main__.py` | Entry point: `vigia-red` — abre o VigiaOS na seção Red. | 0 | 1 | 28 |
| `tools/vigia-red/src/vigia_red/consent.py` | Termo de uso do VigiaRed (Lei 12.737/2012). | 0 | 3 | 45 |
| `tools/vigia-red/src/vigia_red/gate.py` | Portão de termo de uso reusável pelos módulos do VigiaRed. | 0 | 5 | 109 |
| `tools/vigia-red/src/vigia_red/handoff.py` | Passagem de alvo entre módulos do VigiaRed (ex.: Recon → Network Scanner). | 0 | 3 | 29 |
| `tools/vigia-red/src/vigia_red/modules/__init__.py` | Módulos do VigiaRed (pentest). Cada submódulo expõe `page.build_content()`. | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/cracker/__init__.py` | Vigia Cracker — auditoria de robustez de senhas/hashes (john / hashcat). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/cracker/backend.py` | Backend do Vigia Cracker — auditoria de robustez de senhas/hashes. | 4 | 25 | 456 |
| `tools/vigia-red/src/vigia_red/modules/cracker/page.py` | GUI do Vigia Cracker — termo de uso + Auditar / Histórico / Sobre. | 2 | 24 | 542 |
| `tools/vigia-red/src/vigia_red/modules/exploit/__init__.py` | Vigia Exploit — explorador educacional do Metasploit (busca/info + payload de lab). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/exploit/backend.py` | Backend do Vigia Exploit — explorador EDUCACIONAL do Metasploit Framework. | 4 | 21 | 407 |
| `tools/vigia-red/src/vigia_red/modules/exploit/page.py` | GUI do Vigia Exploit — termo de uso + Explorar / Payload (lab) / Histórico / Sobre. | 4 | 28 | 573 |
| `tools/vigia-red/src/vigia_red/modules/netscan/__init__.py` | Vigia Network Scanner — descoberta de portas e serviços (nmap). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/netscan/backend.py` | Backend do Vigia Network Scanner — descoberta de portas/serviços via nmap. | 5 | 23 | 564 |
| `tools/vigia-red/src/vigia_red/modules/netscan/page.py` | GUI do Vigia Network Scanner — termo de uso + Varredura / Histórico / Sobre. | 2 | 27 | 589 |
| `tools/vigia-red/src/vigia_red/modules/recon/__init__.py` | Vigia Recon — reconhecimento passivo (OSINT) via theHarvester. | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/recon/backend.py` | Backend do Vigia Recon — OSINT passivo (reconhecimento de fontes abertas). | 2 | 17 | 397 |
| `tools/vigia-red/src/vigia_red/modules/recon/page.py` | GUI do Vigia Recon — termo de uso + abas Investigar / Histórico / Sobre. | 2 | 20 | 422 |
| `tools/vigia-red/src/vigia_red/modules/vuln/__init__.py` | Vigia Vuln Scanner — varredura de vulnerabilidades por templates (nuclei). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/vuln/backend.py` | Backend do Vigia Vuln Scanner — vulnerabilidades por templates (nuclei). | 3 | 15 | 361 |
| `tools/vigia-red/src/vigia_red/modules/vuln/page.py` | GUI do Vigia Vuln Scanner — termo de uso + Varredura / Histórico / Sobre. | 2 | 23 | 481 |
| `tools/vigia-red/src/vigia_red/modules/web/__init__.py` | Vigia Web Scanner — análise de vulnerabilidades de aplicações web (wapiti). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/web/backend.py` | Backend do Vigia Web Scanner — vulnerabilidades de aplicações web (wapiti). | 3 | 18 | 365 |
| `tools/vigia-red/src/vigia_red/modules/web/page.py` | GUI do Vigia Web Scanner — termo de uso + Varredura / Histórico / Sobre. | 2 | 23 | 465 |
| `tools/vigia-red/src/vigia_red/modules/wireless/__init__.py` | Vigia Wireless — auditoria de robustez da senha da SUA rede Wi-Fi (aircrack-ng). | 0 | 0 | 2 |
| `tools/vigia-red/src/vigia_red/modules/wireless/backend.py` | Backend do Vigia Wireless — auditoria da senha da SUA rede Wi-Fi. | 1 | 19 | 326 |
| `tools/vigia-red/src/vigia_red/modules/wireless/page.py` | GUI do Vigia Wireless — termo de uso + Auditar / Histórico / Sobre. | 2 | 22 | 524 |
| `tools/vigia-red/src/vigia_red/registry.py` | Registro de módulos do VigiaRed (pentest / red team). | 0 | 0 | 187 |
| `tools/vigia-red/src/vigia_red/runner.py` | Execução cancelável de comandos externos — compartilhada pelos módulos do Red. | 1 | 4 | 61 |

### Testes

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/activity_log_gui/test_fuzz_activity.py` | 3 | Fuzz tests pro parser de bundle do Activity Log GUI (Etapa E — hardening). |
| `tests/activity_log_gui/test_glossary.py` | 10 | Testes do glossário do Activity Log (rótulos PT-BR + explain) — puro. |
| `tests/antivirus/test_antivirus_cancel.py` | 4 | Testes de cancelamento pkexec + regressao do construtor de comando do scan. |
| `tests/antivirus/test_clamav_parser.py` | 16 | Testes dos parsers do ClamAV (vigia_antivirus.backend). |
| `tests/antivirus/test_fuzz_antivirus.py` | 2 | Fuzz tests pro parser JSON do Antivirus (Etapa E — hardening). |
| `tests/blue/test_audit_fixes.py` | 4 | Regressões da auditoria 2026-09 (Blue): regex de regra YARA, heurística de root do IDS. |
| `tests/blue/test_ids_backend.py` | 25 | Testes do backend do Vigia IDS (parser eve.json + cmd + análise). |
| `tests/blue/test_intel_backend.py` | 19 | Testes do backend do Vigia Intel (classificação, checagem, import, base). |
| `tests/blue/test_memory_backend.py` | 27 | Testes do backend do Vigia Memory (catálogo + cmd + parser Volatility). |
| `tests/blue/test_playbooks_backend.py` | 12 | Testes do backend do Vigia Playbooks (catálogo + estado + trilha, sem gi). |
| `tests/blue/test_siem_backend.py` | 36 | Testes do backend do Vigia SIEM (motor de detecção puro, sem gi/vigia-log). |
| `tests/blue/test_timeline_backend.py` | 13 | Testes do backend do Vigia Timeline (cmd builders + parser psort json_line). |
| `tests/blue/test_yara_backend.py` | 34 | Testes do backend do Vigia YARA (vigia_blue.modules.yara.backend). |
| `tests/capabilities/test_caps_parser.py` | 30 | Testes do parser/catalogo do Capabilities Inspector (vigia_caps). |
| `tests/common/test_events.py` | 26 | Testes do banco de eventos (vigia_common.events). Puro: SQLite em tmp_path. |
| `tests/common/test_layout_constants.py` | 11 | Testes para constantes de layout em vigia_common. |
| `tests/common/test_markdown.py` | 25 | Testes para vigia_common.markdown.md_to_pango. |
| `tests/common/test_markdown_block.py` | 14 | Testes do md_to_pango_block — conversor de manual (markdown -> Pango). |
| `tests/common/test_notices.py` | 5 | Testes do modelo puro de notificações do sininho (vigia_common.notices). |
| `tests/common/test_notifications.py` | 4 | Testes para vigia_common.notifications (Etapa D — notificacoes desktop). |
| `tests/common/test_notify.py` | 2 | Testes do wrapper de notificação — contrato à prova de erro (sem GTK). |
| `tests/common/test_platform.py` | 3 | Testes para vigia_common.platform (Fedora Workstation / dnf). |
| `tests/common/test_posture.py` | 17 | Testes da camada de postura (avaliadores puros + overall) — sem GTK. |
| `tests/common/test_proc.py` | 14 | Testes do wrapper de subprocesso vigia_common.proc.run. |
| `tests/common/test_state.py` | 13 | Testes da persistência de estado vigia_common.state. |
| `tests/common/test_systemd_scheduler.py` | 2 | Testes do gerador de units systemd (conteúdo puro) — sem tocar no systemd. |
| `tests/dashboard/test_alerts.py` | 19 | Testes para vigia_dashboard.alerts. |
| `tests/dashboard/test_alerts_persistence.py` | 11 | Testes de persistencia em vigia_dashboard.alerts. |
| `tests/dashboard/test_format_helpers.py` | 25 | Testes para format helpers do Dashboard backend. |
| `tests/dashboard/test_fuzz_alerts.py` | 2 | Fuzz tests pro parser de regras de alerta do Dashboard (Etapa E). |
| `tests/dashboard/test_net_bandwidth.py` | 15 | Testes do net_bandwidth (parser do nethogs -t + snapshot mockado). |
| `tests/dashboard/test_page_kb.py` | 2 | RSS em KiB usa o tamanho de página real do kernel (não 4 KiB fixo). |
| `tests/dashboard/test_platform_label.py` | 8 | Testes do rotulo de plataforma do hero (Fedora Workstation). |
| `tests/dashboard/test_proc_inspect.py` | 12 | Testes do inspetor de processo (strace -c) do Dashboard. |
| `tests/dashboard/test_proc_parsers.py` | 15 | Testes para parsers de /proc no Dashboard backend. |
| `tests/dns/test_backend_cancel.py` | 3 | Testes de cancelamento pkexec (rc 126/127) do backend dnscrypt-proxy. |
| `tests/dns/test_dnscrypt_backend_helpers.py` | 10 | Tests para helpers internos do dnscrypt_backend. |
| `tests/dns/test_dnscrypt_catalog.py` | 21 | Tests para dnscrypt_catalog (catalogo do modo avancado). |
| `tests/dns/test_migration_mode.py` | 13 | Tests para migration.py — v0.3.0 (setup helpers). |
| `tests/dns/test_scenarios.py` | 11 | Cenarios completos de interacao do user — v0.3.0 (dnscrypt-only). |
| `tests/dns/test_toml_editor.py` | 6 | Tests para o editor de TOML line-based do dnscrypt_backend. |
| `tests/firewall/test_firewall_parser.py` | 17 | Testes dos parsers e validacoes do backend do firewall-gui. |
| `tests/hardening/test_hardening_cancel.py` | 5 | Testes de cancelamento pkexec (rc 126/127) + regressao do julgamento por |
| `tests/hardening/test_lynis_parser.py` | 28 | Testes do parser do report Lynis (vigia_hardening.backend). |
| `tests/hash/test_hash_operations.py` | 27 | Testes para vigia_integrity.hash_backend. |
| `tests/hash/test_safe_name.py` | 2 | hash_backend.safe_name — nomes com bytes fora do UTF-8 não estouram o JSON. |
| `tests/hub/test_adapters.py` | 18 | Testes do adaptador Module → ToolEntry (vigia_hub.adapters). |
| `tests/hub/test_auth.py` | 18 | Tests pro auth.py (v0.5.9 — refatorado pra pkexec direto). |
| `tests/hub/test_backup.py` | 22 | Tests pro modulo backup.py do Vigia Hub. |
| `tests/hub/test_binpath.py` | 13 | Testes do augmentador de PATH (vigia_hub.binpath). Puro, sem GTK, sem FS real. |
| `tests/hub/test_cli.py` | 10 | Tests pro CLI `vigia` (vigia_hub.cli). |
| `tests/hub/test_fuzz_settings.py` | 3 | Fuzz tests pro parser de settings do Vigia Hub (Etapa E — hardening). |
| `tests/hub/test_idle.py` | 6 | Tests pro IdleMonitor do Vigia Hub. |
| `tests/hub/test_logging.py` | 5 | Tests pro logging_setup do Vigia Hub. |
| `tests/hub/test_manuals.py` | 17 | Tests pro manuals.py do Vigia Hub. |
| `tests/hub/test_registry.py` | 8 | Testes do registry do Hub. |
| `tests/hub/test_reports_html.py` | 6 | Testes do gerador de relatório HTML (vigia_hub.reports_html). Puro, sem GTK. |
| `tests/hub/test_scan.py` | 2 | Testes do vigia-scan — formato do resultado. |
| `tests/hub/test_settings.py` | 28 | Tests pro modulo settings.py do Vigia Hub. |
| `tests/hub/test_status.py` | 33 | Tests pro modulo status.py do Vigia Hub. |
| `tests/hub/test_theme.py` | 9 | Tests pro theme.py do Vigia Hub (v0.6.4 — sempre segue GNOME). |
| `tests/hub/test_tray.py` | 26 | Tests pro modulo tray do Vigia Hub. |
| `tests/installer/test_backend.py` | 32 | Testes do backend do Tool Installer (Fedora Workstation, dnf). |
| `tests/installer/test_catalog.py` | 10 | Regressão do catálogo: Tor de sistema REMOVIDO. |
| `tests/integrity/test_aide_parser.py` | 26 | Testes do parser do output de `aide --check` (vigia_integrity.backend). |
| `tests/integrity/test_fuzz_integrity.py` | 3 | Fuzz tests pros parsers JSON do File Integrity (Etapa E — hardening). |
| `tests/integrity/test_hash_baseline.py` | 12 | Testes do hash_backend: deteccao de 'movido' + selecao de engine (hashdeep). |
| `tests/integrity/test_integrity_cancel.py` | 7 | Testes de cancelamento pkexec (rc 126/127) + regressao get_last_check. |
| `tests/netmon/test_humanize.py` | 8 | Testes do humanize do Network Monitor (puro — sem rede). |
| `tests/netmon/test_ss_parser.py` | 36 | Testes do parser de `ss -tunap` (vigia_netmon.backend). |
| `tests/products/test_blue_dependencies.py` | 12 | Testes das dependências dos módulos: shell.Dependency + registry requires. |
| `tests/products/test_product_manuals.py` | 7 | Manuais dos produtos Red/Blue — helper puro + cobertura. |
| `tests/products/test_skeleton_registries.py` | 10 | Testes do esqueleto dos produtos (VigiaRed / VigiaBlue) — dados puros. |
| `tests/red/test_cracker_backend.py` | 23 | Testes do backend do Vigia Cracker (john/hashcat). Puro: sem ferramentas, sem GTK. |
| `tests/red/test_exploit_backend.py` | 19 | Testes do backend do Vigia Exploit (Metasploit). Puro: sem msf, sem GTK. |
| `tests/red/test_handoff.py` | 3 | Teste do handoff — passagem de alvo Recon → Network Scanner (em memória). |
| `tests/red/test_netscan_backend.py` | 36 | Testes do backend do Vigia Network Scanner (nmap). Puro: sem nmap, sem GTK. |
| `tests/red/test_recon_backend.py` | 29 | Testes do backend do Vigia Recon (OSINT) + termo de uso do VigiaRed. |
| `tests/red/test_runner.py` | 5 | Testes do runner cancelável do Red (vigia_red.runner.ScanProcess). |
| `tests/red/test_vuln_backend.py` | 11 | Testes do backend do Vigia Vuln Scanner (nuclei). Puro: sem nuclei, sem GTK. |
| `tests/red/test_web_backend.py` | 13 | Testes do backend do Vigia Web Scanner (wapiti). Puro: sem wapiti, sem GTK. |
| `tests/red/test_wireless_backend.py` | 20 | Testes do backend do Vigia Wireless (aircrack-ng). Puro: sem ferramenta, sem GTK. |
| `tests/reports/test_charts.py` | 12 | Testes dos gráficos SVG (charts.py) — puros, sem GTK, sem rede. |
| `tests/reports/test_cli.py` | 5 | Testes do despachante de coleta + modo headless (cli.py). |
| `tests/reports/test_compliance.py` | 13 | Testes das checagens de Conformidade LGPD (compliance.py) — puros. |
| `tests/reports/test_config.py` | 10 | Testes da identidade do escritório (config.py) + branding no render. |
| `tests/reports/test_fuzz_reports.py` | 4 | Fuzz tests pros parsers de journal/JSON do Reports (Etapa E — hardening). |
| `tests/reports/test_integrity.py` | 10 | Testes do selo de integridade (SHA-256) + pacote de auditoria (.zip). |
| `tests/reports/test_render.py` | 11 | Smoke test de render ponta-a-ponta dos 2 templates. |
| `tests/reports/test_scheduler.py` | 4 | Testes do agendador (scheduler.py) — construtores de unit puros + parsing. |
| `tests/reports/test_summary.py` | 15 | Testes do status/resumo executivo + bucketing por dia (backend). |
| `tests/reports/test_system_health.py` | 20 | Testes do consolidador Saúde do Sistema (system_health.py) — puros. |
| `tests/rootkit/test_backend.py` | 23 | Tests pro backend do Vigia Rootkit Scanner. |
| `tests/rootkit/test_fuzz_rootkit.py` | 4 | Fuzz tests pros parsers JSON do Rootkit Scanner (Etapa E — hardening). |
| `tests/rootkit/test_rootkit_cancel.py` | 2 | Testes de cancelamento pkexec (rc 126/127) dos scanners de rootkit. |
| `tests/selinux/test_selinux_parser.py` | 36 | Testes dos parsers do backend SELinux (vigia_selinux.backend). |

## Rust

| Arquivo | O que é (//!) | Funções pub | Testes |
|---|---|---|---|
| `tools/activity-log/src/audit.rs` | Parseador de linhas do audit log do Linux (`/var/log/audit/audit.log`). | 5 | 4 |
| `tools/activity-log/src/correlator.rs` | Detecta padroes cross-source nos eventos e gera "correlations" — | 1 | 5 |
| `tools/activity-log/src/event.rs` | Abstracao unificada de "evento" sobre as varias fontes (audit, journal, fail2ban, ...). | 5 | 6 |
| `tools/activity-log/src/fail2ban.rs` | Parser para o log do fail2ban (`/var/log/fail2ban.log`). | 2 | 5 |
| `tools/activity-log/src/journal.rs` | Parser e loader para `systemd-journald`. | 5 | 3 |
| `tools/activity-log/src/live.rs` | Live tail mode — re-le periodicamente as fontes e devolve apenas eventos novos. | 3 | 1 |
| `tools/activity-log/src/main.rs` | vigia-log — CLI/TUI para `vigia-activity-log`. | 0 | 0 |
| `tools/activity-log/src/narrator.rs` | Converte `Event`s em frases human-readable em portugues. | 1 | 4 |
| `tools/activity-log/src/tui.rs` | Interface TUI para navegar nos eventos parseados. | 1 | 0 |

## Scripts de shell

| Arquivo | Primeira linha de comentário |
|---|---|
| `install/_ids_capture.sh` | # _ids_capture.sh — INTERNO. Rodado via pkexec (como root) pelo Vigia IDS quando |
| `install/_mem_capture.sh` | # _mem_capture.sh — INTERNO. Rodado via pkexec (como root) pelo Vigia Memory |
| `install/blue-deps.sh` | # blue-deps.sh — instala as dependências externas dos módulos do VigiaBlue. |
| `install/bootstrap.sh` | # VigiaOS — bootstrap único (auto-detecta a plataforma) |
| `install/ids-demo.sh` | # ids-demo.sh — gera um arquivo .pcap de TESTE para o Vigia IDS, de forma segura. |
| `install/install-tool.sh` | # VigiaOS — instala UM módulo isolado (user-level, sem root) |
| `install/test-samples.sh` | # test-samples.sh — cria AMOSTRAS DE TESTE seguras para os módulos do VigiaOS, |
| `install/uninstall.sh` | # uninstall.sh — remove o VigiaOS do usuário (sem precisar reinstalar a VM). |
| `install/vigia-setup.sh` | # vigia-setup.sh — instalador GUIADO do ecossistema VigiaOS (Hub · Blue · Red). |
