# Deployments Manager

## Em uma frase

GUI GTK4 pra `rpm-ostree` que lista os deployments do sistema atômico
(snapshots imutáveis que aparecem no GRUB), permite **rollback / pin /
cleanup** via pkexec e adiciona camada de **labels + notas multilinha**
em JSON local 0600 pra audit LGPD.

## O que envolve

| Item | Detalhe |
|---|---|
| Pacotes wrap | `rpm-ostree`, `ostree` |
| Versão | 0.1.1 |
| App ID | `br.com.vigia.DeploymentsManager` |
| Privilégios | `pkexec` pra rollback/pin/unpin/cleanup |
| Módulo | `vigia_deployments` |
| State local | `~/.config/vigia-deployments/state.json` (0600) |

## Arquitetura interna

```
vigia_deployments/
├── backend.py          # get_deployments, rollback/pin/cleanup blocking
├── state.py            # Labels + notas (JSON 0600 atomic write)
├── window.py           # build_content() -> Adw.ToolbarView 3 tabs
└── tabs/
    ├── deployments.py  # Lista expansivel + acoes
    ├── cleanup.py      # Botao 'Limpar tudo' + alerta /boot
    └── about.py        # Manual didatico
```

State local (limit técnico: rpm-ostree não tem campo "label custom"):

```json
{
  "labels": {
    "abc123def...": "Pre instalacao do dnscrypt"
  },
  "notes": {
    "abc123def...": "Deployment 2026-05-20.\nInstalei chkrootkit pro cliente X.\nAudit semanal LGPD."
  }
}
```

Mapping é por **checksum SHA-256** do deployment (chave estável).
Quando um deployment some (cleanup), o `cleanup_orphaned()` remove o
entry correspondente.

## Comandos disparados

Status (sem root):

```bash
rpm-ostree status --json
df -m /boot
rpm-ostree db diff <commit_a> <commit_b>
```

Operações elevadas (pkexec):

```bash
pkexec rpm-ostree rollback
pkexec ostree admin pin <index>
pkexec ostree admin pin --unpin <index>
pkexec rpm-ostree cleanup -p -r -m
```

Flags do `cleanup`:
- `-p` pending — staged que ainda não bootou
- `-r` rollback — deployment de boot anterior
- `-m` metadata — refspecs em cache

## Tabs / Funcionalidades

| Tab | Função |
|---|---|
| **Deployments** | Lista de `Adw.ExpanderRow` por deployment. Header: badge STATUS + label custom + checksum/timestamp. Expandido: editar label + notas + lista de pacotes layered + botões (Reverter, Pin/Unpin) |
| **Cleanup** | Espaço em `/boot` (total/usado/disponível) + KPIs de deployments (total/pinned/will-clean) + botão `Limpar tudo` (pkexec, 1 dialog) + alerta vermelho se `/boot >85%` |
| **Sobre** | Manual didático denso (10 seções sobre deployments, atomic, pin, /boot, LGPD) |

## Status badges

| Badge | Cor | Significado |
|---|---|---|
| ATIVO | verde | `booted=true`. Rodando agora. Não pode ser removido. |
| STAGED | amarelo | `staged=true`. Pending. Vai virar ATIVO no próximo boot. Cleanup remove com `-p`. |
| ROLLBACK | cinza | Deployment anterior preservado. Cleanup remove com `-r`. |
| PIN | azul | `pinned=true`. NUNCA removido automaticamente. |

## Dataclass principal

```python
@dataclass
class Deployment:
    index: int                       # 0 = atual, 1 = anterior, etc.
    checksum: str                    # SHA-256 base commit
    base_commit: str                 # short (8 chars) display
    timestamp: int                   # epoch
    timestamp_str: str               # "2026-05-20 14:30"
    osname: str                      # 'fedora'
    origin: str                      # 'silverblue/x86_64/41'
    version: str                     # '41.20260520.0'
    booted: bool
    pinned: bool
    staged: bool
    layered_packages: list[str]
    removed_base_packages: list[str]
    unlocked: str = "none"
```

## Quando usar

- **Antes de instalar pacote experimental** com `rpm-ostree install`:
  pin o deployment atual.
- **Antes de upgrade major** (Fedora 41 -> 42): pin + adicionar nota com
  data e motivo.
- **Antes de rebase** pra outra variant (Silverblue -> Kinoite): pin.
- **Quando `/boot` >70%**: rodar cleanup pra evitar bloqueio de upgrades.
- **Audit LGPD**: documentar contexto de cada mudança importante via
  labels + notas.

## Cuidado com /boot

Em sistemas atômicos, `/boot` é tipicamente 600 MB – 1 GB. Cada deployment
usa 100-200 MB (kernel + initramfs). Com 5+ deployments pinados, `/boot`
pode encher e **impedir upgrades futuros**.

Thresholds visuais (na aba Cleanup):
- `>70%` — banner amarelo
- `>85%` — banner vermelho com sugestão de cleanup

## Limitações conhecidas (técnicas do rpm-ostree)

- **Sem criar snapshot manual** ("snapshot agora"): não existe no
  rpm-ostree. Deployments só nascem via `install`/`upgrade`/`rebase`.
  Workaround: `rpm-ostree install --idempotent <pkg-ja-instalado>`
  força um novo deployment.
- **Label do Vigia é display-only** — não modifica nada no rpm-ostree.
- **Sem deletar deployment específico** via UI — cleanup remove pending,
  rollback ou cache em batch. Pra remover um pinned, primeiro despinne.
- **Sem pkg-diff visual entre deployments arbitrários** na UI (backend
  tem `pkg_diff_blocking`, mas a tab não expõe widget — vem na v0.2).

## Trecho de código relevante

State local com atomic write + chmod 0600:

```python
def _save(state: State) -> bool:
    """Salva atomico. Retorna True se OK."""
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_PATH.parent, 0o700)
        tmp = STATE_PATH.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({
                "labels": state.labels,
                "notes": state.notes,
            }, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        tmp.replace(STATE_PATH)  # atomic
        return True
    except OSError as e:
        print(f"[state] save falhou: {e}", flush=True)
        return False
```

Cleanup all em UMA chamada pkexec (1 dialog cobre os 3 modos):

```python
def cleanup_all_blocking() -> tuple[bool, str]:
    """`pkexec rpm-ostree cleanup -p -r -m` num so call.

    -p (pending): staged que ainda nao bootou
    -r (rollback): deployment do boot anterior
    -m (cached metadata): refspecs em cache
    """
    if shutil.which("pkexec") is None:
        return False, "pkexec nao encontrado."

    rc, out, err = _run(
        ["pkexec", "rpm-ostree", "cleanup", "-p", "-r", "-m"],
        timeout=120,
    )
    if rc in (126, 127):
        return False, "Autenticacao cancelada."
    if rc != 0:
        return False, (err.strip() or out.strip() or "Falha no cleanup.")[:500]
    return True, ""
```

Parse do `rpm-ostree status --json`:

```python
def get_deployments() -> list[Deployment]:
    rc, out, _ = _run(["rpm-ostree", "status", "--json"], timeout=10)
    if rc != 0 or not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return []

    out_list: list[Deployment] = []
    for i, d in enumerate(data.get("deployments", [])):
        checksum = d.get("checksum", "") or d.get("base-checksum", "")
        out_list.append(Deployment(
            index=i,
            checksum=checksum,
            base_commit=checksum[:8] if checksum else "",
            timestamp=int(d.get("timestamp", 0)),
            timestamp_str=_format_ts(d.get("timestamp", 0)),
            osname=d.get("osname", ""),
            origin=d.get("origin", "") or d.get("container-image-reference", ""),
            version=d.get("version", ""),
            booted=bool(d.get("booted", False)),
            pinned=bool(d.get("pinned", False)),
            staged=bool(d.get("staged", False)),
            layered_packages=list(d.get("requested-packages", []) or []),
            removed_base_packages=list(d.get("requested-base-removals", []) or []),
            unlocked=d.get("unlocked", "none"),
        ))
    return out_list
```

## Privacidade / LGPD

- **100% offline**.
- **State local**: `~/.config/vigia-deployments/state.json` com mode
  `0600`, dir `0700`.
- **Operações elevadas via pkexec** (in-app polkit dialog). Nunca
  `sudo` ou shell escape.
- **Audit trail**: rpm-ostree mantém histórico completo de deployments
  com checksums. Combinado com notas + labels, você tem evidência de
  processo de mudanças (LGPD-friendly).

## Referências

- `man rpm-ostree`, `man ostree`
- Docs Silverblue: https://docs.fedoraproject.org/en-US/fedora-silverblue/
- ostree: https://www.ostree.io/
