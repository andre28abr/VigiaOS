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

### 2026-05-22 — Activity Log v0.4 (fail2ban + tres fontes mergeadas)
- Novo modulo `fail2ban.rs`:
  - Parser de `/var/log/fail2ban.log` linhas formato:
    `YYYY-MM-DD HH:MM:SS,mmm logger [pid]: LEVEL [jail] Action IP`
  - struct `Fail2banEntry` com timestamp, level, logger, pid, jail, action, ip, raw
  - enum `Action`: Ban, Unban, Found, JailStarted, JailStopped, Other{raw}
  - enum `Level`: Debug, Info, Notice, Warning, Error, Critical
  - Detecta IPv4 e IPv6 (heuristica: tem '.' ou ':' + digito)
- `Event` enum extendida: `Event::Fail2ban(Fail2banEntry)`.
- Narrator nova: "fail2ban BANIU IP `X` (jail `Y`)", "liberou", "detectou tentativa", etc.
- TUI extendida:
  - Tag `[F]` na lista para distinguir fail2ban de [A]udit e [J]ournal
  - Cores: BAN vermelho (critico), FOUND ambar (warning), UNBAN emerald (positivo)
  - Header com contagem das 3 fontes (audit/journal/fail2ban)
  - Detail panel com formato proprio (logger, jail, action, ip, raw_message)
  - Filter cycle expandido: BAN, UNBAN, FOUND, JAIL_START, JAIL_STOP
- CLI: novo `--fail2ban-path` (default `/var/log/fail2ban.log`).
  Multi-source funciona: `--sources audit journald fail2ban` mergeia tudo.
- 5 novos unit tests para fail2ban (ban, unban, found, jail-started, ipv6).
- Total: 16 tests passando.
- Fixture: `tests/fixtures/sample-fail2ban.log` com 7 entries cobrindo
  Found (tres tentativas), Ban, Found IP novo, Ban IP novo, Unban.
- **Firewalld nao foi adicionado como source separada** — ele nao tem
  log proprio em arquivo, escreve direto via systemd journal. Usuario
  acessa eventos firewalld com `--sources journald` + busca por
  "firewalld" na TUI.

### 2026-05-22 — Activity Log v0.3 (journald + multi-source)
- Novo modulo `event.rs` com enum `Event { Audit(AuditEvent), Journal(JournalEntry) }`
  como abstracao unificada. Narrator, TUI e filtros agora operam em `Event`.
- Novo modulo `journal.rs` com:
  - struct `JournalEntry` (timestamp, priority, message, unit, comm, pid, uid, hostname, extra)
  - enum `Priority` (Emerg..Debug) mapeada do PRIORITY syslog do journal
  - `parse_json_line()` para parsear o output JSON-lines do journalctl
  - `parse_log()` para BufRead (arquivo ou stdin)
  - `fetch_via_journalctl()` que spawneia `journalctl -o json --no-pager -n LIMIT`
    e parseia stdout. Falha com mensagem clara se journalctl nao existe.
- CLI atualizada: novo flag `--sources` (multi-valor, default `audit`) +
  `--audit-path` e `--journal-path` separados. Eventos de multiplas fontes
  sao mergeados e ordenados por timestamp.
- Narrator extendido para journal: priority tag + source label trimado
  (unit sem `.service`/`.target`/etc, fallback para comm).
- TUI extendida:
  - Header mostra contagem por source (`audit:N journal:M`)
  - Cada linha tem tag `[A]` ou `[J]` antes do tipo
  - Cores semanticas adicionadas para journal priorities: ERR/CRIT/ALERT/EMERG
    em vermelho, WARNING em ambar, NOTICE em branco, INFO em zinc-300, DEBUG em zinc-500.
  - Detail panel com formato distinto para audit (records[]) vs journal (campos + message)
- JSON output discrimina source com chave `"source"` no top-level (via serde tag interno).
- Filter cycle expandido para incluir niveis syslog (ERR, WARNING, NOTICE, INFO, DEBUG)
  alem dos tipos de audit.
- 10 unit tests passando (5 audit + 3 journal + 2 narrator).
- Fixture `tests/fixtures/sample-journal.json` com 6 entries cobrindo
  Info, Notice, Warning, Err, Crit.

### 2026-05-22 — Activity Log v0.2 (filtros + search)
- Refator do TUI: estado encapsulado em `App` struct (events, visible
  indices, list_state, mode, filter, search).
- Modo `Mode::Searching` ativado com `/`. Acceita chars, Backspace,
  Enter (confirma), Esc (cancela e limpa). Lista filtrada em tempo real.
- Filtro por tipo com `f` cycle: None → AVC → USER_AUTH → USER_LOGIN
  → ANOM_ABEND → ANOM_PROMISCUOUS → SYSCALL → None.
- Esc no modo normal limpa filtro e busca.
- Title da lista mostra estado: `eventos · filter=AVC search="denied"`.
- Status bar com hints contextuais (normal vs searching).
- Match da busca destacado com fundo emerald + bold na lista.
- Detail panel cresceu de 10 para 16 linhas (Length(16)).
- Confirmado por screenshot do autor: paleta e layout funcionais.

### 2026-05-22 — Activity Log v0.1 (Rust + Ratatui + audit.log)
- Primeira ferramenta da Vigia Suite criada como projeto Cargo
  em `tools/activity-log/`.
- Parser hand-rolled de `audit.log`: handles double-quoted,
  single-quoted com expansão recursiva de nested key=value
  (USER_* pattern), e extração do `{ action }` dos AVC para
  field virtual `avc_op`.
- Narrator em PT-BR para AVC, USER_AUTH/LOGIN/ACCT, ANOM_*, SYSCALL.
- TUI Ratatui com paleta VigiaOS (zinc-950 bg, emerald accent).
- 3 modos de saída: TUI default, text (CLI pipe), json.
- 5 unit tests, fixture em `tests/fixtures/sample-audit.log`.

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
