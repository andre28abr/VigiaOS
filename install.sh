#!/usr/bin/env bash
#
# VigiaOS — bootstrap installer
#
# Uso (em uma instalacao Fedora Silverblue aarch64 limpa):
#     curl -fsSL https://raw.githubusercontent.com/andre28abr/VigiaOS/main/install.sh | bash
#
# O que faz:
#   1. Valida ambiente (precisa ser Silverblue / Atomic em aarch64)
#   2. Rebaseia o sistema para ghcr.io/andre28abr/vigiaos:latest
#   3. Pede para reiniciar (atualizacoes futuras: rpm-ostree upgrade)
#
# A deployment anterior (Silverblue limpo) fica disponivel no menu do GRUB
# como rollback caso algo de errado.

set -euo pipefail

IMAGE="ghcr.io/andre28abr/vigiaos:latest"
REPO_URL="https://github.com/andre28abr/VigiaOS"

# ---- visual ---------------------------------------------------------------
GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'
DIM=$'\e[2m'; BOLD=$'\e[1m'; ACCENT=$'\e[38;5;42m'; NC=$'\e[0m'

info()  { echo "${GREEN}==>${NC} ${BOLD}$*${NC}"; }
warn()  { echo "${YELLOW}!! ${NC} $*"; }
fail()  { echo "${RED}xx ${NC} $*" >&2; }
hr()    { echo "${DIM}--------------------------------------------------${NC}"; }

cat <<BANNER

${ACCENT}  VIGIA${NC}${BOLD}.OS${NC}  ${DIM}|  seguranca / LGPD / auditoria${NC}
  ${DIM}Fedora Atomic personalizada · aarch64 · GNOME${NC}
  ${DIM}${REPO_URL}${NC}

BANNER

# ---- validacoes -----------------------------------------------------------
info "Validando ambiente..."

ARCH="$(uname -m)"
if [ "$ARCH" != "aarch64" ]; then
    fail "VigiaOS so suporta aarch64. Detectado: ${ARCH}"
    fail "Use Apple Silicon (UTM/Parallels) ou hardware ARM nativo."
    exit 1
fi

if ! command -v rpm-ostree >/dev/null 2>&1; then
    fail "rpm-ostree nao encontrado. Voce precisa de Fedora Silverblue,"
    fail "Kinoite ou outro Atomic desktop. Baixe em:"
    fail "  https://fedoraproject.org/atomic-desktops/silverblue/"
    exit 1
fi

# Detecta se ja esta no VigiaOS
if rpm-ostree status 2>/dev/null | grep -q "andre28abr/vigiaos"; then
    warn "Voce ja esta no VigiaOS."
    warn "Para atualizar: ${BOLD}rpm-ostree upgrade && systemctl reboot${NC}"
    exit 0
fi

# ---- confirmacao ----------------------------------------------------------
hr
echo "${BOLD}Origem:${NC}   $(rpm-ostree status --booted --json 2>/dev/null \
        | python3 -c 'import json,sys; d=json.load(sys.stdin)["deployments"][0]; print(d.get("origin","?"))' 2>/dev/null \
        || echo '?')"
echo "${BOLD}Destino:${NC}  ${IMAGE}"
echo
echo "${DIM}A deployment atual ficara como rollback no GRUB.${NC}"
echo
read -rp "Continuar com o rebase? [y/N] " ANSWER < /dev/tty || ANSWER=""
case "$ANSWER" in
    y|Y|yes|YES) ;;
    *) echo "Cancelado."; exit 0 ;;
esac

# ---- rebase ---------------------------------------------------------------
hr
info "Rebaseando para VigiaOS (download + staging, ~3-5 min)..."
rpm-ostree rebase "ostree-unverified-registry:${IMAGE}"

# ---- proximo passo --------------------------------------------------------
hr
info "Pronto! Reinicie para entrar no VigiaOS:"
echo
echo "    ${BOLD}systemctl reboot -i${NC}"
echo
echo "${DIM}Apos o reboot, novas versoes chegam automaticamente.${NC}"
echo "${DIM}Forcar update manual: ${BOLD}rpm-ostree upgrade${NC}"
echo
