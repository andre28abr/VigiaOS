# Vigia IDS — manual técnico

Módulo de **Detecção** do **VigiaBlue**. Painel de leitura para o IDS de rede
**Suricata**: parseia o **`eve.json`** (formato JSONL) e apresenta os eventos
`event_type=="alert"` triados por severidade — mesmo padrão visual do Vigia
SIEM/YARA.

## Dois modos

1. **Ler eve.json existente** (de um Suricata em execução). **Não** exige o
   Suricata instalado — é só leitura de arquivo.
2. **Analisar um pcap**: roda `suricata -r <pcap> -l <outdir>` e lê o `eve.json`
   gerado (exige `suricata`).

## Arquivos

```
tools/vigia-blue/src/vigia_blue/modules/ids/
├── __init__.py
├── backend.py     # parser eve.json + cmd builder + análise + relatórios (PURO+IO)
└── page.py        # GUI: Alertas / Histórico / Sobre

tests/blue/test_ids_backend.py   # 12 testes
tools/vigia-blue/docs/manuals/{leigo,tecnico}/ids.md
```

## Backend (`backend.py`)

Puro/testável (sem suricata, sem gi):
- **`parse_eve(jsonl) -> list[Alert]`** — uma linha = um objeto JSON. Mantém só
  `event_type=="alert"`; extrai `alert.signature/category/severity/signature_id`,
  `src_ip:src_port`, `dest_ip:dest_port`, `proto`. Ignora linhas vazias, JSON
  inválido e eventos que não são alerta. Nunca crasha.
- **`map_severity(n)`** — Suricata usa 1=alta … 3+=baixa. Mapeia: 1→`alto`,
  2→`suspeito`, 3→`baixo`, ≥4→`info`; inválido→`suspeito`.
- **`build_pcap_cmd(pcap, outdir)`** — `["suricata","-r",pcap,"-l",outdir]`
  (lista, nunca shell string).

Toca disco/sistema:
- **`find_eve()`** — primeiro `eve.json` existente nos caminhos padrão
  (`/var/log/suricata/eve.json`).
- **`analyze_eve(path, max_alerts)`** — lê (com `_read_tail`: só a cauda se o
  arquivo for gigante — eve.json cresce sem parar), parseia, ordena por
  severidade, limita.
- **`analyze_pcap(pcap, timeout)`** — `tempfile.mkdtemp` + `proc.run` do
  `build_pcap_cmd` + lê o `eve.json` gerado. Nunca levanta.
- Relatórios **0600** em `~/.local/share/vigia-ids/analysis-*.json`
  (`save_report`/`list_recent_reports`).

## GUI (`page.py`)

`build_content()` → `ToolbarView` + `ViewSwitcher` (Alertas / Histórico / Sobre).
- **Alertas** (`_AlertsView`): linha do `eve.json` (auto-detectado via `find_eve`
  ou escolhido por `Gtk.FileDialog`), botão **Analisar eve.json**, e uma linha
  separada **Analisar .pcap** (habilitada só se `suricata_available()`). A análise
  roda em `threading.Thread` → `idle_add`. Banner se faltar eve.json **e**
  Suricata. Alerta = `ExpanderRow` (assinatura + categoria + pílula; expande
  Origem/Destino/Protocolo/Quando/SID).
- **Histórico**: `list_recent_reports()`.

## Privilégio / LGPD

- Ler eve.json do usuário roda **sem root**. (Em `/var/log/suricata`, o acesso
  depende da permissão do arquivo; pkexec p/ paths root fica como pendência.)
- Relatórios **0600**; nada sai da máquina.

## Pendências (próximos passos)

1. **pkexec** para ler eve.json em `/var/log/suricata` quando sem permissão.
2. Filtros (por severidade, por IP, por assinatura) e agrupamento por SID.
3. Live tail do eve.json (acompanhar em tempo real).
4. Gestão de regras do Suricata (habilitar/atualizar rulesets).
