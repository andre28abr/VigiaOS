#!/usr/bin/env bash
# Compila os defaults do dconf em /etc/dconf/db/local.
# Roda no contexto do build container.

set -oue pipefail

echo "Compilando dconf db 'local' a partir de /etc/dconf/db/local.d/"
dconf update
echo "OK"
