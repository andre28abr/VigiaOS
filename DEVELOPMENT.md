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
┌─────────────────────────────────────────────────────────┐
│ 1. Wallpaper (.svg)                                     │
│    files/system/usr/share/backgrounds/vigiaos/          │
│    Referenciado via dconf: picture-uri-dark             │
├─────────────────────────────────────────────────────────┤
│ 2. dconf defaults                                       │
│    files/system/etc/dconf/db/local.d/00-vigiaos-defaults│
│    Compilado por `dconf update` no build                │
│    - color-scheme='prefer-dark'                         │
│    - accent-color='green'                               │
│    - monospace-font-name='JetBrains Mono 11'            │
│    - picture-uri[-dark]='file:///...'                   │
├─────────────────────────────────────────────────────────┤
│ 3. libadwaita overrides (apps GNOME nativos)            │
│    files/system/etc/xdg/gtk-4.0/gtk.css                 │
│    @define-color de window_bg_color, accent_color, ...  │
│    Lido por GTK4 via $XDG_CONFIG_DIRS                   │
├─────────────────────────────────────────────────────────┤
│ 4. GTK3 fallback (apps legados)                         │
│    files/system/etc/xdg/gtk-3.0/gtk.css                 │
│    @define-color de theme_bg_color, theme_fg_color, ... │
└─────────────────────────────────────────────────────────┘
```

### Apps cobertos

- ✅ **Cobertos** (apps GNOME nativos / libadwaita): Nautilus, Settings, Console,
  Calendar, Files, Calculator, Software, Text Editor, About, Login Manager
- ⚠️ **Parcial** (apps GTK3): cobertos pelos overrides GTK3 mas com diferenças
  visuais sutis (libadwaita tem mais tokens que GTK3 não tem)
- ❌ **NÃO cobertos** (Flatpaks): sandboxed, não veem `/etc/xdg/`. Workarounds:
  - `flatpak override --user --filesystem=xdg-config/gtk-4.0:ro <app>` (por app)
  - Ou copiar para `~/.config/gtk-4.0/gtk.css` (afeta todos Flatpaks do usuário)

### Como mudar uma cor

1. Edite `files/system/etc/xdg/gtk-4.0/gtk.css` (e/ou `gtk-3.0/gtk.css`)
2. Commit + push
3. CI builda nova imagem
4. Usuário roda `rpm-ostree upgrade && systemctl reboot`

### Gotchas conhecidos

- **dconf defaults só pegam em chaves nunca tocadas pelo usuário.** Se o user
  já mexeu manualmente, o valor pessoal sobrescreve. Para forçar:
  `dconf reset /org/gnome/desktop/interface/color-scheme`
- **libadwaita não suporta temas GTK custom completos.** Só `@define-color` e
  algumas regras CSS limitadas. Não tente reescrever Adwaita do zero.
- **Mudanças em `.svg` de wallpaper podem precisar de cache flush** se o
  arquivo tem o mesmo nome. Usar versionamento no nome se quiser garantir.

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
**Causa**: Flatpak sandbox não vê `/etc/xdg/`.
**Fix opcional**: copiar para `~/.config/gtk-4.0/gtk.css`:
```bash
mkdir -p ~/.config/gtk-4.0
cp /etc/xdg/gtk-4.0/gtk.css ~/.config/gtk-4.0/gtk.css
```
Ou expor sob demanda por app:
```bash
flatpak override --user --filesystem=xdg-config/gtk-4.0:ro <app-id>
```

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
