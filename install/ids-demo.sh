#!/usr/bin/env bash
#
# ids-demo.sh — gera um arquivo .pcap de TESTE para o Vigia IDS, de forma segura.
#
# Faz o Suricata "apitar" SEM nenhum malware real: acessa o testmynids.org — um
# serviço-teste que devolve uma string inofensiva ("uid=0(root) gid=0(root)...")
# que dispara a regra clássica "GPL ATTACK_RESPONSE id check returned root". É o
# equivalente ao EICAR (o arquivo-teste de antivírus), só que para IDS.
#
# Ele captura esse tráfego num .pcap. Você abre o .pcap no Vigia IDS
# (aba IDS → "Selecionar .pcap") e vê o alerta aparecer.
#
# Precisa de: suricata + tcpdump + curl, e de sudo (capturar rede exige root).
# A única coisa que ele baixa são as REGRAS do Suricata (suricata-update), e só
# se elas ainda não existirem.
#
# Uso:
#   ./install/ids-demo.sh                      # gera ~/teste/ids/vigia-ids-demo.pcap
#   ./install/ids-demo.sh /caminho/saida.pcap  # escolhe onde salvar
#
set -uo pipefail

if [[ -t 1 ]]; then
    BOLD=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; D=$'\e[2m'; N=$'\e[0m'
else BOLD=""; G=""; Y=""; R=""; D=""; N=""; fi
info() { echo "${G}==>${N} ${BOLD}$*${N}"; }
ok()   { echo "  ${G}✓${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; }
die()  { echo "  ${R}✗${N} $*" >&2; exit 1; }

case "${1:-}" in
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

PCAP="${1:-$HOME/teste/ids/vigia-ids-demo.pcap}"
URL="http://testmynids.org/uid/index.html"   # HTTP (texto claro) — de propósito
IFACE="any"
mkdir -p "$(dirname "$PCAP")"                 # convenção: ~/teste/<modulo>/

# ---- pré-requisitos --------------------------------------------------------
command -v suricata >/dev/null 2>&1 \
    || die "Suricata não instalado. Rode ./install/blue-deps.sh (ou instale o suricata)."
command -v tcpdump  >/dev/null 2>&1 \
    || die "tcpdump não instalado. Instale: sudo dnf install tcpdump  (ou rpm-ostree install tcpdump)."
command -v curl     >/dev/null 2>&1 || die "curl não encontrado."

# ---- regras do Suricata (sem elas: 0 alertas) ------------------------------
RULES=/var/lib/suricata/rules/suricata.rules
if [[ ! -s "$RULES" ]]; then
    info "Baixando as regras do Suricata (suricata-update — pede senha + internet)…"
    sudo suricata-update || warn "suricata-update falhou; pode não haver regras (0 alertas)."
fi

# ---- captura + disparo seguro ----------------------------------------------
info "Capturando o tráfego e disparando o teste seguro (testmynids.org)…"
( sleep 2; curl -s --max-time 5 "$URL" >/dev/null 2>&1 \
    || warn "não consegui acessar $URL (sem internet?)." ) &
sudo timeout 6 tcpdump -i "$IFACE" -w "$PCAP" >/dev/null 2>&1 || true
wait
sudo chown "$(id -un)":"$(id -gn)" "$PCAP" 2>/dev/null || true

[[ -s "$PCAP" ]] || die "não capturei nada em $PCAP (a captura precisa de sudo)."
ok "Captura salva em ${BOLD}$PCAP${N}"

# ---- auto-verificação: roda o Suricata no .pcap (igual o Vigia IDS faz) -----
info "Conferindo se o .pcap dispara alerta…"
OUT="$(mktemp -d)"
suricata -r "$PCAP" -l "$OUT" >/dev/null 2>&1 || true
N_ALERTS=0
if [[ -f "$OUT/eve.json" ]]; then
    N_ALERTS=$(grep -c '"event_type":"alert"' "$OUT/eve.json" 2>/dev/null || true)
    N_ALERTS=${N_ALERTS:-0}
fi
rm -rf "$OUT"

echo
if [[ "$N_ALERTS" -gt 0 ]]; then
    ok "${BOLD}${N_ALERTS} alerta(s)${N} no .pcap — o teste funcionou!"
    echo "  Agora, no ${BOLD}Vigia IDS${N}: aba IDS → ${BOLD}Selecionar .pcap${N} → escolha:"
    echo "    ${D}${PCAP}${N}"
    echo "  Você deve ver ${BOLD}\"GPL ATTACK_RESPONSE id check returned root\"${N}."
else
    warn "Nenhum alerta no .pcap. Causas comuns: regras ausentes (suricata-update),"
    warn "sem internet no momento da captura, ou o tráfego não passou na interface."
    echo "  Mesmo assim, dá pra abrir ${D}${PCAP}${N} no Vigia IDS para ver o fluxo."
fi
