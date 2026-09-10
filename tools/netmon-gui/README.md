# Vigia Network Monitor

> Monitor visual de conexões TCP/UDP em tempo real. Wrapper GTK4 sobre `ss`.

## Estado

🟢 **v0.2.0** — três abas (`Conexões`, `Escutando`, `Sobre`) com auto-refresh:

### Conexões
- **Todas** as conexões TCP+UDP em qualquer estado, **agrupadas por aplicativo**
  (uma linha expansível por processo, com o número de conexões)
- **IP → nome** (DNS reverso, assíncrono em background) e **estados em
  português** (`ESTAB` → "conectado", `TIME-WAIT` → "encerrando"…)
- **Auto-refresh** a cada 3 s (toggle ON/OFF + botão "Atualizar")
- **Busca** por processo, IP, porta ou estado

### Escutando
- Só o que **aceita conexões** neste host: sockets `LISTEN` (TCP) e `UNCONN`
  com peer wildcard (UDP)
- **Glossário de portas** — explica em português o que costuma rodar em
  cada porta (22, 53, 631, 5432…)

### Modo admin (opt-in)
Sem privilégio, `ss -tunap` **não mostra o processo** de sockets de outros
usuários (aparece `(processo restrito)`). O switch **Admin** no cabeçalho
roda a coleta via `pkexec` (diálogo Polkit) e revela `NetworkManager`,
`systemd-resolve`, `cupsd`… Nunca use `sudo vigia-netmon`.

## Setup

Normalmente embarcado no **VigiaOS** (seção Hub). Sozinho:

```bash
cd ~/dev/VigiaOS/tools/netmon-gui
pip install --user -e .
vigia-netmon
```

## Limitações

- **Sem estatísticas de banda** — para banda por processo use o Monitor do
  Sistema (seção Início, aba Rede)
- **Sem inspeção de pacotes** — só estatísticas de sockets (para isso, o
  IDS na seção Blue)
- **Sem histórico** — a vista é instantânea (cada refresh substitui)

## Stack

- Python 3.11+ + PyGObject + GTK4 + libadwaita
- Backend: parser de `ss -tunap` (argv em lista, sem shell)
- Sem deps externas pip (PyGObject vem do RPM `python3-gobject`)
