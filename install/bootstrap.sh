#!/usr/bin/env bash
#
# VigiaOS — bootstrap único (auto-detecta a plataforma)
#
# Instala a suíte VigiaOS completa numa instalação Fedora limpa:
#   - Detecta se é Fedora Atomic (Silverblue/Kinoite/…) ou Workstation
#     tradicional e usa rpm-ostree ou dnf automaticamente.
#   - Instala as dependências de runtime (GTK4) + os backends CLI que as
#     ferramentas wrappam (lynis, aide, clamav, …).
#   - Clona o repo, instala as 16 ferramentas (pip --user) e registra
#     atalhos + ícones no menu do GNOME.
#   - Instala Flatpaks de privacidade (KeePassXC, Signal, Tor Browser…).
#
# **NÃO liga nenhum serviço.** tor, fail2ban e dnscrypt-proxy ficam
# DESLIGADOS — você ativa cada um na ferramenta correspondente quando
# quiser (princípio de minimum surface area / LGPD).
#
# Uso (instalação limpa):
#   curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install/bootstrap.sh | bash
#
# Ou, se já clonou o repo:
#   ./install/bootstrap.sh
#
# Para instalar só UM módulo (ex: só o Antivírus), use install/install-tool.sh.
#
set -euo pipefail

REPO_URL="https://github.com/andre28abr/VigiaOS"
CLONE_DIR="${VIGIA_DIR:-$HOME/dev/VigiaOS}"

# ---- visual ---------------------------------------------------------------
GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'
DIM=$'\e[2m'; BOLD=$'\e[1m'; ACCENT=$'\e[38;5;42m'; NC=$'\e[0m'
info()  { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
warn()  { echo "${YELLOW}!! ${NC} $*"; }
fail()  { echo "${RED}xx ${NC} $*" >&2; }
hr()    { echo "${DIM}--------------------------------------------------${NC}"; }

# ---- detecta plataforma ---------------------------------------------------
if [ -f /run/ostree-booted ]; then
    ATOMIC=1; PLATFORM="Fedora Atomic (Silverblue/Kinoite/…)"; PM="rpm-ostree"
else
    ATOMIC=0; PLATFORM="Fedora Workstation (tradicional)"; PM="dnf"
fi

cat <<BANNER

${ACCENT}  VIGIA${NC}${BOLD}OS${NC}  ${DIM}|  suite de seguranca / privacidade / auditoria${NC}
  ${DIM}Plataforma detectada: ${PLATFORM} (${PM})${NC}
  ${DIM}${REPO_URL}${NC}

BANNER

# ---- pacotes --------------------------------------------------------------
# Runtime GUI (GTK4) + ferramentas pra instalar via pip. Em Silverblue a
# maioria ja' vem na imagem base — rpm-ostree/dnf sao idempotentes.
DEPS_CORE=(git python3-pip python3-gobject gtk4 libadwaita)

# Backends CLI que as ferramentas Vigia wrappam. INSTALA, mas NAO LIGA
# servico nenhum (tor/fail2ban/dnscrypt ficam off — opt-in nas tools).
DEPS_BACKENDS=(
    lynis aide chkrootkit rkhunter        # auditoria / rootkits
    clamav clamav-update                  # antivirus
    mtr nethogs iftop                     # rede (diagnostico)
    lsof strace                           # debug
    fail2ban                              # defesa (servico — fica OFF)
    tor torsocks wireguard-tools          # privacidade (tor fica OFF)
    dnscrypt-proxy                        # DNS encriptado (fica OFF)
    hashdeep                              # forense
)

# Ferramentas Vigia (dirs em tools/). vigia-common primeiro (dep das outras).
VIGIA_TOOLS=(
    vigia-common
    vigia-hub dashboard activity-log-gui privacy-controls dns-manager
    selinux-gui firewall-gui netmon-gui hardening-checks reports
    file-integrity tool-installer capabilities-inspector rootkit-scanner
    antivirus deployments-manager
)

# Flatpaks de privacidade/produtividade (escopo user). Opcional, mas curado.
FLATPAKS=(
    com.github.tchx84.Flatseal                  # gerenciador de permissoes Flatpak
    org.keepassxc.KeePassXC                     # gerenciador de senhas local
    org.signal.Signal                           # mensageria E2EE
    com.github.micahflee.torbrowser-launcher    # Tor Browser
    org.mozilla.Thunderbird                     # email
)

# ---- localiza o repo (clone existente ou vamos clonar) --------------------
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]:-}")" 2>/dev/null && pwd || echo "")
if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/../tools" ]; then
    REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)   # rodando de dentro do clone
    CLONE_NEEDED=0
else
    REPO_DIR="$CLONE_DIR"                      # curl|bash: clonar depois
    CLONE_NEEDED=1
fi

# ---- preview --------------------------------------------------------------
hr
info "Vai instalar (${PM}):"
echo "  ${DIM}runtime:${NC}  ${DEPS_CORE[*]}"
echo "  ${DIM}backends:${NC} ${DEPS_BACKENDS[*]}"
echo "  ${DIM}tools:${NC}    ${#VIGIA_TOOLS[@]} ferramentas Vigia (pip --user) + atalhos no GNOME"
echo "  ${DIM}flatpaks:${NC} ${FLATPAKS[*]}"
echo
warn "Nenhum servico sera LIGADO (tor/fail2ban/dnscrypt off — opt-in nas tools)."
if [ "$ATOMIC" = "1" ]; then
    warn "Sistema atomico: os pacotes ficam layered e exigem REBOOT no fim."
fi
hr
read -rp "Continuar? [y/N] " ANSWER < /dev/tty || ANSWER=""
case "$ANSWER" in y|Y|yes|YES) ;; *) echo "Cancelado."; exit 0 ;; esac

# ---- 1. update + deps -----------------------------------------------------
hr
if [ "$ATOMIC" = "1" ]; then
    info "Atualizando o sistema (rpm-ostree)..."
    sudo rpm-ostree upgrade || warn "upgrade pulado (sem mudancas ou offline)."
    info "Layerando dependencias (uma transacao)..."
    sudo rpm-ostree install --idempotent "${DEPS_CORE[@]}" "${DEPS_BACKENDS[@]}"
else
    info "Atualizando o sistema (dnf)..."
    sudo dnf -y upgrade || warn "upgrade pulado."
    info "Instalando dependencias..."
    sudo dnf install -y "${DEPS_CORE[@]}" "${DEPS_BACKENDS[@]}"
fi

# ---- 2. clona o repo (se necessario) --------------------------------------
hr
if [ "$CLONE_NEEDED" = "1" ]; then
    if [ -d "$REPO_DIR/.git" ]; then
        info "Repo ja' existe em $REPO_DIR — atualizando..."
        git -C "$REPO_DIR" pull --ff-only || warn "git pull pulado."
    else
        info "Clonando o repo em $REPO_DIR..."
        git clone "$REPO_URL" "$REPO_DIR"
    fi
fi

# ---- 3. instala as ferramentas Vigia (pip --user) + atalhos ---------------
hr
info "Instalando as ${#VIGIA_TOOLS[@]} ferramentas Vigia (pip --user)..."
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$APPS_DIR" "$ICONS_DIR"
for t in "${VIGIA_TOOLS[@]}"; do
    tdir="$REPO_DIR/tools/$t"
    [ -d "$tdir" ] || { warn "tools/$t nao encontrada — pulando."; continue; }
    (cd "$tdir" && python3 -m pip install --user -e . -q) \
        && echo "  ${GREEN}ok${NC} $t" || warn "falha no pip de $t"
    # Registra .desktop + icone (so' tools com GUI tem data/)
    if compgen -G "$tdir/data/*.desktop" >/dev/null 2>&1; then
        install -Dpm 0644 "$tdir"/data/*.desktop "$APPS_DIR"/ 2>/dev/null || true
    fi
    if compgen -G "$tdir/data/*.svg" >/dev/null 2>&1; then
        install -Dpm 0644 "$tdir"/data/*.svg "$ICONS_DIR"/ 2>/dev/null || true
    fi
done
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

# ---- 4. Flatpaks ----------------------------------------------------------
hr
if command -v flatpak >/dev/null 2>&1; then
    info "Instalando Flatpaks de privacidade (escopo user)..."
    flatpak remote-add --user --if-not-exists flathub \
        https://flathub.org/repo/flathub.flatpakrepo || true
    flatpak install --user --noninteractive --or-update flathub \
        "${FLATPAKS[@]}" || warn "alguns Flatpaks falharam (segue o jogo)."
else
    warn "flatpak nao encontrado — pulando apps Flatpak."
fi

# ---- fim ------------------------------------------------------------------
hr
info "Bootstrap concluido."
echo
echo "${DIM}Nenhum servico foi ligado. Ative o que quiser nas ferramentas:${NC}"
echo "${DIM}  • Tor / fail2ban → Privacy Controls    • DNS encriptado → DNS Manager${NC}"
echo
if [ "$ATOMIC" = "1" ]; then
    echo "${BOLD}Reinicie para ativar os pacotes layered:${NC}"
    echo "    ${BOLD}systemctl reboot${NC}"
    echo "${DIM}Apos o reboot, abra o ${BOLD}Vigia Hub${NC}${DIM} pelo menu do GNOME.${NC}"
else
    echo "${BOLD}Pronto — sem reboot.${NC} Abra o ${BOLD}Vigia Hub${NC} pelo menu do GNOME"
    echo "${DIM}(ou rode ${BOLD}vigia-hub${NC}${DIM} no terminal).${NC}"
fi
echo
