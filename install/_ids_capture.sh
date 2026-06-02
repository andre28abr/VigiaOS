#!/usr/bin/env bash
#
# _ids_capture.sh — INTERNO. Rodado via pkexec (como root) pelo Vigia IDS quando
# o usuário clica em "Capturar tráfego agora".
#
# Captura N segundos de tráfego num .pcap, roda o Suricata sobre ele e DEVOLVE a
# posse dos arquivos ao usuário (eram criados como root). Tudo num diálogo de
# senha só.
#
# Uso (não chame direto; é o Vigia IDS quem chama):
#   pkexec _ids_capture.sh <segundos> <out_dir> <usuario>
#
# Segurança: valida que <segundos> é número e que <out_dir> está sob ~/teste/ids/
# (impede um chown -R recursivo em lugar perigoso). argv vem do app (não do
# usuário), mas validamos mesmo assim.
#
set -uo pipefail

SECS="${1:?segundos}"
OUTDIR="${2:?diretorio de saida}"
OWNER="${3:?usuario}"

[[ "$SECS" =~ ^[0-9]+$ ]] || { echo "segundos inválido" >&2; exit 2; }
case "$OUTDIR" in
    */teste/ids/*) : ;;
    *) echo "diretório fora do esperado (~/teste/ids/)" >&2; exit 2 ;;
esac

mkdir -p "$OUTDIR"
PCAP="$OUTDIR/captura.pcap"

# 1) captura por SECS segundos (o timeout encerra o tcpdump no fim)
timeout "$SECS" tcpdump -i any -w "$PCAP" >/dev/null 2>&1 || true

# 2) analisa a captura com o Suricata (gera eve.json em OUTDIR)
suricata -r "$PCAP" -l "$OUTDIR" >/dev/null 2>&1 || true

# 3) devolve a posse ao usuário (os arquivos foram criados como root)
chown -R "$OWNER" "$OUTDIR" 2>/dev/null || true
