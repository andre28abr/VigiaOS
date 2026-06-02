#!/usr/bin/env bash
#
# _mem_capture.sh — INTERNO. Rodado via pkexec (como root) pelo Vigia Memory
# quando o usuário clica em "Capturar memória agora".
#
# Captura a RAM desta máquina num arquivo (formato LiME) usando o AVML e DEVOLVE
# a posse do arquivo ao usuário (foi criado como root), com permissão 0600 — o
# dump tem dados sensíveis (senhas, chaves) e o projeto preza minimum surface
# (LGPD). Tudo num diálogo de senha só.
#
# Uso (não chame direto; é o Vigia Memory quem chama):
#   pkexec _mem_capture.sh <avml_path> <out_file> <usuario>
#
# Segurança: valida que <out_file> está sob ~/teste/memory/ (impede gravar/chown
# em lugar perigoso) e que <avml_path> é um executável. argv vem do app (não do
# usuário), mas validamos mesmo assim.
#
set -uo pipefail

AVML="${1:?caminho do avml}"
OUT="${2:?arquivo de saida}"
OWNER="${3:?usuario}"

case "$OUT" in
    */teste/memory/*) : ;;
    *) echo "saída fora do esperado (~/teste/memory/)" >&2; exit 2 ;;
esac
[[ -x "$AVML" ]] || { echo "avml não encontrado/executável: $AVML" >&2; exit 2; }

OUTDIR="$(dirname "$OUT")"
mkdir -p "$OUTDIR"

# Captura a RAM física. O AVML auto-detecta a fonte (/proc/kcore, /dev/crash,
# /dev/mem) e grava em formato LiME — que o Volatility 3 lê.
"$AVML" "$OUT" >/dev/null 2>&1 || { echo "falha na captura (avml)" >&2; exit 3; }

# Devolve a posse ao usuário + permissão restrita (dump = dados sensíveis).
chown "$OWNER" "$OUT" 2>/dev/null || true
chmod 0600 "$OUT" 2>/dev/null || true
