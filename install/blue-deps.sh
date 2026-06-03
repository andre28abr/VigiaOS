#!/usr/bin/env bash
#
# blue-deps.sh — instala as dependências externas dos módulos do VigiaBlue.
#
# Os módulos do VigiaBlue embarcam ferramentas open source que NÃO fazem parte
# do pacote Python (vigia-blue). Este script instala todas de uma vez no
# Fedora Workstation (dnf):
#
#   yara        → dnf                                       — módulo Vigia YARA
#   suricata    → dnf                                       — módulo Vigia IDS
#   tcpdump     → dnf                                       — captura do Vigia IDS
#   volatility3 → pipx (forense, sem root)                  — módulo Vigia Memory
#   avml        → download oficial (Microsoft) → ~/.local/bin — captura do Memory
#   dwarf2json  → go install → ~/.local/bin                  — símbolos do Memory
#   plaso       → pipx (forense, sem root)                  — módulo Vigia Timeline
#   vigia-log   → cargo build + install /usr/local/bin      — módulo Vigia SIEM
#
# Os módulos Vigia Intel e Vigia Playbooks NÃO precisam de nada externo.
#
# Uso:
#   ./install/blue-deps.sh                 # instala tudo
#   ./install/blue-deps.sh --no-forensics  # pula volatility3 + plaso
#   ./install/blue-deps.sh --no-core       # pula a build do vigia-log
#
# Segurança: nomes de pacote são fixos (sem entrada do usuário nos comandos).

set -uo pipefail

# ---- cores -----------------------------------------------------------------
if [[ -t 1 ]]; then
    BOLD=$'\e[1m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; RED=$'\e[31m'
    DIM=$'\e[2m'; NC=$'\e[0m'
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; DIM=""; NC=""
fi
info() { echo "${BOLD}==>${NC} $*"; }
ok()   { echo "${GREEN}  ✓${NC} $*"; }
warn() { echo "${YELLOW}  !${NC} $*"; }
err()  { echo "${RED}  ✗${NC} $*"; }

# ---- opções ----------------------------------------------------------------
DO_FORENSICS=1
DO_CORE=1
for arg in "$@"; do
    case "$arg" in
        --no-forensics) DO_FORENSICS=0 ;;
        --no-core)      DO_CORE=0 ;;
        -h|--help)
            sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) err "opção desconhecida: $arg"; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

declare -a DONE=() SKIPPED=() FAILED=()

# ---- plataforma ------------------------------------------------------------
info "Fedora Workstation — usando dnf."

# ===========================================================================
# 1) Pacotes do sistema: yara, suricata (+ pipx p/ a forense)
# ===========================================================================
RPM_PKGS=(yara suricata tcpdump)
# Forense via pipx: + build tools (o plaso compila libs C — libyal, yara-python)
# e golang/dnf-plugins-core pros símbolos (dwarf2json + debuginfo do kernel).
[[ $DO_FORENSICS -eq 1 ]] && RPM_PKGS+=(pipx python3-devel gcc make yara-devel \
                                       golang dnf-plugins-core)

info "Instalando pacotes do sistema: ${RPM_PKGS[*]}"
if sudo dnf install -y "${RPM_PKGS[@]}"; then
    ok "Instalados."
    DONE+=("${RPM_PKGS[*]}")
else
    err "dnf falhou."
    FAILED+=("${RPM_PKGS[*]}")
fi

# ===========================================================================
# 2) Forense (pipx): volatility3, plaso
# ===========================================================================
if [[ $DO_FORENSICS -eq 1 ]]; then
    if command -v pipx >/dev/null 2>&1; then
        info "pipx install volatility3"
        if pipx install volatility3; then
            ok "volatility3 instalado."
            DONE+=("volatility3 (pipx)")
        else
            err "falha ao instalar volatility3 via pipx."
            FAILED+=("volatility3")
        fi
        # plaso: o Fedora empacota plaso e as libs libyal — tenta o RPM
        # primeiro (sem compilar); se faltar, cai pro pipx (que compila as
        # libs C usando os build tools do sistema mutável).
        info "Instalando plaso (dnf, sem compilar)…"
        if sudo dnf install -y plaso 2>/dev/null; then
            ok "plaso instalado (dnf)."
            DONE+=("plaso (dnf)")
        elif pipx install plaso; then
            ok "plaso instalado (pipx)."
            DONE+=("plaso (pipx)")
        else
            warn "plaso não instalou. Instale os build tools e tente de novo:"
            warn "  sudo dnf install -y gcc python3-devel && pipx install plaso"
            SKIPPED+=("plaso (instale gcc/python3-devel e repita)")
        fi
    else
        warn "pipx ainda não está disponível."
        warn "Instale o pipx e rode de novo: sudo dnf install -y pipx"
        SKIPPED+=("volatility3 + plaso (sem pipx)")
    fi
else
    SKIPPED+=("forense (--no-forensics)")
fi

# ===========================================================================
# 3) Core do SIEM: vigia-log (Rust)
# ===========================================================================
if [[ $DO_CORE -eq 1 ]]; then
    if command -v vigia-log >/dev/null 2>&1; then
        ok "vigia-log já instalado."
        DONE+=("vigia-log (já presente)")
    elif command -v cargo >/dev/null 2>&1 && [[ -d "$REPO_ROOT/tools/activity-log" ]]; then
        info "Compilando vigia-log (cargo build --release)…"
        if (cd "$REPO_ROOT/tools/activity-log" && cargo build --release) \
           && sudo install -m 0755 \
                "$REPO_ROOT/tools/activity-log/target/release/vigia-log" \
                /usr/local/bin/; then
            ok "vigia-log compilado e instalado em /usr/local/bin."
            DONE+=("vigia-log (compilado)")
        else
            err "falha ao compilar/instalar o vigia-log."
            FAILED+=("vigia-log")
        fi
    else
        warn "cargo (Rust) não encontrado — necessário para o vigia-log."
        warn "Instale o Rust e rode de novo: sudo dnf install -y cargo"
        SKIPPED+=("vigia-log (sem cargo)")
    fi
else
    SKIPPED+=("vigia-log (--no-core)")
fi

# ===========================================================================
# 4) Captura de memória: AVML (binário estático oficial da Microsoft)
# ===========================================================================
if [[ $DO_FORENSICS -eq 1 ]]; then
    AVML_DEST="$HOME/.local/bin/avml"
    if command -v avml >/dev/null 2>&1 || [[ -x "$AVML_DEST" ]]; then
        ok "AVML já presente."
        DONE+=("avml (já presente)")
    else
        info "Baixando o AVML (release oficial da Microsoft) → ~/.local/bin/avml…"
        mkdir -p "$HOME/.local/bin"
        # AVML publica um binário POR ARQUITETURA — escolhe pelo uname -m
        # (x86_64 = 'avml', ARM64 = 'avml-aarch64'). Sem isso, o binário x86
        # não rodaria no Fedora ARM.
        case "$(uname -m)" in
            x86_64)        AVML_ASSET="avml" ;;
            aarch64|arm64) AVML_ASSET="avml-aarch64" ;;
            *)             AVML_ASSET="" ;;
        esac
        if [[ -z "$AVML_ASSET" ]]; then
            warn "Sem binário AVML oficial para $(uname -m) — captura de RAM indisponível."
            warn "Você ainda pode ANALISAR dumps existentes no Vigia Memory."
            SKIPPED+=("avml (arquitetura $(uname -m) sem binário oficial)")
        else
            AVML_URL="https://github.com/microsoft/avml/releases/latest/download/${AVML_ASSET}"
            if command -v curl >/dev/null 2>&1; then
                DL=(curl -fsSL -o "$AVML_DEST" "$AVML_URL")
            else
                DL=(wget -qO "$AVML_DEST" "$AVML_URL")
            fi
            if "${DL[@]}" && chmod 0755 "$AVML_DEST"; then
                ok "AVML instalado em ~/.local/bin/avml (${AVML_ASSET})."
                DONE+=("avml (${AVML_ASSET})")
                case ":$PATH:" in
                    *":$HOME/.local/bin:"*) : ;;
                    *) warn "~/.local/bin não está no PATH — adicione p/ o 'avml' ser achado." ;;
                esac
            else
                err "falha ao baixar o AVML."
                warn "Baixe manualmente: $AVML_URL → ~/.local/bin/avml (chmod +x)"
                FAILED+=("avml")
                rm -f "$AVML_DEST" 2>/dev/null || true
            fi
        fi
    fi
else
    SKIPPED+=("avml (--no-forensics)")
fi

# ===========================================================================
# 5) Símbolos do kernel: dwarf2json (gera o ISF p/ análise de dump Linux)
# ===========================================================================
if [[ $DO_FORENSICS -eq 1 ]]; then
    if command -v dwarf2json >/dev/null 2>&1 || [[ -x "$HOME/.local/bin/dwarf2json" ]]; then
        ok "dwarf2json já presente."
        DONE+=("dwarf2json (já presente)")
    elif command -v go >/dev/null 2>&1; then
        info "Instalando dwarf2json (go install) → ~/.local/bin…"
        mkdir -p "$HOME/.local/bin"
        if GOBIN="$HOME/.local/bin" go install github.com/volatilityfoundation/dwarf2json@latest; then
            ok "dwarf2json instalado em ~/.local/bin."
            DONE+=("dwarf2json (go install)")
        else
            err "falha ao instalar dwarf2json via go."
            FAILED+=("dwarf2json")
        fi
    else
        warn "Go não encontrado — preciso dele p/ o dwarf2json (gera os símbolos)."
        warn "Instale com: sudo dnf install -y golang  e rode de novo. Sem isso,"
        warn "a análise de dump Linux (experimental) não roda."
        SKIPPED+=("dwarf2json (sem go)")
    fi
else
    SKIPPED+=("dwarf2json (--no-forensics)")
fi

# ===========================================================================
# Resumo
# ===========================================================================
echo
info "${BOLD}Resumo${NC}"
for d in "${DONE[@]:-}";    do [[ -n "$d" ]] && ok "$d"; done
for s in "${SKIPPED[@]:-}"; do [[ -n "$s" ]] && warn "pulado: $s"; done
for f in "${FAILED[@]:-}";  do [[ -n "$f" ]] && err "falhou: $f"; done

echo
echo "${GREEN}Pronto.${NC} Abra o VigiaBlue → aba ${BOLD}Instalador${NC} para conferir o status."
