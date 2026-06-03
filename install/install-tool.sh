#!/usr/bin/env bash
#
# VigiaOS — instala UM módulo isolado (user-level, sem root)
#
# Instala uma única ferramenta da VigiaOS via `pip --user` e registra o
# atalho (.desktop) + ícone no GNOME do usuário. Não precisa do Vigia Hub
# nem de root — instala tudo dentro de ~/.local (sem dnf aqui).
#
# Uso:
#   install/install-tool.sh <modulo>     # ex: antivirus, dns-manager
#   install/install-tool.sh --list       # lista os módulos disponíveis
#
# Para instalação como pacote de sistema (quando o COPR estiver ativo):
#   sudo dnf install vigia-antivirus
#
set -euo pipefail

# pip --user em Fedora 38+ exige isto (PEP 668: Python externally-managed).
export PIP_BREAK_SYSTEM_PACKAGES=1

# ---- visual ---------------------------------------------------------------
GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'
DIM=$'\e[2m'; BOLD=$'\e[1m'; NC=$'\e[0m'
info() { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
warn() { echo "${YELLOW}!! ${NC} $*"; }
fail() { echo "${RED}xx ${NC} $*" >&2; }

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(dirname "$SCRIPT_DIR")
TOOLS_DIR="$REPO_ROOT/tools"

APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

# ---- helpers --------------------------------------------------------------
is_module() {
    # Tem pyproject e um .desktop em data/ => é um módulo GUI instalável.
    local d="$1"
    [ -f "$d/pyproject.toml" ] && compgen -G "$d/data/*.desktop" >/dev/null 2>&1
}

list_tools() {
    echo "${BOLD}Módulos disponíveis${NC} ${DIM}(install/install-tool.sh <modulo>)${NC}:"
    echo
    local d name desc
    for d in "$TOOLS_DIR"/*/; do
        name=$(basename "$d")
        is_module "$d" || continue
        desc=$(grep -m1 '^Comment=' "$d"data/*.desktop 2>/dev/null | head -1 | cut -d= -f2-)
        printf "  ${GREEN}%-22s${NC} ${DIM}%s${NC}\n" "$name" "${desc:-—}"
    done
    echo
    echo "${DIM}vigia-common é biblioteca interna (dep) — instalada automaticamente.${NC}"
}

usage() {
    echo "Uso: install/install-tool.sh <modulo>     # instala um módulo isolado"
    echo "     install/install-tool.sh --list       # lista os módulos"
    echo
    list_tools
}

# ---- args -----------------------------------------------------------------
if [ $# -ne 1 ]; then
    usage
    exit 1
fi
case "$1" in
    -h|--help)  usage; exit 0 ;;
    -l|--list)  list_tools; exit 0 ;;
esac

TOOL="$1"
TOOL_DIR="$TOOLS_DIR/$TOOL"

if [ ! -d "$TOOL_DIR" ]; then
    fail "Módulo '$TOOL' não encontrado em tools/."
    echo
    list_tools
    exit 1
fi
if ! is_module "$TOOL_DIR"; then
    fail "'$TOOL' não é um módulo GUI instalável (sem pyproject ou sem .desktop)."
    exit 1
fi

# ---- pré-requisito: pip ---------------------------------------------------
if ! python3 -m pip --version >/dev/null 2>&1; then
    fail "python3 -m pip não disponível. Instale python3-pip primeiro."
    exit 1
fi

# ---- instala vigia-common (dependência de todas as tools) -----------------
info "Instalando vigia-common (dependência compartilhada)..."
(cd "$TOOLS_DIR/vigia-common" && python3 -m pip install --user -e . -q)

# ---- instala o módulo -----------------------------------------------------
info "Instalando módulo '$TOOL'..."
(cd "$TOOL_DIR" && python3 -m pip install --user -e . -q)

# ---- registra .desktop + ícone no GNOME do usuário ------------------------
info "Registrando atalho + ícone no menu do GNOME..."
mkdir -p "$APPS_DIR" "$ICONS_DIR"
install -Dpm 0644 "$TOOL_DIR"/data/*.desktop "$APPS_DIR"/
if compgen -G "$TOOL_DIR/data/*.svg" >/dev/null 2>&1; then
    install -Dpm 0644 "$TOOL_DIR"/data/*.svg "$ICONS_DIR"/
fi

# Atualiza caches. gtk-update-icon-cache EXIGE um index.theme no diretório do
# tema; em ~/.local ele costuma faltar — e sem ele o cache não reconstrói, então
# ícones novos ficam invisíveis (o GNOME mostra um ícone genérico). Copia o do
# sistema se faltar e força o rebuild (-f).
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
[ -f "$HICOLOR_DIR/index.theme" ] || cp /usr/share/icons/hicolor/index.theme "$HICOLOR_DIR/" 2>/dev/null || true
update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
gtk-update-icon-cache -f "$HICOLOR_DIR" >/dev/null 2>&1 || true

# ---- fim ------------------------------------------------------------------
EXEC_CMD=$(grep -m1 '^Exec=' "$TOOL_DIR"/data/*.desktop | head -1 | cut -d= -f2-)
APP_NAME=$(grep -m1 '^Name=' "$TOOL_DIR"/data/*.desktop | head -1 | cut -d= -f2-)
echo
info "Pronto. '$TOOL' instalado isoladamente."
echo "  ${DIM}• No menu do GNOME:${NC} procure por ${BOLD}${APP_NAME:-$TOOL}${NC} (tecle Super e digite)"
echo "  ${DIM}• No terminal:${NC}      ${BOLD}${EXEC_CMD:-$TOOL}${NC}"
echo
echo "${DIM}Se o ícone não aparecer na hora, faça logout/login (cache do GNOME).${NC}"
echo "${DIM}Para remover: python3 -m pip uninstall <pacote> + apague o .desktop em${NC}"
echo "${DIM}$APPS_DIR.${NC}"
