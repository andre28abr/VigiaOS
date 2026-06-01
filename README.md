# VigiaOS — Suite de segurança, privacidade e LGPD para Fedora

> **VigiaOS não é uma distro Linux.** É uma coleção de **15 ferramentas
> gráficas** (GTK4 + libadwaita) + um Hub launcher que transformam uma
> instalação **vanilla** de Fedora Silverblue/Workstation numa estação de
> trabalho voltada para **segurança, privacidade, auditoria e conformidade
> com a LGPD** — pensada para o advogado, o profissional liberal e o
> escritório pequeno que lida com dados sensíveis de clientes. Tudo em
> português, com interface moderna.

![Status](https://img.shields.io/badge/status-v0.x%20ativo%20%C2%B7%20auditado-success)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![GTK4](https://img.shields.io/badge/GTK4-libadwaita-4A86CF?logo=gnome&logoColor=white)
![Rust](https://img.shields.io/badge/Rust-Activity%20Log%20core-dea584?logo=rust&logoColor=black)
![Tests](https://img.shields.io/badge/tests-940%20passing-success)
![License](https://img.shields.io/badge/license-Apache--2.0-orange)
![Fedora](https://img.shields.io/badge/Fedora-Silverblue%20%2F%20Workstation-51A2DA?logo=fedora&logoColor=white)
![LGPD](https://img.shields.io/badge/LGPD-by%20design-10b981)

---

## 👤 Autor

**André Augusto Azarias De Souza** — DPO / Encarregado de Dados · Compliance & GRC · Privacy Engineering

Profissional com mais de 18 anos de experiência em **gestão administrativa, compliance, governança da informação e proteção de dados pessoais**, com formação dupla em **Direito (Anhanguera)** e **Análise e Desenvolvimento de Sistemas (Mackenzie)**. Atuou por quase duas décadas como **Gerente Administrativo e Encarregado de Dados (DPO)** em organização do setor de saúde suplementar, com foco em adequação à LGPD, governança documental e interface com áreas técnicas.

Atualmente em **transição de carreira, com disponibilidade imediata**, conduziu o VigiaOS como **product owner técnico, com auxílio de assistentes de IA generativa para a etapa de codificação** — exercitando a tradução de exigências regulatórias (LGPD) e conceitos de hardening, auditoria e privacidade em uma suíte funcional, demonstrando fluência técnica suficiente para dialogar com times de engenharia, segurança e operações.

→ **[Bio completa: AUTHOR.md](AUTHOR.md)** · [LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza) · [GitHub Profile](https://github.com/andre28abr)

### 📂 Outros projetos do autor

**[SentinelBR](https://github.com/andre28abr/SentinelBR-platform)** — Plataforma open-source de **SIEM + LGPD** para PMEs brasileiras. Onde o VigiaOS cuida da *estação de trabalho*, o SentinelBR cuida da *infraestrutura*: agente Go (gRPC mTLS), detecção em tempo real (Sigma-style + YARA + OSV.dev), resposta automatizada (SOAR-lite) e compliance LGPD nativa, multi-tenant. Stack: Python 3.12 / FastAPI / Go 1.25 / React 19 / PostgreSQL / Loki.

**SC Platform** *(privado, sob NDA — disponível para apresentação em entrevistas mediante solicitação)* — SaaS multi-tenant pra gestão de licitações públicas (PNCP, simulador da Lei 14.133, robô de lances, extração de PDF com IA local, CRM). 75k+ linhas, 420 testes.

---

## 🛡️ Ecossistema Vigia

O VigiaOS é o **primeiro de quatro produtos** planejados. Em vez de inflar uma
única ferramenta com tudo (single-host + multi-host + pentest + SOC), o
ecossistema separa por audiência, compartilhando a biblioteca `vigia-common`,
a identidade visual (zinc + emerald) e os padrões de UI (GTK4 + libadwaita).

| Produto | Audiência | Escopo | Status |
|---|---|---|---|
| **VigiaOS** *(este repo)* | Advogado, profissional liberal, escritório LGPD | Segurança + privacidade + hardening + auditoria **single-host** | 🟢 **Ativo** (v0.x, 15 ferramentas) |
| **VigiaOps** | Sysadmin, MSP, gestor de TI | Orquestração **multi-host** via SSH (inventário, fan-out, audit log de comandos remotos) | 🔜 Planejado |
| **VigiaRed** | Pentester, red team | Ferramentas **ofensivas** com GUI (scanner, vuln, OSINT, web app) + termo de uso (Lei 12.737/12) | 🔜 Planejado |
| **VigiaBlue** | Blue team, analista de SOC | **Detecção e resposta** (SIEM-lite, IDS, YARA hunting, forense de memória, threat intel) | 🔜 Planejado |

- **VigiaOps** *(o próximo da fila)* leva as ferramentas do VigiaOS para **vários servidores ao mesmo tempo** — rodar um Hardening Check em 30 hosts via SSH, com pool de conexões persistente e trilha de auditoria assinada dos comandos remotos.
- **VigiaRed** trará o que foi deliberadamente *removido* do VigiaOS (scanner de rede, etc.) — mas no produto certo, com aviso ético/legal na primeira execução.
- **VigiaBlue** aproveita o **core do Activity Log (Rust)**, que já tem potencial de SIEM-lite: agregação de logs, correlação, threat hunting e playbooks de resposta a incidentes.

> Os quatro são **produtos distintos** (distribuição separada), não um monólito.
> O roadmap completo está em [DEVELOPMENT.md §10](DEVELOPMENT.md#10-roadmap).

---

## Por que não uma distro?

Manter uma distro custom é caro (segurança, updates, testes contra upstream).
Manter ferramentas é leve. Red Hat já constrói um ótimo OS atômico —
deixamos eles fazerem isso e construímos por cima.

Resultado: as ferramentas funcionam em qualquer Fedora Atomic (Silverblue,
Kinoite, Bluefin, Bazzite, Aurora) **e** no Workstation, aproveitando
atualizações automáticas do sistema-base sem complicação.

---

## 🚀 O Vigia Hub

O **Vigia Hub** é o coração do VigiaOS: um *launcher* central que reúne as 15
ferramentas numa única janela, em layout **master-detail-content** (3 painéis:
categorias → lista de ferramentas → conteúdo). As ferramentas rodam
**embarcadas dentro do Hub** (modo *embedded*), então é tudo uma experiência só
— sem 15 janelas espalhadas.

Recursos do Hub:

- **Autostart XDG** — inicia junto com o sistema (`~/.config/autostart`).
- **Ícone na bandeja** — subprocess GTK3 com ações rápidas ("Abrir módulo" →
  Monitor, Antivírus, …); fechar a janela esconde em vez de matar o processo.
- **Bloqueio por senha (Polkit)** — exige autenticação pra abrir o Hub, **sem
  armazenar credencial** (LGPD-friendly), com *lazy auth* quando inicia minimizado.
- **Backup/restauração** da configuração em `.zip` (`0600`).
- **Aba Ajuda** — manuais leigos e técnicos em Markdown renderizados in-app.
- **Configurações** — centro de preferências com 3 sub-abas (Aplicação / Segurança / Sobre).

Stack: Python + GTK4 + libadwaita. Cada ferramenta também **roda sozinha**, sem
depender do Hub (veja *Instalar só um módulo*).

---

## O que está incluído (15 ferramentas focadas em LGPD/escritório)

| # | Componente | Stack | Status |
|---|---|---|---|
| 1 | `bootstrap.sh` | bash | 🟡 Em desenvolvimento |
| 2 | **[Vigia Hub](tools/vigia-hub/)** v0.7.5 | Python + GTK4 | 🟢 3 painéis + autostart XDG + tray (quick actions) + lock Polkit + backup/restore + Ajuda (manuais MD) |
| 3 | **[Vigia Monitor do Sistema](tools/dashboard/)** v0.4.2 | Python + GTK4 + Cairo | 🟢 Sistema em tempo real + per-process I/O + alertas + inspetor syscalls + banda por processo + selo de plataforma |
| 4 | **[Vigia Activity Log](tools/activity-log/)** v0.7.1 (core) + [GUI](tools/activity-log-gui/) v0.1.1 | Rust + Python | 🟢 audit + journald + fail2ban + correlations |
| 5 | **[Vigia Privacy Controls](tools/privacy-controls/)** v0.3.2 | Python + GTK4 | 🟢 12 toggles user+system scope |
| 6 | **[Vigia SELinux GUI](tools/selinux-gui/)** v0.2.1 | Python + GTK4 | 🟢 6 tabs + pt-BR + audit2allow |
| 7 | **[Vigia Firewall GUI](tools/firewall-gui/)** v0.1 | Python + GTK4 | 🟡 Status + zones CRUD |
| 8 | **[Vigia Network Monitor](tools/netmon-gui/)** v0.1.1 | Python + GTK4 | 🟡 Conexões + modo admin opt-in |
| 9 | **[Vigia Hardening Checks](tools/hardening-checks/)** v0.1.5 | Python + GTK4 | 🟢 Lynis wrapper + perfil Silverblue |
| 10 | **[Vigia Reports](tools/reports/)** v0.2.7 | Python + Jinja2 + SVG | 🟢 6 modelos + selo SHA-256 + identidade do escritório + **agendamento mensal** (headless) |
| 11 | **[Vigia File Integrity](tools/file-integrity/)** v0.2.6 | Python + GTK4 | 🟢 AIDE (sistema) + Hash ad-hoc (user) — 6 tabs |
| 12 | **[Vigia Tool Installer](tools/tool-installer/)** v0.3.6 | Python + GTK4 | 🟢 rpm-ostree + **extensões navegador open source** |
| 13 | **[Vigia DNS Manager](tools/dns-manager/)** v0.4.3 | Python + GTK4 | 🟢 **dnscrypt-proxy** (DoH/DoT) com 11 servers curados |
| 14 | **[Vigia Capabilities Inspector](tools/capabilities-inspector/)** v0.1.2 | Python + GTK4 | 🟢 getcap audit + 41 caps pt-BR |
| 15 | **[Vigia Antivirus](tools/antivirus/)** v0.1.4 | Python + GTK4 | 🟢 ClamAV wrapper (substitui clamtk) |
| 16 | **[Vigia Rootkit Scanner](tools/rootkit-scanner/)** v0.2.2 | Python + GTK4 | 🟢 **chkrootkit + rkhunter** unificados |
| 17 | **[Vigia Deployments Manager](tools/deployments-manager/)** v0.1.2 | Python + GTK4 | 🟢 **rpm-ostree** GUI — rollback, pin, cleanup, labels LGPD |

*(linhas 1–2 são o instalador e o Hub; as 15 ferramentas são as linhas 3–17 —
o Tool Installer é acessado à parte, fora da sidebar das outras 14.)*

### Removidas na limpeza 2026-05-27 (foco LGPD)

- ~~Network Scanner (nmap)~~ — fora do escopo + risco ético (Lei 12.737/12) → volta no **VigiaRed**
- ~~Firmware Analyzer (binwalk)~~ — nicho RE/CTF
- ~~VPN Manager~~ — NetworkManager nativo do GNOME já gerencia WireGuard
- ~~Hash Tools~~ — mergeado em File Integrity v0.2.0 (mesma categoria)

## Instalação

### Tudo de uma vez (recomendado)

Um comando — o instalador **detecta sozinho** se você está em Fedora
Atomic (Silverblue, Kinoite, Bluefin, Bazzite, Aurora) ou Workstation, e
usa `rpm-ostree` ou `dnf`:

```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
# Em sistema atômico, reinicie ao final:  systemctl reboot
```

Instala as 15 ferramentas + os backends que elas usam (`lynis`, `aide`,
`clamav`, …), registra os atalhos no menu do GNOME e instala Flatpaks de
privacidade (KeePassXC, Signal, Tor Browser…). **Não liga nenhum serviço**
— `fail2ban`/`dnscrypt-proxy` ficam off; você ativa cada um na
ferramenta correspondente (*minimum surface area* / LGPD). Guias por
plataforma: **[Silverblue / atomic](install/silverblue/)** ·
**[Workstation](install/workstation/)**.

### Instalar só um módulo (isolado)

Não precisa da suíte inteira. Para usar **uma ferramenta só** (ex: só o
Antivírus), use o helper — instala a tool no seu usuário (`pip --user`,
**sem root**) e registra o atalho + ícone no GNOME. Funciona igual em
Silverblue e Workstation:

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
install/install-tool.sh --list          # ver módulos disponíveis
install/install-tool.sh antivirus       # instala só o Antivírus
```

Cada módulo roda sozinho, sem depender do Vigia Hub. Quando o COPR estiver
ativo: `rpm-ostree install vigia-antivirus` (atomic) ou `dnf install
vigia-antivirus` (Workstation).

### Compatibilidade por plataforma

Quase tudo roda igual nos dois — as diferenças:

| | Silverblue / Atomic | Workstation |
|---|---|---|
| Pacotes | `rpm-ostree` (+ reboot) | `dnf` (na hora) |
| Deployments Manager | ✅ | ❌ (sem deployments rpm-ostree) |
| Tool Installer → aba *Pendentes* | ✅ | ❌ (instala na hora) |
| As outras 15 ferramentas | ✅ | ✅ |

### Dev (editable)

Para hackear no código, instale em editable mode (roteiro completo em
[DEVELOPMENT.md §8](DEVELOPMENT.md#8-setup-numa-máquina-nova-silverblue-limpa)):

```bash
git clone https://github.com/andre28abr/VigiaOS.git ~/dev/VigiaOS
cd ~/dev/VigiaOS
(cd tools/vigia-common && pip install --user -e .)   # dep das outras, primeiro
for d in vigia-hub privacy-controls selinux-gui firewall-gui netmon-gui \
         hardening-checks reports file-integrity tool-installer \
         dns-manager capabilities-inspector activity-log-gui \
         antivirus dashboard rootkit-scanner deployments-manager; do
  (cd tools/$d && pip install --user -e .)
done
vigia-hub   # abre o launcher
```

### Futuro: via COPR (em preparação)

As specs RPM estão prontas em [`packaging/`](packaging/), mas o **repo
COPR ainda não foi ativado** (passos em [`packaging/README.md`](packaging/README.md)).
Quando ativo:

```bash
sudo wget -O /etc/yum.repos.d/_copr_andre28abr-vigia.repo \
  https://copr.fedorainfracloud.org/coprs/andre28abr/vigia/repo/fedora-$(rpm -E %fedora)/andre28abr-vigia-fedora-$(rpm -E %fedora).repo
sudo rpm-ostree install vigia-suite && sudo systemctl reboot   # atomic
# Workstation: sudo dnf copr enable andre28abr/vigia && sudo dnf install vigia-suite
```

## Histórico

A v1 do projeto era uma distro Linux completa baseada em Fedora Silverblue
buildada via BlueBuild. Foi pivotada em 2026-05-22 para suíte de ferramentas
após avaliarmos que o trabalho de manter um image build sobrepunha pouco
valor ao que Red Hat já entrega. A v1 está preservada em
[`legacy/v1-distro`](https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro).

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
