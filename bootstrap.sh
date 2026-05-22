#!/usr/bin/env bash
#
# VigiaOS — bootstrap em Fedora Silverblue vanilla
#
# Uso (em uma instalacao Fedora Silverblue limpa):
#     curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/bootstrap.sh | bash
#
# Layereia ferramentas de seguranca/auditoria/privacidade via rpm-ostree
# e instala Flatpaks essenciais. Reboot necessario ao final.
#
# Status: v2 (ferramentas-sobre-vanilla). Sem custom OS image.

set -euo pipefail

REPO_URL="https://github.com/andre28abr/VigiaOS"

# ---- visual ---------------------------------------------------------------
GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'
DIM=$'\e[2m'; BOLD=$'\e[1m'; ACCENT=$'\e[38;5;42m'; NC=$'\e[0m'

info()  { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
warn()  { echo "${YELLOW}!! ${NC} $*"; }
fail()  { echo "${RED}xx ${NC} $*" >&2; }
hr()    { echo "${DIM}--------------------------------------------------${NC}"; }

cat <<BANNER

${ACCENT}  VIGIA${NC}${BOLD}OS${NC}  ${DIM}|  suite de seguranca / privacidade / auditoria${NC}
  ${DIM}Ferramentas sobre Fedora Silverblue vanilla${NC}
  ${DIM}${REPO_URL}${NC}

BANNER

# ---- validacoes -----------------------------------------------------------
info "Validando ambiente..."

if ! command -v rpm-ostree >/dev/null 2>&1; then
    fail "rpm-ostree nao encontrado. VigiaOS Suite requer Fedora Silverblue,"
    fail "Kinoite, Bluefin, Bazzite ou outro Atomic desktop."
    fail "Baixe em: https://fedoraproject.org/atomic-desktops/silverblue/"
    exit 1
fi

# Detecta se esta na imagem antiga VigiaOS v1 (era um custom image)
if rpm-ostree status 2>/dev/null | grep -q "andre28abr/vigiaos"; then
    warn "Voce esta na imagem VigiaOS v1 (custom distro)."
    warn "v2 e' toolkit sobre Silverblue vanilla. Recomendado rebasar de volta:"
    warn ""
    warn "  ${BOLD}rpm-ostree rebase ostree-unverified-registry:quay.io/fedora-ostree-desktops/silverblue:44${NC}"
    warn "  ${BOLD}systemctl reboot${NC}"
    warn ""
    warn "Depois rode este bootstrap novamente."
    exit 0
fi

# ---- pacotes RPM (layered via rpm-ostree install) -------------------------
# Curadoria minima e justificada. Categorias separadas para facilitar revisao.
RPMS_NETWORK=(
    nmap                    # scanner de rede
    nmap-ncat               # netcat moderno
    tcpdump                 # captura de pacotes
    traceroute
    mtr                     # traceroute + ping continuo
    bind-utils              # dig, nslookup, host
    whois
    iperf3                  # benchmark de rede
    wireshark-cli           # tshark (GUI vem via Flatpak)
    iftop                   # monitor de banda por host
    nethogs                 # banda por processo
)

RPMS_AUDIT=(
    lynis                   # auditoria de sistema
    aide                    # file integrity monitoring
    chkrootkit
    rkhunter
    clamav                  # antivirus
    clamav-update
)

RPMS_FORENSICS=(
    yara                    # pattern matching para malware
    binwalk                 # analise de firmware/binarios
)

RPMS_CRYPTO=(
    age                     # criptografia simples e moderna
)

RPMS_DEV=(
    gcc
    make
    cmake
    podman-compose
    python3-pip
    python3-devel
    golang
    rust
    cargo
)

RPMS_ALL=(
    "${RPMS_NETWORK[@]}"
    "${RPMS_AUDIT[@]}"
    "${RPMS_FORENSICS[@]}"
    "${RPMS_CRYPTO[@]}"
    "${RPMS_DEV[@]}"
)

# ---- Flatpaks -------------------------------------------------------------
FLATPAKS=(
    com.github.tchx84.Flatseal              # gerenciador de permissoes Flatpak
    org.keepassxc.KeePassXC                 # gerenciador de senhas local
    org.signal.Signal                       # mensageria E2EE
    org.wireshark.Wireshark                 # GUI do Wireshark
    com.github.micahflee.torbrowser-launcher # Tor Browser
    org.mozilla.Thunderbird                 # email
)

# ---- preview --------------------------------------------------------------
hr
info "RPMs a layerar via rpm-ostree (precisam reboot):"
printf "  %s\n" "${RPMS_ALL[@]}"
echo
info "Flatpaks a instalar (escopo sistema, sem reboot):"
printf "  %s\n" "${FLATPAKS[@]}"
hr

read -rp "Continuar com a instalacao? [y/N] " ANSWER < /dev/tty || ANSWER=""
case "$ANSWER" in
    y|Y|yes|YES) ;;
    *) echo "Cancelado."; exit 0 ;;
esac

# ---- instalacao -----------------------------------------------------------
hr
info "Layerando RPMs (uma transacao, va tomar um cafe)..."
rpm-ostree install --idempotent "${RPMS_ALL[@]}"

hr
info "Garantindo remote Flathub (system scope)..."
flatpak remote-add --system --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo

info "Instalando Flatpaks..."
flatpak install --system --noninteractive --or-update flathub "${FLATPAKS[@]}"

# ---- fim ------------------------------------------------------------------
hr
info "Bootstrap concluido."
echo
echo "${BOLD}Reinicie para ativar os RPMs layered:${NC}"
echo
echo "    ${BOLD}systemctl reboot${NC}"
echo
echo "${DIM}Apos o reboot, todas as ferramentas estarao disponiveis no PATH.${NC}"
echo "${DIM}Para customizar (adicionar/remover): edite o bootstrap.sh local${NC}"
echo "${DIM}ou use 'rpm-ostree install/uninstall' direto.${NC}"
echo
