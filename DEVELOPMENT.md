# VigiaOS — Guia de Desenvolvimento

> **Documento vivo.** Atualizar a cada mudança significativa. Serve como contexto
> completo para retomar o desenvolvimento (humano ou IA) sem precisar reler
> histórico de PRs ou conversas anteriores.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Decisões de arquitetura](#2-decisões-de-arquitetura)
3. [Estrutura do repositório](#3-estrutura-do-repositório)
4. [Pipeline de build](#4-pipeline-de-build)
5. [Sistema de tema](#5-sistema-de-tema)
6. [Instalação e atualização](#6-instalação-e-atualização)
7. [Operações comuns](#7-operações-comuns)
8. [Log de implementação](#8-log-de-implementação)
9. [Roadmap](#9-roadmap)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Visão geral

**VigiaOS** é uma distribuição Linux baseada em **Fedora Silverblue** (atômico,
imutável), customizada para uso pessoal do criador (André) em contexto de
escritório de advocacia.

**Foco**:
- Segurança e privacidade
- Conformidade LGPD
- Ferramentas de auditoria
- Produtividade em escritório
- Tema escuro inspirado no app SentinelBR (mesmo autor)

**Modelo**:
- Distro construída como **container OCI** via [BlueBuild](https://blue-build.org)
- Publicada no GitHub Container Registry: `ghcr.io/andre28abr/vigiaos:latest`
- Instalada em qualquer Fedora Silverblue aarch64 via `rpm-ostree rebase`
- Atualizações automáticas atômicas (com rollback) via `rpm-ostree upgrade`

**Alvo de hardware**: **aarch64 apenas**. x86_64 foi deliberadamente descartado.
Apple Silicon (M1/M2/M3/M4) via UTM/Parallels é o ambiente primário; futuro
hardware ARM nativo é o destino final.

---

## 2. Decisões de arquitetura

| Decisão | Escolha | Razão |
|---|---|---|
| **Base** | `quay.io/fedora-ostree-desktops/silverblue:44` (oficial) | Cobertura aarch64 estável; alternativa uBlue tinha gaps |
| **Arquitetura** | aarch64 only | Convicção de que ARM é o futuro; simplifica CI |
| **Build framework** | BlueBuild | Menor fricção que `bootc` puro; migração futura é possível (formato compatível) |
| **Desktop** | GNOME (Silverblue) | Estabilidade > customização extrema; libadwaita aceita overrides via `@define-color` |
| **CI** | GitHub Actions, runner `ubuntu-24.04-arm` | Grátis para repo público; ARM nativo (sem QEMU emulation) |
| **Signing** | cosign com chave própria | Integridade end-to-end; chave pública no repo, privada como GitHub Secret |
| **Registry** | ghcr.io | Integrado ao GitHub, grátis para imagens públicas |
| **Theming** | libadwaita `@define-color` overrides via `/etc/xdg/gtk-4.0/gtk.css` | Único caminho funcional em GNOME 47+ (temas GTK custom desencorajados) |
| **Wallpaper** | SVG vetorial em `/usr/share/backgrounds/vigiaos/` | Escala para qualquer resolução; fácil de versionar |
| **Defaults de UI** | dconf system db (`/etc/dconf/db/local`) | Padrão GNOME para defaults com possibilidade de override do usuário |
| **Flatpak** | Sim, com Flathub (system scope + user scope) | Apps de usuário ficam fora do sistema atômico, atualizam independente |

### Por que NÃO `bootc` puro?
O modelo de container nativo (`bootc`) é o futuro do Fedora Atomic, mas exige
escrever `Containerfile` à mão e gerenciar publicação. BlueBuild usa exatamente
o mesmo formato OCI por baixo, mas adiciona DSL YAML e CI templates. Quando
quisermos mais controle, migrar é trivial.

### Por que NÃO uBlue?
[Universal Blue](https://universal-blue.org) tem ótima base mas a cobertura
aarch64 era incompleta no momento da decisão. Reavaliar quando ublue-os melhorar
ARM (vale verificar `ghcr.io/ublue-os/silverblue-main` periodicamente).

---

## 3. Estrutura do repositório

```
VigiaOS/
├── .github/
│   ├── workflows/
│   │   └── build.yml                # CI: builda imagem em ARM runner e publica
│   └── dependabot.yml               # PRs automáticos para atualizar Actions
│
├── recipes/
│   └── recipe.yml                   # DEFINIÇÃO DA IMAGEM (BlueBuild DSL)
│
├── files/                           # Tudo aqui é copiado para a imagem
│   ├── scripts/
│   │   ├── example.sh               # Placeholder do template (não usado)
│   │   └── setup-dconf.sh           # Roda `dconf update` no build
│   │
│   └── system/                      # files/system/* vira / na imagem final
│       ├── etc/
│       │   ├── dconf/
│       │   │   ├── profile/user     # Profile dconf (chains user-db + system-db)
│       │   │   └── db/local.d/
│       │   │       └── 00-vigiaos-defaults   # Defaults de UI (dark, accent, font)
│       │   └── xdg/
│       │       ├── gtk-3.0/gtk.css  # Overrides cores GTK3 (apps legados)
│       │       └── gtk-4.0/gtk.css  # Overrides @define-color libadwaita
│       │
│       └── usr/share/
│           └── backgrounds/vigiaos/
│               └── vigiaos-dark.svg # Wallpaper VigiaOS
│
├── modules/                         # Vazio (placeholder p/ módulos BlueBuild custom)
│
├── cosign.pub                       # Chave PÚBLICA cosign (committed)
├── cosign.key                       # Chave PRIVADA cosign (gitignored)
│
├── install.sh                       # Bootstrap one-liner para usuários
├── DEVELOPMENT.md                   # Este arquivo
├── README.md                        # README público (curto, para visitantes)
├── LICENSE                          # Apache 2.0 (herdado do template BlueBuild)
└── .gitignore
```

### Convenção crítica: `files/system/`

Tudo dentro de `files/system/` é copiado **literalmente** para `/` na imagem:
- `files/system/etc/foo/bar.conf` → `/etc/foo/bar.conf`
- `files/system/usr/share/baz.svg` → `/usr/share/baz.svg`

Não tem mágica. É um `rsync` recursivo no momento do build.

### Convenção: `files/scripts/`

Scripts executados durante o build da imagem (em contexto root, dentro do
container de build). Não vão para a imagem final — são apenas build steps.
Referenciados em `recipes/recipe.yml` via módulo `script`.

---

## 4. Pipeline de build

### Visão geral

```
push ao main
   ↓
GitHub Actions (ubuntu-24.04-arm)
   ↓
blue-build/github-action@v1.11
   ├─ Lê recipes/recipe.yml
   ├─ Pull da base (quay.io/fedora-ostree-desktops/silverblue:44)
   ├─ Aplica módulos na ordem: files → dnf → script → default-flatpaks
   ├─ Assina com cosign (chave privada do GitHub Secret)
   └─ Push para ghcr.io/andre28abr/vigiaos:latest
   ↓
Imagem assinada disponível para `rpm-ostree rebase`
```

### Triggers do build

```yaml
# .github/workflows/build.yml
on:
  schedule:
    - cron: "00 06 * * *"   # Diário às 06:00 UTC (~03:00 BRT)
  push:
    paths-ignore:           # Mudanças em docs não buildam
      - "**.md"
  pull_request:
  workflow_dispatch:        # Trigger manual via UI/CLI
```

### Concorrência

Apenas um build por vez. Push novo cancela build anterior em andamento:
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref || github.run_id }}
  cancel-in-progress: true
```

### Secrets necessários

| Secret | Conteúdo | Como criar |
|---|---|---|
| `SIGNING_SECRET` | Conteúdo do arquivo `cosign.key` | `gh secret set SIGNING_SECRET -R andre28abr/VigiaOS < cosign.key` |
| `GITHUB_TOKEN` | Token padrão do GH Actions | Automático (não precisa criar) |

### Permissões do workflow

Devem estar configuradas como `write` (necessário para push no GHCR):
```bash
gh api -X PUT repos/andre28abr/VigiaOS/actions/permissions/workflow \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

### Visibilidade do pacote GHCR

Após o primeiro build, o pacote `vigiaos` no GHCR é **privado por padrão**.
Para usuários poderem instalar sem `docker login`, precisa torná-lo público:
1. https://github.com/users/andre28abr/packages/container/vigiaos/settings
2. Danger Zone → Change visibility → Public

---

## 5. Sistema de tema

### Paleta

Portada do app **SentinelBR** (mesmo autor), que usa Tailwind CSS + shadcn/ui
com base color `zinc` e accent `emerald`.

| Token | Hex | Tailwind |
|---|---|---|
| `window_bg_color` | `#09090b` | zinc-950 |
| `view_bg_color` | `#0a0a0c` | (intermediário) |
| `card_bg_color` | `#18181b` | zinc-900 |
| `sidebar_bg_color` | `#050507` | (mais escuro) |
| `headerbar_border_color` | `#27272a` | zinc-800 |
| `window_fg_color` | `#fafafa` | zinc-50 |
| `accent_color` | `#34d399` | emerald-400 |
| `accent_bg_color` | `#10b981` | emerald-500 |
| `accent_fg_color` | `#052e16` | green-950 |
| `success_color` | `#34d399` | emerald-400 |
| `warning_color` | `#fbbf24` | amber-400 |
| `error_color` | `#f87171` | red-400 |

### Camadas (cascata)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. Wallpaper (.svg)                                              │
│    files/system/usr/share/backgrounds/vigiaos/vigiaos-dark.svg   │
│    Referenciado pelo dconf via picture-uri[-dark]                │
├──────────────────────────────────────────────────────────────────┤
│ 2. dconf defaults (sistema)                                      │
│    files/system/etc/dconf/db/local.d/00-vigiaos-defaults         │
│    Compilado por setup-dconf.sh durante o build                  │
│    - color-scheme='prefer-dark'                                  │
│    - accent-color='green'                                        │
│    - icon-theme='Papirus-Dark'                                   │
│    - monospace-font-name='JetBrainsMono Nerd Font 11'            │
│    - picture-uri[-dark]='file:///.../vigiaos-dark.svg'           │
├──────────────────────────────────────────────────────────────────┤
│ 3. libadwaita overrides via /etc/skel + sync                     │
│    files/system/etc/skel/.config/gtk-4.0/gtk.css                 │
│    files/system/etc/skel/.config/gtk-3.0/gtk.css                 │
│    Sincronizado para ~/.config/gtk-{3,4}.0/ por:                 │
│      /usr/libexec/vigiaos-sync-user-config                       │
│    Disparado por: /etc/profile.d/vigiaos-init.sh (no login)      │
└──────────────────────────────────────────────────────────────────┘
```

### ⚠️ Sobre o gtk.css: por que `/etc/skel/` e não `/etc/xdg/`

Tentativa anterior colocava o gtk.css em `/etc/xdg/gtk-4.0/gtk.css` confiando
no `$XDG_CONFIG_DIRS`. **GTK4/libadwaita não lê esse caminho** — só lê:
- Tema ativo em `/usr/share/themes/<nome>/gtk-4.0/gtk.css`
- CSS pessoal em `~/.config/gtk-4.0/gtk.css`

Como `/usr/share/themes/` exige um tema completo (não só overrides), e
libadwaita ignora a maioria dos temas custom, a única forma confiável de
aplicar `@define-color` em todos os apps é via `~/.config/gtk-4.0/gtk.css`.

**Solução**: ship em `/etc/skel/.config/gtk-{3,4}.0/gtk.css` (auto-aplica
para usuários novos via `useradd`) e um script de sync para os já existentes:

```bash
/usr/libexec/vigiaos-sync-user-config
# Cria symlinks em ~/.config/gtk-{3,4}.0/gtk.css apontando para /etc/skel/...
# Idempotente. Acionado automaticamente no primeiro login shell via
# /etc/profile.d/vigiaos-init.sh.
```

### Apps cobertos

- ✅ **Apps GNOME nativos / libadwaita**: Nautilus, Settings, Console,
  Calendar, Calculator, Software, Text Editor, About, etc.
- ⚠️ **GTK3 legados**: cobertos por `gtk-3.0/gtk.css` mas com diferenças sutis.
- ❌ **Flatpaks**: sandboxed, **não veem** `~/.config/gtk-4.0/`. Para libertar:
  ```bash
  flatpak override --user --filesystem=xdg-config/gtk-4.0:ro <app-id>
  ```
  Ou de uma vez para todos os Flatpaks do user:
  ```bash
  flatpak override --user --filesystem=xdg-config/gtk-4.0:ro
  ```

### Como mudar uma cor do tema

1. Edite `files/system/etc/skel/.config/gtk-4.0/gtk.css` (e `gtk-3.0/gtk.css`)
2. Commit + push → CI builda nova imagem
3. Na VM: `rpm-ostree upgrade && systemctl reboot`
4. O symlink `~/.config/gtk-4.0/gtk.css → /etc/skel/...` é estável, então
   reload do app (ou logout/login) já pega a mudança nova

### Gotchas conhecidos

- **dconf defaults só pegam em chaves nunca tocadas pelo usuário.** Se já
  mexeu manualmente, o valor pessoal sobrescreve. Para forçar reset:
  ```bash
  dconf reset /org/gnome/desktop/interface/color-scheme
  ```
- **libadwaita não suporta temas GTK custom completos.** Só `@define-color` e
  algumas regras CSS limitadas. Não tente reescrever Adwaita do zero.
- **Cache de cosign/skopeo no GHCR pode confundir.** Após push, espera o build
  terminar (`gh run watch`) antes de `rpm-ostree upgrade` na VM.

---

## 5b. Terminal customizado (Nerd Font + Starship + zsh)

VigiaOS empacota um setup de terminal "Powerline-style" similar ao Kali:
fontes com glyphs (git branch, ícones de OS, separadores), prompt rico e
shell zsh com syntax highlighting e autosuggestions.

### Componentes

| Peça | Origem | Path |
|---|---|---|
| **JetBrainsMono Nerd Font** | Download direto do release no build | `/usr/share/fonts/nerd-fonts-jetbrains-mono/` |
| **Starship** | RPM Fedora | `/usr/bin/starship` |
| **Config do Starship** | Versionada no repo | `/etc/starship.toml` |
| **zsh + plugins** | RPM Fedora (`zsh`, `zsh-autosuggestions`, `zsh-syntax-highlighting`) | `/usr/bin/zsh` |
| **.zshrc default** | Template em `/etc/skel/` | `~/.zshrc` (auto p/ novos users) |
| **Starship em bash** | profile.d hook | `/etc/profile.d/vigiaos-starship.sh` |

### Por que download direto de Nerd Fonts em vez de COPR?

A COPR `che/nerd-fonts` existe mas a cobertura aarch64 é incerta. O script
`files/scripts/install-nerd-fonts.sh` baixa o `.tar.xz` direto do release
oficial em `github.com/ryanoasis/nerd-fonts`, mais simples e confiável.

### Mudar default shell para zsh (usuário existente)

Usuários criados ANTES do recipe incluir zsh não ganham zsh automático.
Para mudar:
```bash
chsh -s /usr/bin/zsh
# logout/login para aplicar
```

Novos usuários criados via `useradd` ganham zsh se `/etc/default/useradd`
estiver setado (não setamos por padrão — ainda é debate se queremos).

### Customizar o prompt

`/etc/starship.toml` é versionado no repo (em `files/system/etc/starship.toml`).
Para customizar pessoalmente sem mexer no sistema, copie para `~/.config/`:
```bash
cp /etc/starship.toml ~/.config/starship.toml
# Starship dá prioridade ao do usuário
```

---

## 6. Instalação e atualização

### Para usuários novos (qualquer Fedora Silverblue aarch64)

**One-liner**:
```bash
curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install.sh | bash
```

**Manualmente** (mesmo efeito):
```bash
rpm-ostree rebase ostree-unverified-registry:ghcr.io/andre28abr/vigiaos:latest
systemctl reboot -i
```

A primeira instalação usa `ostree-unverified-registry:` porque o sistema do
usuário ainda não tem a chave pública cosign instalada. **Após o primeiro
boot no VigiaOS**, a chave fica em `/etc/pki/containers/` e atualizações
futuras podem usar `ostree-image-signed:docker://` para verificação.

### Atualizações

Quando já está no VigiaOS:
```bash
rpm-ostree upgrade
systemctl reboot
```

GNOME Software também checa updates automaticamente em background.

### Rollback

Se um update quebrar algo, no menu do GRUB selecione a deployment anterior.
Ou via CLI:
```bash
rpm-ostree rollback
systemctl reboot
```

---

## 7. Operações comuns

### Adicionar um pacote RPM

Editar `recipes/recipe.yml`, no módulo `dnf.install.packages`:

```yaml
- type: dnf
  install:
    packages:
      - micro
      - htop
      - tmux
      - SEU_PACOTE_AQUI       # ← adicionar
```

Importante: verificar que o pacote existe para aarch64 no Fedora 44:
```bash
dnf --releasever=44 --forcearch=aarch64 info nome-do-pacote
```

### Adicionar um Flatpak default

```yaml
- type: default-flatpaks
  configurations:
    - notify: true
      scope: system
      install:
        - com.github.tchx84.Flatseal
        - org.libreoffice.LibreOffice    # ← adicionar
        - org.signal.Signal              # ← exemplo
```

### Mudar wallpaper

1. Substituir `files/system/usr/share/backgrounds/vigiaos/vigiaos-dark.svg`
2. Se mudar o nome do arquivo, atualizar referências em
   `files/system/etc/dconf/db/local.d/00-vigiaos-defaults`

### Adicionar uma config de aplicação (ex: gnome-terminal/ptyxis profile)

1. Identificar o schema dconf (`gsettings list-schemas | grep -i nome-app`)
2. Pegar o valor exato com `dconf dump /caminho/do/schema/`
3. Colar em `files/system/etc/dconf/db/local.d/00-vigiaos-defaults`

### Mudar versão da Fedora base

Editar `recipes/recipe.yml`:
```yaml
base-image: quay.io/fedora-ostree-desktops/silverblue
image-version: 45        # ← bump
```

**Cuidado**: mudança de major version pode trazer breaking changes em pacotes
e dconf schemas. Faça em PR separado e teste antes de mergear na main.

### Forçar rebuild via CLI

```bash
gh workflow run build.yml -R andre28abr/VigiaOS
```

### Ver logs do último build

```bash
gh run list -R andre28abr/VigiaOS --limit 5
gh run view <RUN_ID> -R andre28abr/VigiaOS --log
gh run view <RUN_ID> -R andre28abr/VigiaOS --log-failed   # só falhas
```

### Verificar assinatura cosign de uma imagem

```bash
cosign verify --key cosign.pub --insecure-ignore-tlog ghcr.io/andre28abr/vigiaos:latest
```

### Resetar settings dconf no usuário atual (forçar defaults do VigiaOS)

```bash
dconf reset -f /org/gnome/desktop/interface/
dconf reset -f /org/gnome/desktop/background/
# logout/login ou reboot
```

---

## 8. Log de implementação

> Ordem cronológica. Adicionar entrada a cada milestone.

### 2026-05-20 — Bootstrap do projeto
- Repositório criado em https://github.com/andre28abr/VigiaOS (público)
- Scaffolding inicial copiado de `github.com/blue-build/template`
- Workflow ajustado para `ubuntu-24.04-arm` (ARM nativo)
- `maximize_build_space` desabilitado (script x86-only quebra em ARM)
- Base trocada para `quay.io/fedora-ostree-desktops/silverblue:44`
- Recipe mínimo: `micro`, `htop`, `tmux`, Flatseal

### 2026-05-21 — Signing + primeiro build verde
- Gerada par de chaves cosign (`cosign generate-key-pair`, senha vazia)
- `cosign.pub` commitado, `cosign.key` no .gitignore + GitHub Secret `SIGNING_SECRET`
- Workflow permissions configurada para `write`
- Fix: descrição multi-linha em recipe quebrava parser de Containerfile
  (YAML `|` block scalar virava LABEL inválido) — trocado para single line
- Primeiro build verde: 4m56s, imagem `ghcr.io/andre28abr/vigiaos:latest`
- Rebase testado em VM Silverblue aarch64 (UTM, Apple Virtualization backend)

### 2026-05-21 — Tema escuro (iteração 1)
- Wallpaper SVG vetorial com paleta SentinelBR (zinc + emerald)
- dconf defaults: `color-scheme=prefer-dark`, `accent-color=green`,
  `monospace-font-name=JetBrains Mono 11`, wallpaper apontando para o SVG
- Pacotes adicionados: `papirus-icon-theme`, `jetbrains-mono-fonts`, `gnome-tweaks`
- Script `setup-dconf.sh` roda `dconf update` no build
- Fix: nome de fonte estava `JetBrainsMono Nerd Font 11` (não existia no pacote);
  trocado para `JetBrains Mono 11` (espaçamento de letras voltou ao normal)
- `/etc/xdg/gtk-4.0/gtk.css` + `gtk-3.0/gtk.css` com overrides @define-color
  para libadwaita (Nautilus, Settings, Console, Calendar, etc.)

### 2026-05-21 — UX de instalação + docs
- Script `install.sh` adicionado para one-liner `curl | bash`
- `DEVELOPMENT.md` criado (este arquivo)

### 2026-05-21 — Theme fix + terminal Powerline (iteração 2)
- **Bug crítico do tema corrigido**: `gtk.css` estava em `/etc/xdg/gtk-4.0/`
  mas GTK4/libadwaita **não lê** `$XDG_CONFIG_DIRS` — só lê `~/.config/gtk-4.0/`
  e themes em `/usr/share/themes/`. Solução: arquivos movidos para
  `/etc/skel/.config/gtk-{3,4}.0/` + script `/usr/libexec/vigiaos-sync-user-config`
  cria symlinks em `~/.config/` automaticamente no primeiro login (via hook
  em `/etc/profile.d/vigiaos-init.sh`).
- **JetBrainsMono Nerd Font** baixada direto do release oficial via
  `files/scripts/install-nerd-fonts.sh` (instalada em `/usr/share/fonts/`).
- **Starship** adicionado como prompt; config em `/etc/starship.toml` com
  paleta SentinelBR (emerald accent), Powerline-style com Nerd Font glyphs,
  detecção de git/python/node/rust/go/docker.
- **zsh** + `zsh-syntax-highlighting` + `zsh-autosuggestions` adicionados;
  `.zshrc` default em `/etc/skel/` inicializa starship, aliases comuns,
  histórico compartilhado, completion case-insensitive.
- **Bash fallback** via `/etc/profile.d/vigiaos-starship.sh` (init starship
  em bash interativo se o user ainda não migrou para zsh).
- **Papirus-Dark** setado como `icon-theme` no dconf default.
- **Monospace font** atualizado para `JetBrainsMono Nerd Font 11` no dconf.

---

## 9. Roadmap

### Fase A — Stack de segurança e auditoria (próximo)
**Objetivo**: tornar VigiaOS imediatamente útil para auditoria/forense.

Pacotes RPM a adicionar em `recipes/recipe.yml`:
- `lynis` — auditoria de sistema
- `aide` — file integrity monitoring
- `fail2ban` — proteção contra brute force
- `chkrootkit`, `rkhunter` — detecção de rootkits
- `clamav`, `clamav-update` — antivírus
- `wireshark-cli` — análise de rede (CLI; GUI via Flatpak)
- `nmap`, `tcpdump` — scan/captura de rede
- `tor`, `torsocks` — anonimização
- `gnupg2` (provavelmente já presente, mas explicitar)

Considerações:
- `aide --init` precisa rodar pós-instalação para criar baseline. Não no build.
- `fail2ban` exige systemd unit habilitada. Adicionar via tweaks/services no recipe.
- ClamAV update é custoso — não rodar `freshclam` no build (timer faz isso depois).

### Fase B — Apps de escritório (Flatpaks)
- `org.libreoffice.LibreOffice`
- `org.mozilla.Thunderbird`
- `org.keepassxc.KeePassXC`
- `org.signal.Signal`
- `net.cozic.joplin_desktop` — notes com criptografia
- `org.standardnotes.standardnotes` — alternativa

### Fase C — Empacotar SentinelBR
SentinelBR é app web (Tailwind + React + shadcn/ui) com backend Go. Opções:
- **Flatpak** com WebView (mais aderente ao modelo atômico) — preferido
- **AppImage** — menos integrado mas mais simples
- **RPM próprio** — mais trabalho, melhor integração desktop

Decisão pendente de discussão com o autor (André).

### Fase D — Polish do tema
- Custom profile do terminal (Console / Ptyxis) com paleta zinc + emerald
- GDM theme (login screen escuro)
- Plymouth boot splash com logo VigiaOS
- Logo/icon do sistema (substitui o "Fedora" em sobre)
- Refinar wallpaper (versão "produção" vs "dev")

### Fase E — Hardening
- SELinux em modo enforcing (já é padrão Fedora) — auditar contextos
- `firewalld` zones específicas (default já é `FedoraWorkstation`, considerar `public`)
- Configurar `auditd` com regras LGPD-relevantes
- Desabilitar serviços não usados (telemetria, geolocalização)
- `kernel-cmdline` tweaks (page_poison, slab_nomerge, etc.)
- Considerar imagem assinada com `ostree-image-signed:` (já temos cosign, falta policy)

### Fase F — Distribuição
- ISO instalável (via `bluebuild generate-iso` ou `bootc-image-builder`)
- GitHub Release com checksums
- Site simples (GitHub Pages?) com instruções

### Fase G — Parallels Tools (se necessário)
- Investigar COPR community para `parallels-tools` aarch64
- Ou empacotar como RPM próprio dentro do build
- Atualmente: rodar sem (perde clipboard nativo e shared folders Parallels;
  UTM cobre o caso de uso primário)

---

## 10. Troubleshooting

### Build falha: `Unable to find private/public key pair`
**Causa**: BlueBuild exige par cosign por padrão.
**Fix**:
```bash
COSIGN_PASSWORD="" cosign generate-key-pair      # senha vazia para CI
gh secret set SIGNING_SECRET -R andre28abr/VigiaOS < cosign.key
git add cosign.pub && git commit && git push
# cosign.key fica gitignored
```

### Build falha: `unknown instruction: <palavra>` no Containerfile
**Causa**: provavelmente descrição multi-linha em `recipes/recipe.yml`
(YAML `|` block scalar) virou um LABEL Docker multi-linha inválido.
**Fix**: usar descrição em uma linha só (sem `|`).

### Build falha: `Transaction in progress` ao rodar `rpm-ostree`
**Causa**: GNOME Software disparou upgrade em paralelo.
**Fix**: esperar (`rpm-ostree status` mostrando `State: idle`) ou
`rpm-ostree cancel`.

### Reboot bloqueado por inhibitor
```
Operation inhibited by "andre" (...) "user session inhibited"
```
**Fix**: `systemctl reboot -i` (ignore inhibitors). Ou reboot pela UI do GNOME.

### `skopeo inspect` retorna 403 Forbidden
**Causa**: o pacote GHCR está privado (default).
**Fix**: tornar público em
https://github.com/users/andre28abr/packages/container/vigiaos/settings →
Danger Zone → Change visibility → Public.

### Letter-spacing estranho no terminal
**Causa**: `monospace-font-name` apontando para fonte que não existe (fallback
estranho do GTK).
**Fix**: garantir que o nome bate exatamente com o instalado. Para o pacote
`jetbrains-mono-fonts` da Fedora, o nome correto é `JetBrains Mono` (NÃO
`JetBrainsMono Nerd Font` — o sufixo "Nerd Font" só existe em pacotes da
NerdFonts upstream, que não estão nos repos da Fedora).

Live fix sem rebuild:
```bash
gsettings set org.gnome.desktop.interface monospace-font-name 'JetBrains Mono 11'
```

### Tema GTK não aparece em apps Flatpak
**Causa**: Flatpak sandbox não vê `~/.config/` do host por padrão.
**Fix global** (afeta todos os Flatpaks do user):
```bash
flatpak override --user --filesystem=xdg-config/gtk-4.0:ro
flatpak override --user --filesystem=xdg-config/gtk-3.0:ro
```
**Fix por app** (mais conservador):
```bash
flatpak override --user --filesystem=xdg-config/gtk-4.0:ro <app-id>
```

### Tema GTK não aparece nem em apps nativos após rebase
**Causa provável**: o symlink `~/.config/gtk-4.0/gtk.css` não foi criado.
**Diagnóstico**:
```bash
ls -la ~/.config/gtk-4.0/gtk.css        # deve ser symlink para /etc/skel/...
```
**Fix manual** (também roda automaticamente no próximo login shell):
```bash
/usr/libexec/vigiaos-sync-user-config
# Logout/login para libadwaita recarregar
```

### Letter-spacing estranho no terminal (resolvido em 2026-05-21)
**Histórico**: monospace-font-name apontava para `JetBrainsMono Nerd Font`
mas o pacote `jetbrains-mono-fonts` instalava só `JetBrains Mono` (sem
glyphs Nerd). Agora a Nerd Font está instalada via
`files/scripts/install-nerd-fonts.sh` e o nome bate.

### Cores do tema parecem não terem aplicado em alguns apps após rebase
**Causa**: GNOME Shell ou apps já abertos têm CSS em cache.
**Fix**: logout completo (não só fechar apps) e login de novo, ou reboot.

### `dconf update` falha no build
**Causa**: provavelmente sintaxe inválida no arquivo de defaults (`.d/00-...`).
**Fix**: validar localmente:
```bash
# Em qualquer sistema com dconf:
sudo cp 00-vigiaos-defaults /etc/dconf/db/local.d/
sudo dconf update                                    # vai dar erro detalhado
```

### Imagem não atualiza com `rpm-ostree upgrade`
**Causa**: a) sem internet, b) cached digest aponta para versão atual,
c) pacote GHCR voltou a ser privado.
**Diagnóstico**:
```bash
rpm-ostree status
skopeo inspect docker://ghcr.io/andre28abr/vigiaos:latest
```
Compara o digest do `status` com o do `inspect`. Se forem diferentes mas
`upgrade` não puxa, force:
```bash
rpm-ostree update --check        # mostra o que está disponível
rpm-ostree upgrade --check       # alias
```

---

## Apêndice: comandos de referência rápida

```bash
# CI
gh run list -R andre28abr/VigiaOS --limit 5
gh run watch <ID> -R andre28abr/VigiaOS
gh workflow run build.yml -R andre28abr/VigiaOS
gh secret set SIGNING_SECRET -R andre28abr/VigiaOS < cosign.key

# Sistema (na VM Silverblue/VigiaOS)
rpm-ostree status
rpm-ostree upgrade
rpm-ostree rollback
rpm-ostree rebase ostree-unverified-registry:ghcr.io/andre28abr/vigiaos:latest
systemctl reboot -i

# Tema (live, sem rebuild)
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark'
gsettings set org.gnome.desktop.interface accent-color 'green'
gsettings set org.gnome.desktop.interface monospace-font-name 'JetBrains Mono 11'

# Verificar assinatura
cosign verify --key cosign.pub --insecure-ignore-tlog ghcr.io/andre28abr/vigiaos:latest
```
