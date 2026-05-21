#!/usr/bin/env bash
#
# install-nerd-fonts.sh
#
# Baixa JetBrainsMono Nerd Font (fonte com glyphs extras de git, OS, etc.)
# direto do release do projeto. Mais confiavel que depender de COPR
# (que pode nao buildar para aarch64).
#
# Roda em contexto root no container de build.

set -oue pipefail

NERD_VER="${NERD_VER:-3.2.1}"
FONT="JetBrainsMono"
DEST="/usr/share/fonts/nerd-fonts-jetbrains-mono"

echo "==> Instalando ${FONT} Nerd Font v${NERD_VER}"

mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl -fsSL --retry 3 -o "$TMP/${FONT}.tar.xz" \
    "https://github.com/ryanoasis/nerd-fonts/releases/download/v${NERD_VER}/${FONT}.tar.xz"

tar -xJf "$TMP/${FONT}.tar.xz" -C "$DEST" --no-same-owner

# Mantem so as Regular/Bold/Italic principais; remove variantes raras
find "$DEST" -name '*Propo*.ttf' -delete 2>/dev/null || true
find "$DEST" -name '*Mono*.ttf' -delete 2>/dev/null || true  # variante "Mono" sem ligaduras
find "$DEST" -name 'LICENSE*' -o -name 'README*' -delete 2>/dev/null || true

# Atualiza cache (best-effort — fc-cache pode falhar em container sem display)
fc-cache -f "$DEST" 2>/dev/null || true

echo "==> Fontes instaladas em ${DEST}:"
ls -1 "$DEST" | head -20
