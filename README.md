# VigiaOS &nbsp; [![bluebuild](https://github.com/andre28abr/VigiaOS/actions/workflows/build.yml/badge.svg)](https://github.com/andre28abr/VigiaOS/actions/workflows/build.yml)

Fedora Atomic customizada para uso pessoal — foco em **segurança**, **LGPD**, **auditoria**, e ferramentas para escritório de advocacia. Construída sobre Fedora Silverblue com tema escuro.

> [!IMPORTANT]
> aarch64 (ARM 64-bit) apenas. Pensada para rodar em Apple Silicon via UTM/Parallels e, futuramente, hardware ARM nativo.

## Status

Em desenvolvimento inicial. O recipe atual instala apenas pacotes mínimos (`micro`, `htop`, `tmux`) e o Flatpak Flatseal para validar o pipeline. Stack de segurança/auditoria e tema entram em iterações seguintes.

## Instalação (rebase a partir de Fedora Silverblue aarch64 limpo)

Em uma instalação Silverblue aarch64 já existente, rebaseie para a imagem do VigiaOS:

```bash
rpm-ostree rebase ostree-unverified-registry:ghcr.io/andre28abr/vigiaos:latest
systemctl reboot
```

A partir daí, atualizações são automáticas via `rpm-ostree upgrade`.

## Estrutura do repositório

```
recipes/recipe.yml          # definição da imagem (pacotes, flatpaks, base)
files/system/               # arquivos copiados para / na imagem
  ├── etc/                  # configs do sistema
  └── usr/                  # binários, temas, ícones, dados compartilhados
files/scripts/              # scripts executados durante o build
modules/                    # módulos BlueBuild custom
.github/workflows/build.yml # CI: builda no GitHub Actions ARM runner
```

## Build

O build roda automaticamente via GitHub Actions:
- A cada push em `main`
- Diariamente às 06:00 UTC
- Manualmente via *Actions → bluebuild → Run workflow*

A imagem é publicada em `ghcr.io/andre28abr/vigiaos:latest`.
