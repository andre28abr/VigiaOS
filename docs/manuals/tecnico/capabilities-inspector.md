# Capabilities Inspector

## Em uma frase

Audita Linux capabilities setadas em binarios do sistema via `getcap -r`,
classifica por risco (alto/medio/baixo) e expoe um catalogo pt-BR das 41
capabilities documentadas.

## O que envolve

| Item | Detalhe |
|---|---|
| Pacotes wrap | `libcap`, `getcap` |
| Versao | 0.1.0 (read-only) |
| App ID | `br.com.vigia.CapabilitiesInspector` |
| Privilegios | `pkexec` apenas pra scan elevado (cobertura total) |
| Tipo | Read-only (sem `setcap` nesta release) |
| Saidas | Lista in-memory + UI (nao persiste reports) |
| Modulo | `vigia_caps` |

## Arquitetura interna

```
vigia_caps/
├── backend.py          # scan_binaries_user(), scan_binaries_elevated()
├── capabilities.py     # CATALOGO de 41 caps + risk classifier
├── window.py           # build_content() -> Adw.ToolbarView 4 tabs
└── tabs/
    ├── overview.py     # Hero + KPI counts + botoes Scan / Quick scan
    ├── binaries.py     # Lista filtravel (search + dropdown risco)
    ├── catalog.py      # 41 caps com descricao pt-BR + risco
    └── about.py        # Manual didatico
```

Dois caminhos de scan:

- **Quick scan** (user mode, sem pkexec): roda `getcap -r` em `/usr/bin`,
  `/usr/sbin`, `/usr/libexec`, `/usr/local/bin`, `/usr/local/sbin`, `/opt`.
  Cobertura parcial mas instantanea.
- **Scan completo** (pkexec): um unico dialog cobre `/usr`, `/opt`, `/var`,
  `/srv`. Leva 5-30s. Usa wrapper bash com `set +e` pra ignorar codigos
  de retorno nao-zero do getcap em paths vazios.

## Comandos disparados

Quick scan (sem privilegios):
```bash
getcap -r /usr/bin
getcap -r /usr/sbin
getcap -r /usr/libexec
getcap -r /usr/local/bin
getcap -r /usr/local/sbin
getcap -r /opt
```

Scan elevado (pkexec, 1 dialog):
```bash
pkexec bash -c '
set +e
for path in /usr /opt /var /srv; do
    [ -d "$path" ] && getcap -r "$path" 2>/dev/null
done
exit 0
'
```

Inspect ad-hoc de um binario:
```bash
getcap /usr/bin/ping
# /usr/bin/ping cap_net_raw=ep
```

## Tabs / Funcionalidades

| Tab | Funcao |
|---|---|
| **Visao Geral** | Hero com state label (verde/amarelo/vermelho), KPIs por risco, 2 botoes (Scan elevado + Quick scan) |
| **Binarios** | Lista de `BinaryWithCaps` filtravel via `SearchEntry` + `DropDown` (Todos/Alto/Medio/Baixo). Cada row expansivel mostra TODAS as caps |
| **Capabilities** | Catalogo das 41 caps Linux com descricao pt-BR e classe de risco |
| **Sobre** | Manual didatico (`AboutTab` padrao Vigia) |

## Catalogo de risco

Classificacao opinada (vide `capabilities.py`):

- **ALTO** (10 caps): bypass efetivo do modelo de seguranca.
  `cap_dac_override`, `cap_mac_admin`, `cap_mac_override`, `cap_setgid`,
  `cap_setpcap`, `cap_setuid`, `cap_sys_admin`, `cap_sys_boot`,
  `cap_sys_module`, `cap_sys_ptrace`, `cap_sys_rawio`.
- **MEDIO** (~17 caps): potencialmente perigosas, mas escopadas.
  `cap_chown`, `cap_dac_read_search`, `cap_net_admin`, `cap_net_raw`,
  `cap_kill`, `cap_setfcap`, `cap_sys_chroot`, etc.
- **BAIXO** (~14 caps): especificas, usadas por daemons normais.
  `cap_net_bind_service`, `cap_audit_write`, `cap_ipc_lock`, etc.

Lookup ignora case e o prefix `cap_` (opcional):

```python
from vigia_caps.capabilities import get_capability, risk_for_cap
risk_for_cap("net_raw")     # 'medio'
risk_for_cap("CAP_SETUID")  # 'alto'
```

## Quando usar

- **Apos `rpm-ostree upgrade`**: verifica se algum binario novo ganhou
  capability inesperada.
- **Apos incidente suspeito**: caca por `cap_sys_admin` ou `cap_setuid`
  em paths nao-canonicos (`/tmp`, `/home`, `/var/tmp`).
- **Audit periodico LGPD**: documenta superficie de privilege escalation
  via filesystem caps.
- **Investigacao de exploit**: combina com [GTFOBins](https://gtfobins.github.io/)
  pra checar se algum binario com cap pode ser explorado.

## Limitacoes conhecidas

- Read-only — nao executa `setcap` pra add/remover caps (chega na v0.2).
- So inspeciona **filesystem capabilities** (caps de arquivo). NAO
  inspeciona thread capabilities setadas em runtime via `prctl()`.
- Catalogo de risco e opiniao informada — algumas caps classificadas
  como MEDIO podem ser ALTO num threat model especifico (ex: `cap_net_admin`
  em servidor exposto).
- Quick scan perde paths em `/root`, `/var`, `/srv` (precisa do scan
  elevado pra cobertura total).

## Trecho de codigo relevante

Scan elevado com pkexec (1 dialog cobre todos os paths):

```python
def scan_binaries_elevated() -> tuple[list[BinaryWithCaps], str]:
    """Scan completo via pkexec. UM dialog cobre todos os paths."""
    if not getcap_available():
        return [], "getcap nao instalado (pacote libcap)."

    paths_str = " ".join(SCAN_PATHS_FULL)  # /usr /opt /var /srv
    script = f"""set +e
for path in {paths_str}; do
    [ -d "$path" ] && getcap -r "$path" 2>/dev/null
done
exit 0
"""
    rc, out, err = _run(["pkexec", "bash", "-c", script], timeout=120)
    if rc in (126, 127):
        return [], "Autenticacao cancelada."
    if rc != 0 and not out:
        return [], (err.strip() or "Falha no scan.")
    return parse_getcap_output(out), ""
```

Parser do output do `getcap`:

```python
_GETCAP_LINE_RE = re.compile(r"^(.+?)\s+([a-zA-Z_,=+\-]+)$")

def parse_getcap_output(text: str) -> list[BinaryWithCaps]:
    """Formato esperado:
      /usr/bin/ping cap_net_raw=ep
      /usr/bin/example cap_net_admin,cap_net_raw=ep
    """
    binaries: list[BinaryWithCaps] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("getcap:"):
            continue
        m = _GETCAP_LINE_RE.match(line)
        if not m:
            continue
        binaries.append(BinaryWithCaps(
            path=m.group(1).strip(),
            capabilities=[m.group(2).strip()],
        ))
    return binaries
```

## Referencias

- `man capabilities(7)`
- `man getcap`, `man setcap`
- [GTFOBins](https://gtfobins.github.io/) — binarios SUID/cap explotaveis
- Kernel docs: https://www.kernel.org/doc/html/latest/security/credentials.html
