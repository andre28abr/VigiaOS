# Vigia Activity Log

> Parseador de logs do sistema com narrativa human-readable.
> Converte ruído de `auditd` / `journald` / `fail2ban` em frases que
> dizem **o que aconteceu**, **quem fez**, **quando** e **por quê é notável**.

## Estado

🔴 **Não implementado** — apenas design.

## Problema

Logs do Linux são detalhados mas extremamente verbosos. `journalctl` e
`audit.log` são otimizados para máquina, não para humano. Quando você quer
saber "**houve algo suspeito hoje?**", precisa garimpar manualmente entre
milhares de entradas irrelevantes.

## Solução proposta

Um CLI (e depois TUI/GUI) que:

1. Lê fontes de log conhecidas (audit, journal, fail2ban, firewalld, tcpdump)
2. Filtra eventos rotineiros / de baixo interesse
3. Correlaciona eventos relacionados (ex: SSH falha → fail2ban ban → conexão recusada)
4. Reescreve em **linguagem natural** com contexto:
   - "Às 14:23, fail2ban baniu 192.0.2.1 após 5 tentativas falhas de SSH em 2 minutos"
   - "Às 15:07, SELinux bloqueou processo `httpd` de escrever em `/var/www/uploads/`. Política em uso: targeted. Domínio: `httpd_t`. Provável ação legítima — verificar contexto da pasta."
   - "Às 16:30, processo `firefox` (PID 4521) abriu conexões para 142.250.x.x (Google) e 152.199.x.x (Akamai/Adobe). Padrão normal de navegação."

## Decisões pendentes

- **Linguagem**: Python (rápido para prototipar, fácil para parser e GUI) ou Rust (perf, system service)
- **Form factor v1**: CLI puro (`vigia-log`), TUI estilo `btop`, ou GTK4 GUI direto?
- **Fontes de log v1**: começar com audit + fail2ban (mais ricos em "ações") ou journald (mais amplo)?
- **Cobertura temporal**: últimas 24h por default? Configurável?

## Arquitetura (rascunho)

```
vigia-activity-log/
├── pyproject.toml          # (se Python)
├── src/vigia_activity_log/
│   ├── __init__.py
│   ├── cli.py              # entrypoint
│   ├── sources/            # adapters de cada fonte de log
│   │   ├── auditd.py
│   │   ├── journald.py
│   │   ├── fail2ban.py
│   │   └── firewalld.py
│   ├── correlator.py       # liga eventos relacionados
│   ├── classifier.py       # rotineiro / interessante / suspeito
│   ├── narrator.py         # gera o texto human-readable
│   └── ui/
│       ├── cli.py          # output texto/tabela
│       └── tui.py          # opcional, com textual ou urwid
├── tests/
│   └── fixtures/           # samples de logs reais (anonimizados)
└── README.md
```

## Próximos passos

1. Decidir linguagem e form factor v1 (ver acima)
2. Coletar amostras reais de logs do Silverblue do autor (com PII removido)
3. Definir taxonomia de eventos (categorias + níveis de interesse)
4. MVP: parser de **um único source** (audit ou fail2ban) → output texto
5. Iterar para adicionar mais sources e melhorar correlação
