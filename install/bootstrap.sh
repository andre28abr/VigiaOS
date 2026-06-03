#!/usr/bin/env bash
#
# VigiaOS — bootstrap único (auto-detecta a plataforma)
#
# Instala a suíte VigiaOS completa numa instalação Fedora limpa:
#   - Instala via dnf (Fedora Workstation) as dependências de runtime (GTK4)
#     + os backends CLI que as ferramentas wrappam (lynis, aide, clamav, …).
#   - Clona o repo, instala as ferramentas (pip --user) e registra
#     atalhos + ícones no menu do GNOME.
#   - Instala Flatpaks de privacidade (KeePassXC, Signal, Tor Browser…).
#
# **NÃO liga nenhum serviço.** fail2ban e dnscrypt-proxy ficam
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

# pip --user em Fedora 38+ exige isto (PEP 668: Python externally-managed).
# Em pip sem PEP 668, --break-system-packages e' no-op inofensivo.
export PIP_BREAK_SYSTEM_PACKAGES=1

REPO_URL="https://github.com/andre28abr/VigiaOS"
CLONE_DIR="${VIGIA_DIR:-$HOME/dev/VigiaOS}"

# ---- visual ---------------------------------------------------------------
GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'
DIM=$'\e[2m'; BOLD=$'\e[1m'; ACCENT=$'\e[38;5;42m'; NC=$'\e[0m'
info()  { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
warn()  { echo "${YELLOW}!! ${NC} $*"; }
fail()  { echo "${RED}xx ${NC} $*" >&2; }
hr()    { echo "${DIM}--------------------------------------------------${NC}"; }

# ---- plataforma -----------------------------------------------------------
_V="$(sed -n 's/^VARIANT=//p' /etc/os-release 2>/dev/null | tr -d '"' | sed 's/ Edition//' | head -1)"
PLATFORM="Fedora ${_V:-Workstation}"; PM="dnf"

cat <<BANNER

${ACCENT}  VIGIA${NC}${BOLD}OS${NC}  ${DIM}|  suite de seguranca / privacidade / auditoria${NC}
  ${DIM}Plataforma detectada: ${PLATFORM} (${PM})${NC}
  ${DIM}${REPO_URL}${NC}

BANNER

# ---- pacotes --------------------------------------------------------------
# Runtime GUI (GTK4) + ferramentas pra instalar via pip. O dnf e' idempotente
# (re-rodar o bootstrap nao quebra).
DEPS_CORE=(git python3-pip python3-gobject gtk4 libadwaita)

# Backends CLI que as ferramentas Vigia wrappam. INSTALA, mas NAO LIGA
# servico nenhum (fail2ban/dnscrypt ficam off — opt-in nas tools).
DEPS_BACKENDS=(
    lynis aide chkrootkit rkhunter        # auditoria / rootkits
    clamav clamav-update                  # antivirus
    mtr nethogs                     # rede (diagnostico)
    lsof strace                           # debug
    fail2ban                              # defesa (servico — fica OFF)
    dnscrypt-proxy                        # DNS encriptado (fica OFF)
    md5deep                               # forense (binarios hashdeep/sha256deep)
)

# Ferramentas Vigia (dirs em tools/). vigia-common primeiro (dep das outras).
VIGIA_TOOLS=(
    vigia-common
    vigia-hub dashboard activity-log-gui privacy-controls dns-manager
    selinux-gui firewall-gui netmon-gui hardening-checks reports
    file-integrity tool-installer capabilities-inspector rootkit-scanner
    antivirus
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
warn "Nenhum servico sera LIGADO (fail2ban/dnscrypt off — opt-in nas tools)."
hr
read -rp "Continuar? [y/N] " ANSWER < /dev/tty || ANSWER=""
case "$ANSWER" in y|Y|yes|YES) ;; *) echo "Cancelado."; exit 0 ;; esac

# ---- 1. update + deps -----------------------------------------------------
hr
info "Atualizando o sistema (dnf)..."
sudo dnf -y upgrade || warn "upgrade pulado."
info "Instalando dependencias..."
sudo dnf install -y "${DEPS_CORE[@]}" "${DEPS_BACKENDS[@]}"

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
info "Instalando os ${#VIGIA_TOOLS[@]} pacotes Vigia (pip --user)..."
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
# gtk-update-icon-cache exige um index.theme no dir do tema; em ~/.local ele
# costuma faltar e o cache nao reconstroi (icones novos ficam invisiveis no
# GNOME). Copia o do sistema se faltar e forca o rebuild.
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
[ -f "$HICOLOR_DIR/index.theme" ] || cp /usr/share/icons/hicolor/index.theme "$HICOLOR_DIR/" 2>/dev/null || true
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache -f "$HICOLOR_DIR" >/dev/null 2>&1 || true

# ---- 4. Flatpaks ----------------------------------------------------------
hr
if command -v flatpak >/dev/null 2>&1; then
    info "Instalando Flatpaks de privacidade (escopo user)..."
    flatpak remote-add --user --if-not-exists flathub \
        https://flathub.org/repo/flathub.flatpakrepo || true
    # Instala UM a UM: um app sem build pra esta arquitetura (ex: Signal
    # Desktop nao tem ARM64) nao pode derrubar os outros do lote.
    for fp in "${FLATPAKS[@]}"; do
        if flatpak install --user --noninteractive --or-update flathub "$fp" >/dev/null 2>&1; then
            echo "  ${GREEN}ok${NC} $fp"
        else
            warn "$fp indisponivel (talvez sem build pra $(uname -m)) — pulado."
        fi
    done
else
    warn "flatpak nao encontrado — pulando apps Flatpak."
fi

# ---- fim ------------------------------------------------------------------
hr
info "Bootstrap concluido."
echo
echo "${DIM}Nenhum servico foi ligado. Ative o que quiser nas ferramentas:${NC}"
echo "${DIM}  • fail2ban → Privacy Controls    • DNS encriptado → DNS Manager${NC}"
echo
echo "${BOLD}Pronto — sem reboot.${NC} Abra o ${BOLD}Vigia Hub${NC} pelo menu do GNOME"
echo "${DIM}(ou rode ${BOLD}vigia-hub${NC}${DIM} no terminal).${NC}"
echo
