#!/usr/bin/env bash
#
# test-samples.sh — cria AMOSTRAS DE TESTE seguras para os módulos do VigiaOS,
# organizadas na convenção do projeto:  ~/teste/<modulo>/
#
# Tudo é fictício e inofensivo (formatos de CPF/cartão de teste, a chave AWS de
# exemplo da documentação, o arquivo EICAR padrão de antivírus, IPs/domínios
# reservados para testes — RFC 5737/2606). Não baixa nada, não pede senha, não
# liga serviço; só escreve arquivos na sua pasta pessoal.
#
# Uso:
#   ./install/test-samples.sh          # gera amostras de todos os módulos
#
# Depois, em cada módulo do VigiaBlue, aponte para a pasta correspondente.
#
set -uo pipefail

if [[ -t 1 ]]; then
    BOLD=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; D=$'\e[2m'; N=$'\e[0m'
else BOLD=""; G=""; Y=""; D=""; N=""; fi
info() { echo "${G}==>${N} ${BOLD}$*${N}"; }
ok()   { echo "  ${G}✓${N} $*"; }

case "${1:-}" in -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;; esac

TEST_BASE="$HOME/teste"
info "Criando amostras de teste em ${BOLD}$TEST_BASE${N}"

# ============================================================
# Vigia YARA  →  ~/teste/yara/  (arquivos para escanear)
# ============================================================
YDIR="$TEST_BASE/yara"; mkdir -p "$YDIR"

# EICAR — arquivo-teste padrão de antivírus (inofensivo). Dispara EICAR_Test_File.
printf '%s\n' 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' \
    > "$YDIR/eicar.txt"

# Dados pessoais fictícios — dispara as regras LGPD (CPF/CNPJ/e-mail/tel/cartão).
cat > "$YDIR/clientes-lgpd.txt" <<'EOF'
FICHA DE CLIENTE — ARQUIVO DE TESTE (dados fictícios, não são reais)

Nome:      Fulano de Tal
CPF:       123.456.789-09
Empresa:   12.345.678/0001-99   (CNPJ)
E-mail:    fulano@exemplo.com
Telefone:  (11) 91234-5678
Cartão:    1234 5678 9012 3456   (número de teste)
EOF

# Segredos fictícios — dispara as regras de Credenciais (chave/AWS/senha).
cat > "$YDIR/credenciais-vazadas.txt" <<'EOF'
ARQUIVO DE TESTE — credenciais fictícias (NÃO são reais)

# Chave AWS de exemplo (da própria documentação da AWS):
aws_access_key_id = AKIAIOSFODNN7EXAMPLE

# Senha em texto:
password = "senha-de-teste-123"

# Cabeçalho de chave privada:
-----BEGIN RSA PRIVATE KEY-----
ESTE-E-UM-CONTEUDO-FICTICIO-DE-TESTE-NAO-E-UMA-CHAVE-REAL
-----END RSA PRIVATE KEY-----
EOF

cat > "$YDIR/LEIA-ME.txt" <<'EOF'
Pasta de teste do Vigia YARA.

Como usar: abra o VigiaBlue → Vigia YARA → "Selecionar" → escolha ESTA pasta
(~/teste/yara) → Escanear. Você deve ver alertas:
  - eicar.txt              → EICAR (teste de antivírus)
  - clientes-lgpd.txt      → CPF / CNPJ / e-mail / telefone / cartão (LGPD)
  - credenciais-vazadas.txt→ AWS / senha / chave privada (Credenciais)

Tudo aqui é fictício e inofensivo.
EOF
ok "yara/  (eicar, clientes-lgpd, credenciais-vazadas)"

# ============================================================
# Vigia Intel  →  ~/teste/intel/  (IOCs + indicadores p/ checar)
# ============================================================
IDIR="$TEST_BASE/intel"; mkdir -p "$IDIR"

# IOCs para IMPORTAR na base (IPs/domínios reservados p/ teste — nunca reais).
cat > "$IDIR/iocs-exemplo.txt" <<'EOF'
# Lista de IOCs de exemplo (importar no Vigia Intel → aba IOCs → Importar)
203.0.113.5
198.51.100.23
evil.example.com
phishing.example.net
44d88612fea8a8f36de82e1278abb02f
golpista@exemplo.org
EOF

# Indicadores para COLAR em "Verificar" (uns casam, outros não).
cat > "$IDIR/indicadores-para-verificar.txt" <<'EOF'
203.0.113.5
8.8.8.8
evil.example.com
google.com
44d88612fea8a8f36de82e1278abb02f
EOF

cat > "$IDIR/LEIA-ME.txt" <<'EOF'
Pasta de teste do Vigia Intel.

1) VigiaBlue → Vigia Intel → aba "IOCs" → Importar → escolha iocs-exemplo.txt.
2) Vá na aba "Verificar", cole o conteúdo de indicadores-para-verificar.txt e
   clique em Verificar.

Devem CASAR (estão na base):  203.0.113.5, evil.example.com, 44d88612...
NÃO devem casar:              8.8.8.8 (Google DNS), google.com

São endereços/domínios reservados para teste (RFC 5737/2606) — nunca reais.
EOF
ok "intel/  (iocs-exemplo, indicadores-para-verificar)"

# ============================================================
# Vigia Timeline  →  ~/teste/timeline/  (export json_line — sem precisar de plaso)
# ============================================================
TDIR="$TEST_BASE/timeline"; mkdir -p "$TDIR"
cat > "$TDIR/timeline-exemplo.jsonl" <<'EOF'
{"datetime":"2026-06-02T09:00:00","message":"Arquivo /home/user/contrato.docx criado","data_type":"fs:stat","source_long":"File stat"}
{"datetime":"2026-06-02T09:05:12","message":"Usuario abriu /home/user/relatorio.pdf","data_type":"fs:stat","source_long":"File stat"}
{"datetime":"2026-06-02T09:10:30","message":"Login via SSH de 203.0.113.5 aceito para o usuario andre","data_type":"syslog:line","source_long":"Syslog"}
{"datetime":"2026-06-02T09:12:45","message":"Comando executado: sudo systemctl restart sshd","data_type":"bash:history:command","source_long":"Bash History"}
{"datetime":"2026-06-02T09:20:01","message":"Pacote instalado: nginx-1.25","data_type":"rpm:installation","source_long":"RPM"}
EOF
cat > "$TDIR/LEIA-ME.txt" <<'EOF'
Pasta de teste do Vigia Timeline.

VigiaBlue → Vigia Timeline → "Abrir" (export json_line) → escolha
timeline-exemplo.jsonl. Os eventos aparecem em ordem de tempo. Não precisa do
plaso instalado — é um export pronto, fictício.
EOF
ok "timeline/  (timeline-exemplo.jsonl)"

# ============================================================
# Vigia IDS  →  ~/teste/ids/  (o .pcap é gerado pelo ids-demo.sh)
# ============================================================
DDIR="$TEST_BASE/ids"; mkdir -p "$DDIR"
cat > "$DDIR/LEIA-ME.txt" <<'EOF'
Pasta de teste do Vigia IDS.

O .pcap de teste é gerado por outro script (precisa de suricata + tcpdump + sudo):
    ./install/ids-demo.sh
Ele cria  ~/teste/ids/vigia-ids-demo.pcap  e você abre em
VigiaBlue → Vigia IDS → "Selecionar .pcap".
EOF
ok "ids/  (use ./install/ids-demo.sh para gerar o .pcap)"

# ============================================================
# LEIA-ME geral
# ============================================================
cat > "$TEST_BASE/LEIA-ME.txt" <<'EOF'
Amostras de teste do VigiaOS — geradas por install/test-samples.sh.

Uma pasta por módulo:
  yara/      arquivos para escanear (EICAR, LGPD, credenciais)
  intel/     IOCs para importar + indicadores para verificar
  timeline/  export de timeline (json_line) pronto para abrir
  ids/       (o .pcap vem do ./install/ids-demo.sh)

Sem amostra estática (precisam de coisa real):
  SIEM       lê os eventos do sistema ao vivo (nada para colocar aqui)
  Memory     precisa de um dump real de RAM (capturado com AVML/LiME)
  Playbooks  não usa arquivo externo

Tudo aqui é fictício e inofensivo. Pode apagar a pasta quando quiser.
EOF

echo
info "Pronto. Estrutura criada:"
echo "  ${D}$TEST_BASE/${N}"
for d in yara intel timeline ids; do
    echo "  ${D}├── $d/${N}"
done
echo
echo "Abra cada módulo no VigiaBlue e aponte para a pasta correspondente."
echo "Detalhes em cada ${BOLD}LEIA-ME.txt${N}."
