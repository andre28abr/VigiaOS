# Monitor do Sistema

## Em uma frase

Monitor de sistema em tempo real (CPU/RAM/disco/rede/processos) que lê `/proc` e `/sys` direto **sem deps externas pip**, substituindo `htop` + `btop` + `glances` + `iotop` + `iftop` numa UI nativa libadwaita.

## O que envolve

| Item | Valor |
|---|---|
| **Pacotes Linux** | `procfs` (kernel) + `strace`/`nethogs` opcionais (inspetor de processo e aba Rede) |
| **Comando principal** | Leitura direta de `/proc/*` e `/sys/class/thermal/*` (sem subprocess) |
| **Permissões** | user para leitura; **pkexec kill** apenas para matar processo de outro user |
| **Stack** | Python 3.11, PyGObject, GTK4, libadwaita, Cairo (gráficos custom) |
| **Path config** | `~/.config/vigia/dashboard-alerts.json` (mode `0600`) |
| **Path dados** | Sem persistência — histórico em memória, perdido ao fechar |
| **App ID** | `br.com.vigia.Dashboard` |
| **Versão** | 0.4.1 |

## Arquitetura interna

6 tabs num `Adw.ViewStack` com **lazy construction** + pause/resume de timers.

- **Backend puro** em `backend.py`: dataclasses (`CpuTimes`, `CpuSnapshot`, `MemSnapshot`, `DiskSnapshot`, `NetSnapshot`, `ProcessInfo`) + funções que leem `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/dev`, `/proc/<pid>/{stat,status,cmdline,io,fd}`. CPU/disk/net usam padrão **prev + atual** (delta calculado vs snapshot anterior).
- **Gráficos** em `graphs.py`: `Sparkline`, `LineChart`, `StackedBar` desenhados em `Gtk.DrawingArea` com Cairo. Cores semânticas em `__init__.py` (`COLOR_CPU` emerald, `COLOR_RAM` amber, `COLOR_DISK` cyan, `COLOR_NET` violet).
- **Alertas** em `alerts.py`: `AlertRule` persistido + `AlertState` em memória. Tracking de "X está acima do threshold há N segundos" com `duration_sec` e `cooldown_sec`.

Lazy: somente `AlertsTab` é construída no startup (precisa rodar em background pra detectar disparos mesmo quando user está em outra tab). As outras 5 são construídas na primeira visita via `_build_if_needed(name)`. Cada tab implementa `pause_tick()` / `resume_tick()` — quando user troca de tab, os timers Cairo das tabs invisíveis são pausados (CPU reduzida).

## Comandos disparados

```bash
# Subprocess via pkexec — sob demanda, NUNCA no loop de coleta:
pkexec kill -TERM 12345                                   # matar processo de outro user
pkexec env LC_ALL=C timeout -s INT 5 strace -f -c -p PID  # inspetor de syscalls (aba Processos)
pkexec env LC_ALL=C nethogs -t -c 4 -d 1                  # banda por processo (aba Rede)
```

A **coleta de métricas** não usa `ps`/`top`/`iostat`/`vmstat` — é 100% leitura direta de file (os 3 subprocess acima são ações pontuais opt-in, fora do loop de refresh):

```
/proc/stat        -> CPU times por core
/proc/meminfo     -> RAM, swap, cache, buffers
/proc/diskstats   -> sectors read/written por device
/proc/net/dev     -> RX/TX bytes por interface
/proc/loadavg     -> load average
/proc/uptime      -> boot time
/proc/<pid>/stat       -> PID metadata + CPU time
/proc/<pid>/status     -> RSS, Uid
/proc/<pid>/cmdline    -> linha de comando
/proc/<pid>/io         -> read_bytes/write_bytes (per-process I/O)
/proc/<pid>/fd/*       -> conexoes TCP/UDP via inode lookup
/proc/<pid>/loginuid   -> conta usuarios logados (cache TTL 30s)
/sys/class/thermal/thermal_zone*/temp  -> temperatura
```

## Tabs / Funcionalidades

### Visão Geral (1Hz)

Hero com hostname + **selo da plataforma** (pill colorido; rótulo via `backend.get_platform_label()` lendo `NAME`/`VARIANT` de `/etc/os-release`, ex.: *Fedora Workstation*) + distro + uptime + load avg (3 KPI cards: 1min/5min/15min). Sparklines de **CPU**, **Memória**, **Rede ↓**, **Rede ↑** com 60s de histórico. Lista de discos com barras de uso e top 3 processos por CPU + top 3 por memória.

### Recursos (1Hz)

Gráficos detalhados:

- **CPU** — `LineChart` per-core, frequência atual (MHz), temperatura (max entre `thermal_zone*`)
- **Memória** — `StackedBar` decompondo `used / cached / buffers / free`, total em GB, swap
- **Disco** — barras de uso por mountpoint + sparkline de I/O (`MB/s read + write` por device)
- **Rede** — sparkline RX/TX por interface

### Processos (2Hz)

Top 30 processos com filtros:
- Search por nome ou cmdline
- Sort: CPU / Memória / I/O (read+write) / Conexões ativas / PID / Nome
- Switch "Só meus" — filtra pelo UID atual
- Botão **Kill** com confirmação (default `SIGTERM`, opção `SIGKILL`). Se `os.kill` retorna `PermissionError`, chama `pkexec kill` automaticamente.
- Botão **Inspecionar** por processo: `pkexec … strace -f -c -p PID` (~5s) → resumo de syscalls (`proc_inspect.py`). Só aparece com `strace` instalado.

### Rede (snapshot via pkexec)

Banda **por processo** via `nethogs -t` (tracemode). Snapshot pontual (`pkexec env LC_ALL=C nethogs -t -c 4 -d 1`, ~4s) parseado em `net_bandwidth.py` → `ProcBandwidth(program, pid, sent_kbps, recv_kbps, attributed)`. Lazy: o `nethogs` só roda no clique de **Medir banda**.

- **Atribuído** (`pid>0`): nethogs mapeou a conexão a um processo → `programa + PID`.
- **Não-atribuído** (`pid 0`; conexão pré-existente que o nethogs não viu nascer): mostra o **endpoint remoto** (`ip:porta`) — ainda útil pra exfiltração. Cobre o caso do `iftop` (banda por conexão), por isso o iftop saiu do catálogo.

`LC_ALL=C` força ponto decimal (locale pt-BR sairia com vírgula, quebrando o `float`). Tráfego zero é ignorado; dedup por (rótulo, pid) mantendo a última refresh.

### Alertas

Regras configuráveis persistidas em `~/.config/vigia/dashboard-alerts.json`:

| Metric | Range | Default threshold |
|---|---|---|
| `cpu_pct` | 0-100% | > 95% |
| `mem_pct` | 0-100% | > 90% |
| `swap_pct` | 0-100% | > 50% |
| `load_1` | 0-100 | > 4.0 |
| `cpu_temp_c` | 0-150 °C | > 85 °C |
| `disk_pct_root` | 0-100% | > 90% |
| `disk_pct_home` | 0-100% | > 90% |

Cada `AlertRule` tem `duration_sec` (tempo mínimo violando antes de disparar) e `cooldown_sec` (min entre alertas do mesmo rule). Operador `gt` ou `lt`.

### Sobre

Versão + info do sistema + paths lidos + lista de dependências (vazia — usa só kernel interface).

## Quando usar

- Você precisa diagnosticar lentidão: "quem está puxando CPU?", "swap está cheio?", "disco está saturado?"
- Você quer matar um processo travado sem abrir terminal
- Você quer **alarmar** quando RAM passar de 90% (LGPD: detectar leak antes de OOM kill)
- Você quer monitor leve rodando full-time embarcado no Hub

## Limitações conhecidas

- Sem histórico em disco — fechou, perdeu. Pra histórico use `prometheus-node-exporter` + Grafana.
- Temperatura via `/sys/class/thermal/thermal_zone*/temp` nem sempre reflete CPU "real" — depende do firmware. Em ARM ou laptops antigos pode mostrar `None`.
- Kill via `pkexec` pede senha **a cada kill** de processo de outro user. Sem persistência.
- `n_tcp_established` por processo faz lookup em `/proc/net/tcp{,6}/udp{,6}` por inode — pode ficar pesado com 1000+ processos.

## Trecho de código relevante

Kill com fallback automático pra pkexec:

```python
# tools/dashboard/src/vigia_dashboard/backend.py
def kill_process(pid: int, sig: int = _signal.SIGTERM) -> tuple[bool, str]:
    if pid <= 0:
        return False, "PID invalido."
    try:
        os.kill(pid, sig)
        return True, ""
    except PermissionError:
        if shutil.which("pkexec") is None:
            return False, "Sem permissao e pkexec nao encontrado."
        sig_name = "TERM" if sig == _signal.SIGTERM else "KILL"
        result = subprocess.run(
            ["pkexec", "kill", f"-{sig_name}", str(pid)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode in (126, 127):
            return False, "Autenticacao cancelada."
        ...
```

Lazy tabs + pause de timers:

```python
# tools/dashboard/src/vigia_dashboard/window.py
def _on_visible_child_changed(stk, _pspec):
    visible_name = stk.get_visible_child_name()
    _build_if_needed(visible_name)
    for name, tab in tabs.items():
        if tab is None:
            continue
        if name == visible_name:
            tab.resume_tick()
        elif name != "alerts":  # Alerts sempre ativo
            tab.pause_tick()
```
