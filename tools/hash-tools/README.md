# Vigia Hash Tools

Cálculo e verificação de hashes em arquivos e diretórios. Wrapper de
`hashdeep` + `sha256sum`/`md5sum` com UI GTK4.

## Status

v0.1.0 — alpha. Hash single + verify + baseline (criação e comparação).

## Features

- **Hash single**: SHA-256, SHA-512, SHA-1, MD5 de arquivo único
- **Verify**: compara hash conhecido vs computed
- **Baseline**: cria snapshot de diretório (hash de todos os arquivos),
  compara contra estado atual depois — alerta de added/modified/removed
- **Hashes salvos** em `~/.local/share/vigia-hash/` (permissões `0600`)
- **Aba Sobre** com manual didático

## Setup

```bash
sudo rpm-ostree install hashdeep
systemctl reboot
pip install --user -e .
vigia-hash
```

`coreutils` (sha256sum, md5sum) já vem por padrão no Fedora.

## Wrapper de

- `hashdeep` (para baseline com múltiplos algoritmos simultâneos)
- `coreutils` (sha256sum, sha512sum, sha1sum, md5sum)

## Roadmap

- v0.2: BLAKE3 (hash moderno mais rápido)
- v0.2: HMAC com chave fornecida
- v0.3: integração com File Integrity (tools complementares)
