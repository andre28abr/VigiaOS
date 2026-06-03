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
DEPS_CORE=(git python3-pip python3-gobject gtk4 libadwaita rust cargo)

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

# PRODUTOS: os ÚNICOS que ganham ícone no menu do GNOME (numa pasta "Vigia").
# Tudo roda DENTRO deles — as ferramentas são embarcadas, não apps soltos.
VIGIA_PRODUCTS=(vigia-hub vigia-blue vigia-red)
# MÓDULOS: instalados via pip pra rodar EMBARCADOS no Hub — SEM ícone próprio.
# vigia-common primeiro (dep de todos os outros).
VIGIA_MODULES=(
    vigia-common
    dashboard activity-log-gui privacy-controls dns-manager
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
echo "  ${DIM}produtos:${NC} ${VIGIA_PRODUCTS[*]} (ícones no menu, pasta Vigia)"
echo "  ${DIM}módulos:${NC}  ${#VIGIA_MODULES[@]} ferramentas embarcadas (pip --user, sem ícone solto)"
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

# ---- 3. instala os produtos + módulos (pip --user) ------------------------
hr
info "Instalando o Vigia (pip --user)..."
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$APPS_DIR" "$ICONS_DIR"

# 3a. pip install de TUDO (módulos primeiro — common é dep — depois produtos).
#     NENHUM registra ícone aqui: as ferramentas rodam embarcadas no Hub.
for t in "${VIGIA_MODULES[@]}" "${VIGIA_PRODUCTS[@]}"; do
    tdir="$REPO_DIR/tools/$t"
    [ -d "$tdir" ] || { warn "tools/$t nao encontrada — pulando."; continue; }
    (cd "$tdir" && python3 -m pip install --user -e . -q) \
        && echo "  ${GREEN}ok${NC} $t" || warn "falha no pip de $t"
done

# 3b. ÍCONE no menu SÓ pros 3 produtos (Hub/Blue/Red). As ferramentas não
#     viram apps soltos — abrem dentro do Hub.
for p in "${VIGIA_PRODUCTS[@]}"; do
    pdir="$REPO_DIR/tools/$p"
    compgen -G "$pdir/data/*.desktop" >/dev/null 2>&1 \
        && install -Dpm 0644 "$pdir"/data/*.desktop "$APPS_DIR"/ 2>/dev/null || true
    compgen -G "$pdir/data/*.svg" >/dev/null 2>&1 \
        && install -Dpm 0644 "$pdir"/data/*.svg "$ICONS_DIR"/ 2>/dev/null || true
done

# 3b'. Alguns backends CLI trazem um .desktop próprio que polui o menu (ex:
#      chkrootkit abre num terminal e fecha). Esconde com um override
#      NoDisplay no nível do usuário — o binário continua (o Vigia usa ele).
for app in chkrootkit; do
    [ -f "/usr/share/applications/$app.desktop" ] || continue
    printf '[Desktop Entry]\nType=Application\nName=%s\nNoDisplay=true\n' "$app" \
        > "$APPS_DIR/$app.desktop"
done

# gtk-update-icon-cache exige um index.theme no dir do tema; em ~/.local ele
# costuma faltar e o cache nao reconstroi (icones novos ficam invisiveis no
# GNOME). Copia o do sistema se faltar e forca o rebuild.
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
[ -f "$HICOLOR_DIR/index.theme" ] || cp /usr/share/icons/hicolor/index.theme "$HICOLOR_DIR/" 2>/dev/null || true
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache -f "$HICOLOR_DIR" >/dev/null 2>&1 || true

# 3c. Agrupa os 3 produtos numa pasta "Vigia" no grid de apps do GNOME.
if command -v gsettings >/dev/null 2>&1; then
    AF="org.gnome.desktop.app-folders"
    kids=$(gsettings get "$AF" folder-children 2>/dev/null || echo "[]")
    if [[ "$kids" != *"'Vigia'"* ]]; then
        kids=$(python3 -c "import sys,ast; l=ast.literal_eval(sys.argv[1]) if sys.argv[1].startswith('[') else []; l.append('Vigia'); print(repr(l))" "$kids" 2>/dev/null)
        [ -n "$kids" ] && gsettings set "$AF" folder-children "$kids" 2>/dev/null || true
    fi
    VF="$AF.folder:/org/gnome/desktop/app-folders/folders/Vigia/"
    gsettings set "$VF" name 'Vigia' 2>/dev/null || true
    gsettings set "$VF" apps "['br.com.vigia.Hub.desktop', 'br.com.vigia.Blue.desktop', 'br.com.vigia.Red.desktop']" 2>/dev/null || true
fi

# ---- 3d. core do Activity Log (vigia-log, Rust) ---------------------------
# O Activity Log (GUI) é um frontend do parser Rust `vigia-log`. Sem esse
# binário, a ferramenta fica indisponível no Hub (ponto vermelho).
hr
if command -v vigia-log >/dev/null 2>&1; then
    echo "  ${GREEN}ok${NC} vigia-log (já instalado)"
elif command -v cargo >/dev/null 2>&1 && [ -d "$REPO_DIR/tools/activity-log" ]; then
    info "Compilando o core do Activity Log (vigia-log, Rust) — pode levar minutos..."
    if (cd "$REPO_DIR/tools/activity-log" && cargo build --release) \
       && sudo install -m 0755 \
            "$REPO_DIR/tools/activity-log/target/release/vigia-log" \
            /usr/local/bin/vigia-log; then
        echo "  ${GREEN}ok${NC} vigia-log → /usr/local/bin"
    else
        warn "falha ao compilar/instalar o vigia-log — Activity Log fica indisponível."
    fi
else
    warn "cargo (Rust) ausente — Activity Log (core vigia-log) fica indisponível."
fi

# ---- 4. Flatpaks ----------------------------------------------------------
hr
if command -v flatpak >/dev/null 2>&1; then
    info "Instalando Flatpaks de privacidade (escopo user)..."
    flatpak remote-add --user --if-not-exists flathub \
        https://flathub.org/repo/flathub.flatpakrepo || true
    # Instala UM a UM: um app sem build pra esta arquitetura (ex: Signal
    # Desktop nao tem ARM64) nao pode derrubar os outros do lote.
    for fp in "${FLATPAKS[@]}"; do
        if fp_err=$(flatpak install --user --noninteractive --or-update flathub "$fp" 2>&1); then
            echo "  ${GREEN}ok${NC} $fp"
        else
            # Mostra o motivo REAL (última linha do erro) em vez de adivinhar.
            warn "$fp pulado — $(printf '%s' "$fp_err" | tail -1 | cut -c1-90)"
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
echo "${BOLD}Pronto — sem reboot.${NC} No menu de aplicativos do GNOME, abra a pasta"
echo "${BOLD}Vigia${NC} — lá estão os 3 produtos: ${BOLD}Vigia Hub${NC}, ${BOLD}VigiaBlue${NC} e ${BOLD}VigiaRed${NC}."
echo "${DIM}(as ferramentas rodam embarcadas dentro deles; no terminal: vigia-hub)${NC}"
echo
