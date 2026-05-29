# Vigia Capabilities Inspector

Auditoria de **Linux capabilities** (via `getcap`) com UI GTK4. Parte do [VigiaOS](../../README.md).

## O que faz

- Escaneia o sistema procurando binarios com capabilities setadas (`setcap`)
- Classifica cada cap em **ALTO / MEDIO / BAIXO** (~40 capabilities catalogadas pt-BR)
- Mostra hero card com contagem total + risco mais alto
- Lista filtravel: por risco, por path, por capability
- Catalogo de referencia das 40 capabilities do kernel Linux

## Pre-requisitos

```bash
# Confirma que getcap esta no PATH
which getcap
```

`getcap` faz parte do pacote `libcap` que vem por padrao em Fedora Silverblue.

## Como rodar

```bash
cd tools/capabilities-inspector
pip install --user -e .
vigia-caps
```

Ou via Vigia Hub.

## Tabs

- **Visao Geral**: hero card + KPIs + botoes de scan
- **Binarios**: lista filtravel (risco + search) com expansao mostrando cada cap
- **Capabilities**: catalogo de referencia das 40 caps com descricao pt-BR
- **Sobre**: manual didatico

## Classes de risco

| Risco | Exemplos | Por que perigoso |
|-------|----------|------------------|
| **ALTO** | `cap_sys_admin`, `cap_setuid`, `cap_dac_override`, `cap_sys_module`, `cap_mac_admin` | Bypass efetivo do modelo de seguranca (vira root) |
| **MEDIO** | `cap_net_admin`, `cap_chown`, `cap_kill`, `cap_sys_ptrace` | Acoes potencialmente perigosas, mas escopadas |
| **BAIXO** | `cap_net_bind_service`, `cap_audit_write`, `cap_net_raw` | Especificas, usadas frequentemente por daemons |

## Limitacoes v0.1

- Read-only — nao adiciona/remove capabilities via `setcap`
- Nao inspeciona thread capabilities (so file capabilities)
- Scan completo precisa pkexec (5-30s); quick scan e' instantaneo mas perde paths root-only

## Roadmap (v0.2+)

- Remover capability de um binario (com confirmacao destructive)
- Detectar **diff** entre 2 scans (ver o que apareceu/sumiu apos upgrade)
- Comparar com whitelist de pacote ("o que veio do upstream vs o que foi modificado")
- Detectar binarios em `/tmp`, `/home`, `/var/tmp` com capabilities (vetor classico de persistence)
