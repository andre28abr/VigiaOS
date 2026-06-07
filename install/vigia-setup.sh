#!/usr/bin/env bash
#
# vigia-setup.sh — instalador GUIADO do ecossistema VigiaOS (Hub · Blue · Red).
#
# Conduz a instalação em 3 etapas, cada uma com confirmação, mostrando o que vai
# acontecer em tabelas:
#
#   [1/3] Mostra o sistema (Fedora Workstation) e oferece ATUALIZAR primeiro.
#   [2/3] Mostra os PACOTES principais (e para qual módulo cada um serve) e
#         oferece instalá-los (dnf + pipx + build do vigia-log).
#   [3/3] Instala as INTERFACES GRÁFICAS dos três produtos (Hub + ferramentas,
#         VigiaBlue, VigiaRed) via pip --user, registrando ícones no GNOME.
#
# É o irmão interativo do bootstrap.sh (que é não-interativo, pra `curl | bash`).
# Não liga nenhum serviço (minimum surface area). Não roda como root.
#
# Uso:
#   ./install/vigia-setup.sh            # guiado (pergunta em cada etapa)
#   ./install/vigia-setup.sh --yes      # responde "sim" a tudo
#   ./install/vigia-setup.sh --dry-run  # só mostra, não executa nada
#
set -uo pipefail

# pip --user em Fedora 38+ exige isto (PEP 668). Em pip antigo é no-op.
export PIP_BREAK_SYSTEM_PACKAGES=1

# ============================================================
# Visual (cores + caixas Unicode — sem dependência externa)
# ============================================================
if [[ -t 1 ]]; then
    BOLD=$'\e[1m'; DIM=$'\e[2m'; NC=$'\e[0m'
    GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'
    ACCENT=$'\e[38;5;42m'
else
    BOLD=""; DIM=""; NC=""; GREEN=""; RED=""; YELLOW=""; BLUE=""; ACCENT=""
fi
info() { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
ok()   { echo "  ${GREEN}✓${NC} $*"; }
warn() { echo "  ${YELLOW}!${NC} $*"; }
err()  { echo "  ${RED}✗${NC} $*" >&2; }

# repete uma string (multibyte-safe — tr não serve p/ '─')
rep() { local n=$1 s=$2 o=; while ((n-- > 0)); do o+="$s"; done; printf '%s' "$o"; }
# corta a string para no máx N caracteres (mantém as tabelas alinhadas)
fit() { local s="$1" w="$2"; printf '%s' "${s:0:w}"; }

banner() {
    local bar; bar=$(rep 64 ━)
    echo "${ACCENT}${bar}${NC}"
    echo "  ${BOLD}VigiaOS · Instalador do Ecossistema${NC}"
    echo "  ${DIM}Hub · VigiaBlue · VigiaRed${NC}"
    echo "${ACCENT}${bar}${NC}"
}

step() { echo; echo "${BOLD}${BLUE}[$1]${NC} ${BOLD}$2${NC}"; }

# Pergunta sim/não. confirm "texto" [y]  (default n; y torna o default sim)
confirm() {
    local q="$1" def="${2:-n}" hint="[s/N]" ans
    [[ "$def" == "y" ]] && hint="[S/n]"
    if [[ $ASSUME_YES -eq 1 ]]; then echo "${DIM}? ${q} ${hint} → sim${NC}"; return 0; fi
    read -rp "$(printf '%s %s ' "${BOLD}?${NC} $q" "$hint")" ans </dev/tty || ans=""
    ans="${ans:-$def}"
    [[ "$ans" =~ ^[sSyY] ]]
}

# Tabela de pacotes (3 colunas: 30 / 5 / 22)
PT="$(rep 32 ─)"; P5="$(rep 7 ─)"; P22="$(rep 24 ─)"
prow() { printf "│ %-30s │ %-5s │ %-22s │\n" "$(fit "$1" 30)" "$(fit "$2" 5)" "$(fit "$3" 22)"; }
ptop() { printf "┌%s┬%s┬%s┐\n" "$PT" "$P5" "$P22"; }
psep() { printf "├%s┼%s┼%s┤\n" "$PT" "$P5" "$P22"; }
pbot() { printf "└%s┴%s┴%s┘\n" "$PT" "$P5" "$P22"; }

# Tabela chave/valor (14 / 44)
KT="$(rep 16 ─)"; KV="$(rep 46 ─)"
krow() { printf "│ %-14s │ %-44s │\n" "$(fit "$1" 14)" "$(fit "$2" 44)"; }
ktop() { printf "┌%s┬%s┐\n" "$KT" "$KV"; }
kbot() { printf "└%s┴%s┘\n" "$KT" "$KV"; }

# ============================================================
# Argumentos + sanidade
# ============================================================
ASSUME_YES=0
DRY_RUN=0
for a in "$@"; do
    case "$a" in
        -y|--yes)     ASSUME_YES=1 ;;
        -n|--dry-run) DRY_RUN=1 ;;
        -h|--help)    sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) err "opção desconhecida: $a"; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$REPO_ROOT/tools"

if [[ "$(id -u)" -eq 0 ]]; then
    err "Não rode como root. As GUIs vão para o seu usuário (pip --user)."
    exit 1
fi
[[ -d "$TOOLS_DIR" ]] || { err "tools/ não encontrado. Rode de dentro do repo."; exit 1; }

run() {   # executa, respeitando --dry-run
    if [[ $DRY_RUN -eq 1 ]]; then echo "  ${DIM}\$ $*${NC}"; return 0; fi
    "$@"
}

is_module() {  # pyproject + .desktop em data/ => GUI instalável (igual install-tool.sh)
    local d="$1"
    [ -f "$d/pyproject.toml" ] && compgen -G "$d/data/*.desktop" >/dev/null 2>&1
}

declare -a DONE_PKGS=() SKIP_PKGS=() FAIL_PKGS=() DONE_GUI=() FAIL_GUI=()

# ============================================================
banner
[[ $DRY_RUN -eq 1 ]] && warn "modo --dry-run: nada será instalado, só exibido."

# ============================================================
# [1/3] Sistema
# ============================================================
# variante REAL (Workstation/Server/…) do /etc/os-release
_V="$(sed -n 's/^VARIANT=//p' /etc/os-release 2>/dev/null | tr -d '"' | sed 's/ Edition//' | head -1)"
PLAT="Fedora ${_V:-Workstation}"; PKGMGR="dnf"

step "1/3" "Sistema detectado"
ktop
krow "Plataforma"  "$PLAT"
krow "Gerenciador" "$PKGMGR"
krow "Repositorio" "$REPO_ROOT"
kbot
echo
echo "  ${DIM}Atualizar o sistema antes evita conflito de pacotes.${NC}"

if confirm "Atualizar o sistema agora?"; then
    info "sudo dnf upgrade -y"
    run sudo dnf upgrade -y && ok "Sistema atualizado." || warn "falha ao atualizar."
else
    warn "pulando atualização do sistema."
fi

# ============================================================
# [2/3] Pacotes do sistema (dependências dos módulos)
# ============================================================
step "2/3" "Pacotes principais dos módulos"

# Hub = curado à mão (os wrapped_packages do Hub têm muito "comando" que não é
# pacote instalável, e o Hub é estável). Blue/Red = lidos da REGISTRY
# (Module.requires, via _deps.py) — fonte única de verdade: módulo novo com
# `requires` declarado aparece aqui sozinho, sem editar este script.
HUB_RPM=(clamav clamav-update chkrootkit rkhunter lynis aide firewalld
         policycoreutils-python-utils)
DEPS_TSV="$(python3 "$SCRIPT_DIR/_deps.py" 2>/dev/null || true)"
declare -a DYN_RPM=() DYN_PIP=() SRC_LABELS=()

ptop
prow "Pacote"                        "Prod" "Para qual modulo"
psep
prow "GTK4 + libadwaita + PyGObject" "Base" "Interface (todos)"
prow "clamav, clamav-update"         "Hub"  "Antivirus"
prow "chkrootkit, rkhunter"          "Hub"  "Rootkit Scanner"
prow "lynis"                         "Hub"  "Hardening Checks"
prow "aide"                          "Hub"  "File Integrity"
prow "firewalld"                     "Hub"  "Firewall Manager"
prow "policycoreutils-python-utils"  "Hub"  "SELinux Manager"
# linhas de Blue/Red montadas a partir da registry (uma por dependência)
if [[ -n "$DEPS_TSV" ]]; then
    while IFS=$'\x1f' read -r prod modname label kind package checks; do
        [[ -z "${prod:-}" ]] && continue
        case "$kind" in
            rpm)    disp="$package";                DYN_RPM+=("$package") ;;
            pip)    disp="$package (pipx)";          DYN_PIP+=("$package") ;;
            source) disp="${checks%%,*} (compilar)"; SRC_LABELS+=("$label") ;;
            *)      disp="${package:-$label}" ;;
        esac
        prow "$disp" "$prod" "$modname"
    done <<< "$DEPS_TSV"
fi
pbot
if ! grep -q $'^Red\x1f' <<< "$DEPS_TSV"; then
    echo "  ${DIM}VigiaRed está em construção — sem pacotes externos ainda;"
    echo "  aparecem aqui sozinhos quando os módulos forem declarados.${NC}"
fi

# Listas finais: Hub (curado) + Blue/Red (da registry); base GTK só se faltar.
RPM_PKGS=("${HUB_RPM[@]}" "${DYN_RPM[@]}")
if ! python3 -c "import gi; gi.require_version('Gtk','4.0')" >/dev/null 2>&1; then
    RPM_PKGS=(python3-gobject gtk4 libadwaita "${RPM_PKGS[@]}")
fi
PIPX_PKGS=("${DYN_PIP[@]}")

echo
if confirm "Instalar esses pacotes do sistema?"; then
    info "Pacotes do sistema (${PKGMGR}): ${RPM_PKGS[*]}"
    if run sudo dnf install -y "${RPM_PKGS[@]}"; then
        DONE_PKGS+=("${RPM_PKGS[@]}"); ok "Instalados."
    else err "dnf falhou."; FAIL_PKGS+=("${RPM_PKGS[*]}"); fi

    # forense via pipx (sem root) — pacotes kind=pip lidos da registry
    if [[ ${#PIPX_PKGS[@]} -gt 0 ]]; then
        if command -v pipx >/dev/null 2>&1 || [[ $DRY_RUN -eq 1 ]]; then
            for p in "${PIPX_PKGS[@]}"; do
                info "pipx install $p"
                if run pipx install "$p"; then DONE_PKGS+=("$p (pipx)"); ok "$p ok."
                else err "falha em $p."; FAIL_PKGS+=("$p"); fi
            done
        else
            warn "pipx ausente — instalando via dnf e seguindo."
            run sudo dnf install -y pipx \
                && for p in "${PIPX_PKGS[@]}"; do run pipx install "$p"; done || true
            SKIP_PKGS+=("${PIPX_PKGS[*]}")
        fi
    fi

    # core do SIEM (Rust): só se a registry declarar uma dep kind=source (vigia-log)
    if [[ ${#SRC_LABELS[@]} -gt 0 ]]; then
        if command -v vigia-log >/dev/null 2>&1; then
            ok "vigia-log já instalado."
        elif command -v cargo >/dev/null 2>&1 && [[ -d "$REPO_ROOT/tools/activity-log" ]]; then
            info "Compilando vigia-log (cargo)…"
            if run bash -c "cd '$REPO_ROOT/tools/activity-log' && cargo build --release && sudo install -m 0755 target/release/vigia-log /usr/local/bin/"; then
                DONE_PKGS+=("vigia-log"); ok "vigia-log instalado em /usr/local/bin."
            else err "falha ao compilar o vigia-log."; FAIL_PKGS+=("vigia-log"); fi
        else
            warn "cargo (Rust) ausente — vigia-log (SIEM) fica de fora."
            SKIP_PKGS+=("vigia-log (sem cargo)")
        fi
    fi
else
    warn "pulando pacotes do sistema."
fi

# ============================================================
# [3/3] Interfaces gráficas (Hub + ferramentas, VigiaBlue, VigiaRed)
# ============================================================
step "3/3" "Interfaces gráficas dos produtos"

# Descobre os módulos GUI instaláveis e separa por produto.
declare -a HUB_MODS=() BLUE_MODS=() RED_MODS=()
for d in "$TOOLS_DIR"/*/; do
    is_module "$d" || continue
    name="$(basename "$d")"
    case "$name" in
        vigia-blue) BLUE_MODS+=("$name") ;;
        vigia-red)  RED_MODS+=("$name") ;;
        *)          HUB_MODS+=("$name") ;;
    esac
done

ptop
prow "Produto"   "Pkgs" "O que instala"
psep
prow "Hub (launcher + tools)" "${#HUB_MODS[@]}"  "14 tools embarcadas + launcher"
prow "VigiaBlue"              "${#BLUE_MODS[@]}" "7 modulos prontos"
prow "VigiaRed"              "${#RED_MODS[@]}"  "esqueleto (em breve)"
pbot
echo "  ${DIM}pip --user (editável). Tudo roda embarcado no VigiaOS — só ele${NC}"
echo "  ${DIM}vira ícone no menu (Hub/Red/Blue são seções dentro dele).${NC}"

echo
if confirm "Instalar a interface gráfica (VigiaOS unificado)?" y; then
    # Tudo via pip SEM ícone próprio — o VigiaOS é o único atalho do menu.
    for name in "${HUB_MODS[@]}" "${BLUE_MODS[@]}" "${RED_MODS[@]}"; do
        printf "  %-24s " "$name"
        if [[ $DRY_RUN -eq 1 ]]; then echo "${DIM}(dry-run)${NC}"; continue; fi
        if "$SCRIPT_DIR/install-tool.sh" --no-icon "$name" >"/tmp/vigia-setup-$name.log" 2>&1; then
            echo "${GREEN}✓${NC}"; DONE_GUI+=("$name")
        else
            echo "${RED}✗${NC} ${DIM}(log: /tmp/vigia-setup-$name.log)${NC}"; FAIL_GUI+=("$name")
        fi
    done
    # Registra o ÚNICO ícone (VigiaOS) e limpa ícones/pasta de instalações antigas.
    if [[ $DRY_RUN -eq 0 ]]; then
        APPS_DIR="$HOME/.local/share/applications"
        ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
        mkdir -p "$APPS_DIR" "$ICONS_DIR"
        OS_DATA="$REPO_ROOT/tools/vigia-hub/data"
        install -Dpm 0644 "$OS_DATA/br.com.vigia.OS.desktop" "$APPS_DIR/" 2>/dev/null || true
        install -Dpm 0644 "$OS_DATA/br.com.vigia.OS.svg" "$ICONS_DIR/" 2>/dev/null || true
        rm -f "$APPS_DIR"/br.com.vigia.Hub.desktop \
              "$APPS_DIR"/br.com.vigia.Blue.desktop \
              "$APPS_DIR"/br.com.vigia.Red.desktop 2>/dev/null || true
        update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
        if command -v gsettings >/dev/null 2>&1; then
            AF="org.gnome.desktop.app-folders"
            gsettings reset-recursively \
                "$AF.folder:/org/gnome/desktop/app-folders/folders/Vigia/" 2>/dev/null || true
            kids=$(gsettings get "$AF" folder-children 2>/dev/null || echo "[]")
            if [[ "$kids" == *"'Vigia'"* ]]; then
                kids=$(python3 -c "import sys,ast; print(repr([x for x in ast.literal_eval(sys.argv[1]) if x!='Vigia']))" "$kids" 2>/dev/null)
                [ -n "$kids" ] && gsettings set "$AF" folder-children "$kids" 2>/dev/null || true
            fi
        fi
    fi
else
    warn "pulando instalação da interface."
fi

# ============================================================
# Resumo
# ============================================================
echo
info "Resumo"
[[ ${#DONE_PKGS[@]} -gt 0 ]] && ok "Pacotes: ${DONE_PKGS[*]}"
[[ ${#DONE_GUI[@]}  -gt 0 ]] && ok "Interfaces: ${#DONE_GUI[@]} instaladas"
for s in "${SKIP_PKGS[@]:-}"; do [[ -n "$s" ]] && warn "pulado: $s"; done
for f in "${FAIL_PKGS[@]:-}"; do [[ -n "$f" ]] && err "falhou: $f"; done
for f in "${FAIL_GUI[@]:-}";  do [[ -n "$f" ]] && err "GUI falhou: $f"; done

echo
echo "${GREEN}${BOLD}Pronto!${NC} Abra o ${BOLD}VigiaOS${NC} no menu — Início, Hub, Red e Blue são seções."
echo "${DIM}A seção ${BOLD}Configurações${NC}${DIM} > Atualizações mostra o status das dependências.${NC}"
