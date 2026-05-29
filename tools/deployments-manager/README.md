# Vigia Deployments Manager

GUI pra gerenciar **deployments do rpm-ostree** — os "snapshots" que
aparecem no menu do GRUB ao bootar. Parte do [VigiaOS](../../README.md).

## O que faz

- **Lista deployments** (atual, rollback, staged, pinados)
- **Rollback** pro deployment anterior (1 click + pkexec)
- **Pin/Unpin** — protege deployment do cleanup automatico
- **Cleanup all** em 1 click (`pkexec rpm-ostree cleanup -p -r -m`)
- **Alerta de /boot cheio** (banner amarelo >70%, vermelho >85%)
- **Label customizado + notas multilinha** por deployment (LGPD/audit)

## Pre-requisitos

- Sistema **Fedora Atomic** (Silverblue, Kinoite, Bluefin, Bazzite, Aurora)
- `rpm-ostree` (vem por padrao em todos os atomic)

## Como rodar

Embedded no **Vigia Hub** (recomendado):
```bash
vigia-hub
# Aba lateral: "Deployments Manager"
```

Standalone:
```bash
cd tools/deployments-manager
pip install --user -e .
vigia-deployments
```

## Conceitos

**Deployment**: snapshot completo e imutavel do sistema. Criado a cada
`rpm-ostree install/upgrade/rebase`. Atomico — ou tudo deu certo, ou
nada mudou.

**Pinado**: deployment protegido contra cleanup automatico. Usa antes
de operacoes arriscadas (upgrade major, layer driver proprietario, etc.).

**Rollback**: deployment anterior, preservado pra emergencia. Voce pode
voltar pra ele via GRUB ou via esta tool.

**Staged/Pending**: deployment criado por `install/upgrade` mas que
ainda nao bootou. Vira o ativo no proximo reboot.

## Estado local (labels + notas)

`~/.config/vigia-deployments/state.json` com mode 0600 (owner-only):

```json
{
  "labels": {
    "<checksum>": "Pre instalacao do dnscrypt"
  },
  "notes": {
    "<checksum>": "Deployment de 2026-05-20. Audit LGPD semanal."
  }
}
```

rpm-ostree NAO suporta nome customizado nativo — labels e notas sao
**display only** no Vigia, mas armazenados local pra LGPD/audit.

## Cuidados com `/boot`

A particao `/boot` em sistemas atomicos eh pequena (geralmente 600MB-1GB).
Cada deployment usa 100-200MB la dentro (kernel + initramfs).

**Recomendado**: cleanup periodico (ex: mensal). A tool alerta quando
`/boot` esta >70% ou >85%.

## LGPD

- 100% offline — nenhum dado vai pra rede
- State em `~/.config/vigia-deployments/state.json` com mode 0600
- Operacoes elevadas usam `pkexec` (in-app polkit dialog)
- Audit trail nativo do rpm-ostree (checksums + timestamps)
- Combinado com labels + notas = evidencia de processo de mudancas
