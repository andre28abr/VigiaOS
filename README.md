# VigiaOS — suíte de segurança, privacidade e LGPD (Fedora Workstation)

> **VigiaOS** é **um aplicativo** (GTK4 + libadwaita) que transforma um **Fedora
> Workstation vanilla** numa estação de trabalho de **segurança, privacidade,
> auditoria e conformidade com a LGPD** — para o advogado, o profissional
> liberal e o escritório pequeno que lida com dados sensíveis de clientes. Numa
> janela só, o rail abre cinco seções: **Início** (monitor do sistema em tempo
> real), **Hub** (13 ferramentas gráficas de segurança/privacidade), **Red**
> (pentest), **Blue** (SOC — detecção e resposta) e **Relatórios** (central de
> eventos das ferramentas). Tudo em português — **não é uma distro**, são
> ferramentas sobre o Fedora vanilla.

[![ci](https://github.com/andre28abr/VigiaOS/actions/workflows/ci.yml/badge.svg)](https://github.com/andre28abr/VigiaOS/actions/workflows/ci.yml)
![Status](https://img.shields.io/badge/status-v0.x%20ativo%20%C2%B7%20auditado-success)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/GTK4-libadwaita-4A86CF?logo=gnome&logoColor=white)
![Rust](https://img.shields.io/badge/Rust-Activity%20Log%20core-dea584?logo=rust&logoColor=black)
![Tests](https://img.shields.io/badge/tests-1460%20python%20%2B%2028%20rust-success)
![License](https://img.shields.io/badge/license-Apache--2.0-orange)
![Fedora](https://img.shields.io/badge/Fedora-Workstation-51A2DA?logo=fedora&logoColor=white)
![LGPD](https://img.shields.io/badge/LGPD-by%20design-10b981)

> **Projeto educacional.** O VigiaOS é um projeto de **estudo** — citado pelo
> autor como material didático — com foco em segurança **defensiva** (blue
> team), privacidade e LGPD. As ferramentas são **invólucros gráficos em
> português** de projetos open-source consagrados (ClamAV, Lynis, AIDE, YARA,
> Suricata, Volatility, nmap, theHarvester, nuclei, wapiti…); não há nada de
> ofensivo inédito. A seção **Red** fica atrás de um **termo de uso** que cita
> a Lei 12.737/2012 e destina-se ao uso nos **próprios sistemas** ou em
> laboratório autorizado. Detalhes em [CLAUDE.md](CLAUDE.md).

---

## 👤 Autor

**André Augusto Azarias de Souza** · DPO / Encarregado de Dados · Compliance & GRC · Privacy Engineering

Gestor com **18 anos de atuação como Gerente Administrativo e Encarregado de Dados (DPO)** em organização do setor de saúde suplementar, ambiente regulado pela ANS e pela LGPD. Participou de decisões de diretoria, conduziu a relação com hospitais e operadoras, liderou a modernização dos sistemas administrativos e de segurança da informação e coordenou o programa de adequação à LGPD da organização, com dados sensíveis de saúde sob o Art. 11.

Desde 2025 conduz, como **product owner técnico**, projetos open-source de segurança e privacidade em Python, Go, Rust e Swift, com a codificação orquestrada por assistentes de IA generativa sob sua direção e revisão. O VigiaOS seguiu esse modelo: exercitando a tradução de exigências regulatórias (LGPD) e conceitos de hardening, auditoria e privacidade em uma suíte funcional. Também desenvolve **automações de processos com n8n** e é autor de cinco livros publicados, entre eles *Da Norma à Liderança*, sobre atualização profissional em GRC.

→ **[Bio completa: AUTHOR.md](AUTHOR.md)** · [LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza) · [GitHub Profile](https://github.com/andre28abr)

### 📂 Outros projetos do autor

**[SentinelBR](https://github.com/andre28abr/SentinelBR-platform)** — Plataforma open-source de **SIEM + LGPD** para PMEs brasileiras. Onde o VigiaOS cuida da *estação de trabalho*, o SentinelBR cuida da *infraestrutura*: agente Go (gRPC mTLS), detecção em tempo real (Sigma-style + YARA + OSV.dev), resposta automatizada (SOAR-lite) e compliance LGPD nativa, multi-tenant. Stack: Python 3.12 / FastAPI / Go 1.25 / React 19 / PostgreSQL / Loki.

**[Plataforma LGPD](https://github.com/andre28abr/lgpd-platform)** — Plataforma web multi-tenant que **treina, avalia e opera** a conformidade com a LGPD: diagnóstico de maturidade, ROPA (Art. 37), RIPD (Art. 38), direitos do titular (Art. 18) e resposta a incidentes (Art. 48).

**[Peapod](https://github.com/andre28abr/Peapod)** — Sandboxes **isolados e descartáveis para agentes de IA** (MCP, CLI, dashboard web e app nativo de macOS): rede desligada por padrão, allowlist de domínios e trilha de auditoria.

**[Uptend](https://github.com/andre28abr/Uptend)** — App nativo de macOS para **configurar e manter o Mac** e **auditar servidores Linux**: coletor portátil, relatórios, CVEs, MITRE, lente LGPD e playbook de hardening com rollback (Swift 6 + SwiftUI).

**[banana](https://github.com/andre28abr/banana)** — Editor **local-first** de notas Markdown, código e PDF (Tauri 2 + Rust + Svelte 5), com vault cifrado (Argon2id + AES-256-GCM).

**SC Platform** *(privado, disponível para apresentação mediante solicitação)* — SaaS multi-tenant pra gestão de licitações públicas (PNCP, simulador da Lei 14.133, robô de lances, extração de PDF com IA local, CRM). 75k+ linhas, 547 testes.

---

## 🛡️ O que tem dentro

**VigiaOS** é um app só, com um rail de **seções** — em vez de três janelas
soltas, uma experiência única. Tudo compartilha a biblioteca `vigia-common`, a
identidade visual (zinc + emerald) e os padrões de UI (GTK4 + libadwaita).

| Seção | Audiência | Escopo | Status |
|---|---|---|---|
| **Início** | Todos | Monitor do sistema em tempo real (CPU/RAM/disco/rede/processos) | 🟢 Ativo |
| **Hub** | Advogado, profissional liberal, escritório LGPD | Segurança + privacidade + hardening + auditoria **single-host** (13 ferramentas) | 🟢 Ativo |
| **Red** | Pentester, red team | Ferramentas **ofensivas** com GUI (OSINT, scanner de rede, vuln, web, Wi-Fi, Metasploit, senhas) + termo de uso (Lei 12.737/12) | 🟢 7 módulos prontos |
| **Blue** | Blue team, analista de SOC | **Detecção e resposta** (SIEM-lite, IDS, YARA hunting, forense de memória, threat intel) | 🟢 7 módulos prontos |
| **Relatórios** | Todos | **Central de Relatórios** — eventos das ferramentas (recon/scan/vuln/web/antivírus/rootkit) em SQLite local `0600`, retenção LGPD 180 dias, filtros 7/30/90/365 dias, exportação HTML com selo SHA-256 | 🟢 Ativo |

> Antes eram **3 apps separados** (VigiaHub / VigiaRed / VigiaBlue); foram
> unificados num só — **VigiaOS** — pra uma experiência coesa e **um ícone só**
> no menu. A casca (rail, Configurações, Ajuda, Notificações) é compartilhada;
> Red e Blue entram pelo **mesmo master-detail do Hub** via um adaptador
> (`Module` → `ToolEntry`).
>
> **VigiaOps** (orquestração **multi-host** via SSH) segue no roadmap como
> produto *separado* — esse sim faz sentido distribuir à parte. Detalhes em
> [DEVELOPMENT.md §10](DEVELOPMENT.md#10-roadmap).

---

## Por que não uma distro?

Manter uma distro custom é caro (segurança, updates, testes contra upstream).
Manter ferramentas é leve. Red Hat já constrói um ótimo OS — deixamos eles
fazerem isso e construímos por cima.

Resultado: as ferramentas rodam sobre o **Fedora Workstation vanilla**,
aproveitando as atualizações do sistema-base sem complicação.

---

## 🚀 O app VigiaOS

O **VigiaOS** é uma janela só em layout **master-detail-content**: um rail fino à
esquerda troca de **seção** (Início / Hub / Red / Blue / Relatórios) e, dentro de
cada uma, as ferramentas/módulos aparecem numa lista agrupada por categoria e
abrem **embarcados** no painel de conteúdo — sem janelas espalhadas. No rodapé
do rail ficam **Configurações** e o sino de **Notificações**.

Recursos (nível do app):

- **Tudo Certo?** — painel de checkup com semáforo 🟢🟡🔴: confere atualizações,
  firewall, antivírus e privacidade; o botão **Resolver** leva direto à ferramenta
  que arruma cada pendência. Re-checa sempre que a tela aparece.
- **Busca rápida (`Ctrl+K`)** — abre qualquer ferramenta digitando o nome.
- **Tema Terminal** (opcional) — visual escuro estilo terminal/hacker, em
  *Configurações → Aplicação → Aparência* (o padrão segue o tema do sistema).
- **Notificações de segurança** + **varredura de vírus semanal** — alertas no
  desktop quando algo precisa de atenção e uma checagem automática agendada
  (timer do usuário via systemd, **sem root**). Ambas em *Configurações → Aplicação*.
- **Autostart XDG** — inicia junto com o sistema (`~/.config/autostart`).
- **Ícone na bandeja** — subprocess GTK3 com ações rápidas; fechar a janela
  esconde em vez de matar o processo.
- **Bloqueio por senha (Polkit)** — exige autenticação pra abrir, **sem
  armazenar credencial** (LGPD-friendly), com *lazy auth* quando inicia minimizado.
- **Backup/restauração** da configuração em `.zip` (`0600`).
- **Configurações** — abas **Sobre · Atualizações · Aplicação · Segurança ·
  Ajuda** (a Ajuda traz os manuais leigos e técnicos em Markdown, in-app).

Stack: Python + GTK4 + libadwaita. No terminal: `vigia-os` (ou `vigia-blue` /
`vigia-red`, que abrem o app já na seção). Cada ferramenta do Hub também **roda
sozinha**, sem depender do app (veja *Instalar só um módulo*).

---

## O que está incluído (13 ferramentas na seção Hub + Início + Atualizações)

| # | Componente | Stack | Status |
|---|---|---|---|
| 1 | **[`install/bootstrap.sh`](install/bootstrap.sh)** / **[`install/vigia-setup.sh`](install/vigia-setup.sh)** | bash | 🟢 Instalador one-shot + instalador guiado (3 etapas) |
| 2 | **[Casca VigiaOS](tools/vigia-hub/)** v0.12.6 | Python + GTK4 | 🟢 rail de seções (Início/Hub/Red/Blue/Relatórios) + **busca Ctrl+K** + **tema Terminal** (opcional) + **notificações de segurança** + **varredura de vírus semanal** + autostart XDG + tray + lock Polkit + backup/restore + Configurações (Sobre · Atualizações · Aplicação · Segurança · Ajuda) |
| 3 | **[Vigia Monitor do Sistema](tools/dashboard/)** v0.4.3 *(seção Início)* | Python + GTK4 + Cairo | 🟢 Sistema em tempo real + per-process I/O + alertas + inspetor syscalls + banda por processo + selo de plataforma |
| 4 | **Tudo Certo?** *(built-in da casca)* | Python + GTK4 | 🟢 Painel de checkup 🟢🟡🔴 (atualizações, firewall, antivírus, privacidade) com botão **Resolver** |
| 5 | **[Vigia Activity Log](tools/activity-log/)** v0.7.1 (core) + [GUI](tools/activity-log-gui/) v0.2.0 | Rust + Python | 🟢 audit + journald + fail2ban + correlations + **glossário PT-BR** ("o que é isso?") + aba **Fontes** |
| 6 | **[Vigia Privacy Controls](tools/privacy-controls/)** v0.3.2 | Python + GTK4 | 🟢 12 toggles user+system scope |
| 7 | **[Vigia SELinux GUI](tools/selinux-gui/)** v0.2.2 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow |
| 8 | **[Vigia Firewall GUI](tools/firewall-gui/)** v0.1.1 | Python + GTK4 | 🟡 Status + zones CRUD |
| 9 | **[Vigia Network Monitor](tools/netmon-gui/)** v0.2.0 | Python + GTK4 | 🟢 Conexões **agrupadas por app** + IP→nome (DNS reverso) + estados PT-BR; aba **Escutando** com glossário de portas |
| 10 | **[Vigia Hardening Checks](tools/hardening-checks/)** v0.1.6 | Python + GTK4 | 🟢 Lynis wrapper (auditoria de hardening) |
| 11 | **[Vigia Reports](tools/reports/)** v0.2.8 | Python + Jinja2 + SVG | 🟢 6 modelos + selo SHA-256 + identidade do escritório + **agendamento mensal** (headless) |
| 12 | **[Vigia File Integrity](tools/file-integrity/)** v0.2.7 | Python + GTK4 | 🟢 AIDE (sistema) + Hash ad-hoc (user) — 6 tabs |
| 13 | **[Vigia DNS Manager](tools/dns-manager/)** v0.4.4 | Python + GTK4 | 🟢 **dnscrypt-proxy** (DoH/DoT) com 11 servers curados |
| 14 | **[Vigia Capabilities Inspector](tools/capabilities-inspector/)** v0.1.2 | Python + GTK4 | 🟢 getcap audit + 41 caps pt-BR |
| 15 | **[Vigia Antivirus](tools/antivirus/)** v0.1.5 | Python + GTK4 | 🟢 ClamAV wrapper (substitui clamtk) |
| 16 | **[Vigia Rootkit Scanner](tools/rootkit-scanner/)** v0.2.4 | Python + GTK4 | 🟢 **chkrootkit + rkhunter** unificados |
| 17 | **[Atualizações](tools/tool-installer/)** v0.4.2 *(Configurações → Atualizações)* | Python + GTK4 | 🟢 checa/aplica updates do sistema + suíte via `dnf` (pkexec) |

*(linhas 1–2 são o instalador e a casca do VigiaOS; a linha 3 é o monitor que
vive na seção **Início**; as **13 ferramentas da seção Hub** são as linhas
4–16 — nomes como aparecem na lista: Tudo Certo?, Activity Log, Privacy
Controls, DNS Manager, SELinux Manager, Firewall Manager, Network Monitor,
Hardening Checks, Reports, File Integrity, Capabilities Inspector, Rootkit
Scanner e Antivirus. As **Atualizações** — antigo "Tool Installer" — viraram
uma aba dentro de Configurações. Fora do Hub ficam ainda os 7 módulos prontos
do **Red** (Recon, Network Scanner, Vuln Scanner, Web Scanner), os 7 do
**Blue** (YARA, SIEM, IDS, Memória, Timeline, Intel, Playbooks) e a **Central
de Relatórios**.)*

### Removidas na limpeza 2026-05-27 (foco LGPD)

- ~~Network Scanner (nmap)~~ — fora do escopo + risco ético (Lei 12.737/12) → volta no **VigiaRed**
- ~~Firmware Analyzer (binwalk)~~ — nicho RE/CTF
- ~~VPN Manager~~ — NetworkManager nativo do GNOME já gerencia WireGuard
- ~~Hash Tools~~ — mergeado em File Integrity v0.2.0 (mesma categoria)

## Instalação

### Tudo de uma vez (recomendado)

Um comando, no **Fedora Workstation** — instala tudo via `dnf`, na hora,
sem reboot:

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
```

Instala a suíte completa (casca + ferramentas do Hub + Red + Blue) + os
backends que elas usam (`lynis`, `aide`, `clamav`, …), compila o core Rust do
Activity Log (`cargo`), registra o atalho no menu do GNOME e instala Flatpaks
de privacidade (KeePassXC, Signal, Tor Browser…). **Não liga nenhum serviço**
— `fail2ban`/`dnscrypt-proxy` ficam off; você ativa cada um na
ferramenta correspondente (*minimum surface area* / LGPD).

Prefere ver o que vai acontecer antes? Com o repositório clonado, o
**instalador guiado** mostra tabelas e pede confirmação em cada etapa
(sistema → pacotes Hub/Blue → GUIs dos produtos):

```bash
install/vigia-setup.sh
```

### Instalar só um módulo (isolado)

Não precisa da suíte inteira. Para usar **uma ferramenta só** (ex: só o
Antivírus), use o helper — instala a tool no seu usuário (`pip --user`,
**sem root**) e registra o atalho + ícone no GNOME:

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
install/install-tool.sh --list          # ver módulos disponíveis
install/install-tool.sh antivirus       # instala só o Antivírus
```

Cada módulo roda sozinho, sem depender do VigiaOS.

### Plataforma

Alvo: **Fedora Workstation** (GNOME). Pacotes via `dnf` — aplicados na hora,
sem reboot. (O projeto começou no Silverblue/atômico; veja *Histórico*.)

### Dev (editable)

O caminho recomendado continua sendo `install/bootstrap.sh` (ou
`install/vigia-setup.sh`) — eles já instalam tudo em editable mode a partir do
clone. Se quiser fazer à mão (roteiro completo em
[DEVELOPMENT.md §8](DEVELOPMENT.md#8-setup-numa-máquina-nova-fedora-workstation)):

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
(cd tools/vigia-common && pip install --user -e .)   # dep das outras, primeiro
for d in vigia-hub vigia-red vigia-blue privacy-controls selinux-gui \
         firewall-gui netmon-gui hardening-checks reports file-integrity \
         tool-installer dns-manager capabilities-inspector activity-log-gui \
         antivirus dashboard rootkit-scanner; do
  (cd tools/$d && pip install --user -e .)
done
vigia-os   # abre o app (aliases: vigia-hub / vigia-blue / vigia-red)
```

> O core do Activity Log (`tools/activity-log`) é **Rust** e não entra no
> loop acima — `install/bootstrap.sh` compila com `cargo build --release` e
> copia o binário `vigia-log` para `~/.local/bin`.

### Empacotamento RPM / COPR (experimental)

O diretório [`packaging/`](packaging/) guarda specs RPM para um futuro repo
COPR, mas está **experimental / em manutenção**: as specs estão defasadas em
relação aos `pyproject.toml`, faltam specs de `vigia-red`/`vigia-blue` e o
build não funciona hoje (detalhes em
[`packaging/README.md`](packaging/README.md)). A instalação **suportada** é
pelos scripts em [`install/`](install/).

## Histórico

O VigiaOS nasceu mirando o **Fedora Silverblue** (sistema atômico/imutável),
mas **migrou de vez para o Fedora Workstation** em 2026-06. Motivo técnico: o
ferramental de **forense** (Volatility, plaso, símbolos de kernel) e a
**velocidade de iteração** sofrem no modelo atômico — instalar uma lib exige
toolbox/container e reboot. No Workstation tudo instala direto com `dnf`, na
hora; a suíte ficou mais simples e mais completa.

## Documentação

- [DEVELOPMENT.md](DEVELOPMENT.md) — arquitetura, decisões, roadmap do ecossistema
- [AUTHOR.md](AUTHOR.md) — sobre o autor (mini-currículo)

## Licença

Apache 2.0 — ver [LICENSE](LICENSE).

---

<div align="center">

**Feito por André Augusto Azarias De Souza**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-André%20Augusto-0A66C2?logo=linkedin&logoColor=white)](https://linkedin.com/in/andreaugusto-azariasdesouza)
[![GitHub](https://img.shields.io/badge/GitHub-andre28abr-181717?logo=github&logoColor=white)](https://github.com/andre28abr)

</div>
