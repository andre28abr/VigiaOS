#!/usr/bin/env bash
#
# uninstall.sh — remove o VigiaOS do usuário (sem precisar reinstalar a VM).
#
# Por PADRÃO remove só o que o Vigia colocou no SEU usuário:
#   - pacotes pip (vigia-*), atalhos .desktop + ícones, a pasta "Vigia" do
#     menu do GNOME, e o estado em ~/.config/vigia* e ~/.local/share/vigia*.
# NÃO remove os backends de sistema (lynis/clamav/aide/…) nem os Flatpaks —
# eles são reaproveitados numa reinstalação. Use as flags pra remover também.
#
# Uso:
#   install/uninstall.sh             # remove o Vigia (pip + ícones + estado)
#   install/uninstall.sh --backends  # também: dnf remove os backends CLI +
#                                     # stack do Blue (yara/suricata/volatility3/
#                                     # plaso/avml/dwarf2json/vigia-log)
#   install/uninstall.sh --flatpaks  # também: remove os Flatpaks de privacidade
#   install/uninstall.sh --all       # backends + Blue + flatpaks (wipe total)
#   install/uninstall.sh --dry-run   # só mostra o que faria
#
set -uo pipefail
export PIP_BREAK_SYSTEM_PACKAGES=1

GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BOLD=$'\e[1m'; DIM=$'\e[2m'; NC=$'\e[0m'
info() { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
ok()   { echo "  ${GREEN}✓${NC} $*"; }
warn() { echo "  ${YELLOW}!${NC} $*"; }

DO_BACKENDS=0; DO_FLATPAKS=0; DRY=0
for a in "$@"; do
    case "$a" in
        --backends)   DO_BACKENDS=1 ;;
        --flatpaks)   DO_FLATPAKS=1 ;;
        --all)        DO_BACKENDS=1; DO_FLATPAKS=1 ;;
        -n|--dry-run) DRY=1 ;;
        -h|--help)    sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) warn "opção desconhecida: $a" ;;
    esac
done
run() { if [ $DRY -eq 1 ]; then echo "  ${DIM}\$ $*${NC}"; else "$@"; fi; }

APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# 1) pacotes pip (vigia-*) — descobre dinamicamente o que está instalado
info "Removendo pacotes pip (vigia-*)..."
mapfile -t PKGS < <(python3 -m pip list 2>/dev/null | awk 'tolower($1) ~ /^vigia/ {print $1}')
if [ ${#PKGS[@]} -gt 0 ]; then
    run python3 -m pip uninstall -y "${PKGS[@]}" >/dev/null && ok "removidos: ${PKGS[*]}"
else
    ok "nenhum pacote vigia-* instalado."
fi

# 2) atalhos .desktop + ícones + entry-points soltos
info "Removendo atalhos e ícones do GNOME..."
run rm -f "$APPS_DIR"/br.com.vigia.*.desktop
run rm -f "$ICONS_DIR"/br.com.vigia.*.svg
run rm -f "$HOME"/.local/bin/vigia-*
# overrides NoDisplay de backends (chkrootkit etc.) — restaura o padrão do pacote
for app in chkrootkit; do
    if [ -f "$APPS_DIR/$app.desktop" ] && grep -q "NoDisplay=true" "$APPS_DIR/$app.desktop" 2>/dev/null; then
        run rm -f "$APPS_DIR/$app.desktop"
    fi
done
ok "atalhos/ícones removidos."

# 3) pasta "Vigia" do grid do GNOME
if command -v gsettings >/dev/null 2>&1; then
    info "Removendo a pasta 'Vigia' do menu..."
    SCHEMA="org.gnome.desktop.app-folders"
    if [ $DRY -eq 0 ]; then
        gsettings reset-recursively \
            "$SCHEMA.folder:/org/gnome/desktop/app-folders/folders/Vigia/" 2>/dev/null || true
        kids=$(gsettings get "$SCHEMA" folder-children 2>/dev/null || echo "[]")
        if [[ "$kids" == *"'Vigia'"* ]]; then
            kids=$(python3 -c "import sys,ast; print(repr([x for x in ast.literal_eval(sys.argv[1]) if x!='Vigia']))" "$kids" 2>/dev/null)
            [ -n "$kids" ] && gsettings set "$SCHEMA" folder-children "$kids" 2>/dev/null || true
        fi
    fi
    ok "pasta 'Vigia' removida."
fi

# 4) estado local
info "Removendo estado local (~/.config/vigia*, ~/.local/share/vigia*)..."
run rm -rf "$HOME"/.config/vigia "$HOME"/.config/vigia-* "$HOME"/.local/share/vigia-*
ok "estado removido."

# 5) caches do GNOME
if [ $DRY -eq 0 ]; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
    gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

# 6) OPCIONAL: backends de sistema (dnf) + stack forense/SOC do VigiaBlue
if [ $DO_BACKENDS -eq 1 ]; then
    info "Removendo backends de sistema (dnf)..."
    BACKENDS=(lynis aide chkrootkit rkhunter clamav clamav-update nethogs
              fail2ban dnscrypt-proxy md5deep
              yara suricata tcpdump)            # + stack do VigiaBlue
    run sudo dnf remove -y "${BACKENDS[@]}" || warn "alguns backends não removidos."
    # forense via pipx + binários soltos + core Rust do Activity Log/SIEM
    if command -v pipx >/dev/null 2>&1; then
        run pipx uninstall volatility3 2>/dev/null || true
        run pipx uninstall plaso 2>/dev/null || true
    fi
    run rm -f "$HOME"/.local/bin/avml "$HOME"/.local/bin/dwarf2json
    [ -x /usr/local/bin/vigia-log ] && run sudo rm -f /usr/local/bin/vigia-log
    ok "backends + stack do Blue removidos."
fi

# 7) OPCIONAL: Flatpaks de privacidade
if [ $DO_FLATPAKS -eq 1 ]; then
    info "Removendo Flatpaks de privacidade..."
    for fp in com.github.tchx84.Flatseal org.keepassxc.KeePassXC org.signal.Signal \
              com.github.micahflee.torbrowser-launcher org.mozilla.Thunderbird; do
        run flatpak uninstall --user -y "$fp" 2>/dev/null || true
    done
fi

echo
info "Pronto. Vigia removido do usuário."
[ $DO_BACKENDS -eq 0 ] && echo "${DIM}Backends de sistema mantidos (reaproveitados). Use --backends pra removê-los.${NC}"
echo "${DIM}Reinstalar:  install/bootstrap.sh  (ou o comando curl do README).${NC}"
