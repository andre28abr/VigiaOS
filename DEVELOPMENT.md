# VigiaOS — Guia de Desenvolvimento (v2)

> **Documento vivo.** Atualizar a cada mudança significativa. Serve como
> contexto completo para retomar o desenvolvimento (humano ou IA) sem
> precisar reler histórico de PRs ou conversas anteriores.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [O que mudou em relação à v1](#2-o-que-mudou-em-relação-à-v1)
3. [Decisões de arquitetura](#3-decisões-de-arquitetura)
4. [Estrutura do repositório](#4-estrutura-do-repositório)
5. [bootstrap.sh — o script de setup](#5-bootstrapsh--o-script-de-setup)
6. [Ferramentas planejadas](#6-ferramentas-planejadas)
7. [Roadmap por fases](#7-roadmap-por-fases)
8. [Log de implementação](#8-log-de-implementação)
9. [Operações comuns](#9-operações-comuns)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Visão geral

**VigiaOS** é uma **suite de ferramentas** para Fedora Silverblue, focada em:

- **Segurança**: ferramentas de scan, audit, IDS, forensics
- **Privacidade**: Tor Browser, anonimização, controles de permissão
- **LGPD/Compliance**: ferramentas de audit log e relatórios
- **Produtividade**: ambiente dev completo, ferramentas de escritório

**NÃO** é uma distribuição Linux. Não fork, não custom image. Usa Silverblue
**vanilla** (como Red Hat entrega) e adiciona software por cima via
`rpm-ostree install` (RPMs layered) e `flatpak install` (apps sandboxed).

**Alvo de hardware**: aarch64 e x86_64 (Apple Silicon via UTM + PCs comuns).

---

## 2. O que mudou em relação à v1

A **v1 era uma distro completa** buildada via BlueBuild — imagem container
publicada no GHCR, usuário rebasava com `rpm-ostree rebase`. Funcionava,
mas trazia custos:

- Manter pipeline de imagem (cosign, GHCR, runners ARM)
- Brigar com upstream Silverblue a cada release
- Bug-surface próprio (theme, dconf, GTK CSS — todos foram fontes de erros)
- Pouco valor agregado vs. o que Red Hat já entrega

A **v2** elimina a imagem e foca no que diferencia: ferramentas próprias.

A v1 está preservada em https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro
para consulta.

---

## 3. Decisões de arquitetura

| Decisão | Escolha | Razão |
|---|---|---|
| **Base** | Fedora Silverblue **vanilla** (não custom image) | Red Hat mantém; cobertura aarch64 + x86_64 oficial |
| **Distribuição** | Script `bootstrap.sh` + ferramentas no repo | Sem image build = sem CI/CD de imagem |
| **Instalação de pacotes** | `rpm-ostree install` para CLI nativas, `flatpak` para apps GUI | Respeita o modelo atômico; sandbox de apps usuario |
| **Linguagem default das ferramentas** | Python (PyGObject p/ GUI) | Prototipagem rápida; ecossistema rico p/ parsing; libadwaita bindings |
| **Reescrita em Rust** | Permitida quando perf importar | Mantém porta aberta sem comprometer com Rust prematuramente |
| **Ambientes graficos suportados** | GNOME prioritario; KDE second | Silverblue padrao = GNOME; suite tenta nao acoplar |
| **Distribuicao das ferramentas** | TBD: Flatpaks proprios? RPMs em COPR? PyPI? | Decidir caso a caso. Veneno se cada ferramenta tiver canal diferente. |
| **Cosign infrastructure** | Mantida localmente, nao no repo | Util para assinar releases/RPMs no futuro |

---

## 4. Estrutura do repositório

```
VigiaOS/
├── README.md                   # Pitch publico
├── DEVELOPMENT.md              # Este arquivo
├── LICENSE                     # Apache 2.0
├── .gitignore
│
├── bootstrap.sh                # Script one-liner que prepara Silverblue vanilla
│
└── tools/                      # Uma pasta por ferramenta independente
    └── activity-log/           # Vigia Activity Log (planejado, primeira a ser desenvolvida)
        └── README.md
```

Cada ferramenta em `tools/` é um **projeto independente** com seu próprio
build system (pyproject.toml, Cargo.toml, etc.). Versionam separadamente.

---

## 5. bootstrap.sh — o script de setup

**Função**: transformar uma instalação Silverblue/Kinoite/Bluefin/etc.
recém-instalada em uma estação Vigia.

**O que faz**:
1. Valida ambiente (precisa `rpm-ostree`)
2. Detecta se está na imagem v1 antiga e orienta a rebasar de volta
3. Lista RPMs que serão layered (network, audit, forensics, crypto, dev)
4. Lista Flatpaks que serão instalados (Tor Browser, KeePassXC, Signal, etc.)
5. Pede confirmação
6. Layereia tudo via `rpm-ostree install` (uma transação só)
7. Instala Flatpaks via `flatpak install --system`
8. Prompts reboot

**Categorias de pacotes** (curadoria no script):

| Categoria | Pacotes |
|---|---|
| Network | nmap, nmap-ncat, tcpdump, traceroute, mtr, bind-utils, whois, iperf3, wireshark-cli, iftop, nethogs |
| Audit | lynis, aide, chkrootkit, rkhunter, clamav, clamav-update |
| Forensics | yara, binwalk |
| Crypto | age |
| Dev | gcc, make, cmake, podman-compose, python3-pip, python3-devel, golang, rust, cargo |
| Flatpaks | Flatseal, KeePassXC, Signal, Wireshark, Tor Browser, Thunderbird |

**Filosofia**: opt-out, não opt-in. Tudo vem por padrão. Se o usuário não quer
algum, edita o script local ou usa `rpm-ostree uninstall` depois.

**Iteração futura**: flags `--category network,audit` para instalação seletiva.

---

## 6. Ferramentas planejadas

### Prioridade alta

| Nome | Função | Linguagem | Form factor v1 |
|---|---|---|---|
| **Vigia Activity Log** | Parseador inteligente de auditd/journald/fail2ban com narrativa human-readable | TBD (Python provável) | CLI |
| **Vigia Control Center** | App central GTK4 com tabs: ferramentas, privacidade, SELinux, logs | Python + PyGObject | GTK4 GUI |

### Prioridade média

| Nome | Função |
|---|---|
| **SELinux GUI moderno** | Substituto de `system-config-selinux` em GTK4 |
| **Tool Installer GUI** | Listagem visual de ferramentas com descrição + botão "instalar" |
| **Privacy Controls** | Painel central com toggles (mic, cam, geolocation, telemetry, DNS, VPN, Tor) |

### Prioridade baixa / opcionais

| Nome | Função |
|---|---|
| **Vigia Theme** | Script opcional que aplica tema zinc + emerald (do app SentinelBR) sobre GNOME |
| **Vigia Reports** | Geração de relatórios LGPD a partir dos logs |

---

## 7. Roadmap por fases

### Fase A — Bootstrap funcional (em andamento)
- ✅ Definir lista curada de RPMs e Flatpaks
- ✅ `bootstrap.sh` interativo
- ⏳ Teste end-to-end em VM Silverblue limpa
- ⏳ Documentar troubleshooting

### Fase B — Vigia Activity Log v1 (próximo)
- Decidir linguagem (Python vs. Rust) e form factor (CLI/TUI/GUI)
- MVP: parser de **um** source (audit ou fail2ban)
- Output texto narrativo + JSON (para parsing por outras ferramentas)
- Distribuição: TBD (pip, RPM, Flatpak?)

### Fase C — Vigia Activity Log v2
- Adicionar mais sources (journald, firewalld, tcpdump)
- Correlator: junta eventos relacionados em "narrativas"
- Classificador: rotineiro / interessante / suspeito
- TUI ou GUI básica

### Fase D — Vigia Control Center skeleton
- App GTK4/libadwaita com tabs vazias
- Integrar Activity Log como primeira tab
- Definir bindings com sistema (D-Bus, polkit)

### Fase E — Privacy Controls
- Identificar tudo que dá pra toggle via dconf/firewalld/systemctl
- UI com switches agrupados (Network, Devices, Telemetry, Anonimização)

### Fase F — SELinux GUI moderno
- Wraping leve de `semanage`/`getsebool`/`audit2allow`
- UI focada em "**permitir esta operação que está sendo bloqueada**"

### Fase G — Tema opcional VigiaOS
- Aproveitar trabalho de [legacy/v1-distro](https://github.com/andre28abr/VigiaOS/tree/legacy/v1-distro)
- Script aplicador (gtk.css, dconf defaults, wallpaper, starship)
- NÃO obrigatório — apenas eye candy opt-in

---

## 8. Log de implementação

> Ordem cronológica. Adicionar entrada a cada milestone.

### 2026-05-22 — Pivot: distro → toolkit
- Decisão tomada: parar de manter custom image, focar em ferramentas
- Branch `legacy/v1-distro` criada preservando estado completo da v1
- `main` resetado: novo README, DEVELOPMENT.md, LICENSE, .gitignore
- `bootstrap.sh` v1 escrito com curadoria de RPMs (network, audit, forensics,
  crypto, dev) e Flatpaks (Tor Browser, KeePassXC, Signal, Wireshark, etc.)
- Esqueleto criado para `tools/activity-log/` com README de design
- Build pipeline da v1 (GitHub Actions, BlueBuild, cosign para imagem)
  aposentado. Cosign infrastructure mantida localmente para uso futuro
  (assinar releases de ferramentas)
- Imagem `ghcr.io/andre28abr/vigiaos:latest` permanece publicada como
  arquivo histórico (não é mais buildada/atualizada)

---

## 9. Operações comuns

### Testar o bootstrap.sh

Em VM Silverblue vanilla:
```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/bootstrap.sh | bash
```

### Adicionar um RPM ao bootstrap

Editar `bootstrap.sh`, na array da categoria apropriada (`RPMS_NETWORK`,
`RPMS_AUDIT`, etc.). Commit + push.

Verificar que existe em Fedora Atomic aarch64:
```bash
dnf --releasever=44 --forcearch=aarch64 info nome-do-pacote
```

### Adicionar um Flatpak

Editar `bootstrap.sh`, na array `FLATPAKS`. Usar o App ID completo
(ex: `org.signal.Signal`). Verificar em Flathub:
```bash
flatpak search nome-app
```

### Sair da imagem v1 (rebase de volta para vanilla)

```bash
rpm-ostree rebase ostree-unverified-registry:quay.io/fedora-ostree-desktops/silverblue:44
systemctl reboot
# Depois: rodar bootstrap.sh
```

### Trabalhar numa ferramenta nova

```bash
cd tools/
mkdir minha-ferramenta && cd minha-ferramenta
# Iniciar projeto Python:
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
# Ou Rust:
cargo init
```

---

## 10. Troubleshooting

### `rpm-ostree install` falha com "package not found"

Pacote pode não existir para aarch64 ou não estar nos repos default.
Verificar:
```bash
dnf --releasever=44 --forcearch=aarch64 search nome
```
Se for COPR, adicionar ao bootstrap antes de instalar:
```bash
rpm-ostree install --apply-live --idempotent fedora-copr-config
# ...adicionar repo...
rpm-ostree install pacote
```

### Flatpak instala mas não aparece no menu

`flatpak install --system` precisa de reboot ou pelo menos logout/login
para o GNOME Shell reescanear apps. Tentar:
```bash
killall gnome-shell    # X11; em Wayland tem que relogar
# ou logout/login completo
```

### Sair da imagem v1 não funciona

Confirme que está realmente na v1:
```bash
rpm-ostree status
```
Procure por `ghcr.io/andre28abr/vigiaos` na deployment ativa.
Se sim, faça o rebase para vanilla Silverblue (comando na seção anterior).
Se houver erro, tente:
```bash
rpm-ostree cancel
rpm-ostree cleanup -p
rpm-ostree rebase ostree-unverified-registry:quay.io/fedora-ostree-desktops/silverblue:44
```
