# VigiaOS — Auditoria de código — 2026-09-10

Resumo público da revisão completa feita sobre o código do VigiaOS antes do
próximo ciclo de funcionalidades. Substitui a auditoria anterior (2026-05-26),
que já não refletia o projeto (ferramentas removidas, suíte de testes muito
menor, arquivos que não existem mais).

## Método

- **Compilação** de todos os módulos Python (`py_compile`) e checagem estática
  com `pyflakes` — zero erros, zero nomes não usados/indefinidos.
- **Suíte completa** de testes (`pytest tests/`): ~1.360 testes coletados,
  todos passando (4 pulados fora do Linux, por ausência de GTK).
- **Resolução de imports por AST**: os 397 `import`/`from … import` do
  projeto foram resolvidos contra os pacotes instalados — nenhum módulo,
  função ou classe referenciada sem existir.
- **Revisão manual** de todos os backends (subprocess, arquivos, SQLite) e
  de todas as páginas GTK (workers, `GLib.idle_add`, markup Pango).

## O que foi verificado e está limpo

| Item | Resultado |
|---|---|
| `shell=True` | Nenhuma ocorrência; todo subprocess usa **argv em lista** |
| `sudo` | Nenhuma ocorrência; escalada só via **`pkexec`** (diálogo Polkit) |
| Alvos de rede (Recon/Scanner/Vuln/Web) | Validados por regex/whitelist antes de virar argumento; flag injection (`-iL`, `--script=`…) bloqueada |
| SQL (Central de Relatórios, SIEM) | 100 % **parametrizado**; nenhum f-string em query |
| Relatórios HTML (Reports, Central de Relatórios) | Jinja2 com **autoescape** ligado; selo SHA-256 |
| Backup/restauração (`.zip`) | Guarda contra **Zip-Slip** (caminhos absolutos e `..` rejeitados) |
| Chave de assinatura dos relatórios | Gerada localmente, `0600`, **nunca versionada** |
| Compatibilidade | Python **3.11+** (sem sintaxe/typing 3.12-only) |
| Arquivos de dados sensíveis | `0600` (config, relatórios, exportações, capturas, banco de eventos) |

## O que foi corrigido nesta auditoria

Dois commits, `39c34e2` (robustez) e `2350eb1` (LGPD + bugs):

- **Subprocess tolerante a bytes inválidos** — todos os `subprocess.run`/`Popen`
  com `text=True` passaram a usar `errors="replace"`; saída de ferramentas
  externas com bytes fora de UTF-8 não derruba mais a tela.
- **Fronteira de exceção nos workers** — threads de varredura capturam
  qualquer exceção e devolvem um erro amigável à interface, em vez de
  morrer em silêncio.
- **Escape de markup Pango** — texto vindo de ferramentas externas (nomes
  de hosts, caminhos, mensagens) é escapado antes de virar markup.
- **Exportações `0600`** — todos os arquivos exportados (TXT/XML/JSON/HTML)
  nascem só-leitura-do-dono.
- **Retenção LGPD 180 dias ativa** — a poda do banco de eventos, que existia
  mas não era chamada, agora roda a cada abertura.
- **Captura do IDS `0600`** — o script de captura criava `.pcap`/`eve.json`
  legíveis por todos (`0644`); agora o diretório nasce `0700` e os arquivos
  perdem permissão de grupo/outros.
- **`/tmp` limpo** — Timeline e IDS usavam `mkdtemp` e deixavam dados
  forenses em `/tmp` para sempre (em tmpfs, isso é RAM); passaram a
  `TemporaryDirectory`, removido ao fim da análise.
- **Cancelamento de processos `pkexec`** — processos elevados (root) não
  aceitavam `SIGTERM` do usuário (`EPERM`); o helper agora recorre a
  `pkexec kill -TERM`, o cancelamento roda em thread própria (não congela a
  interface) e operações longas do SELinux (`setsebool -P`) ganharam timeout
  realista.
- **`MAX_HOSTS` por faixa de octeto** — o Network Scanner limita o tamanho da
  faixa por octeto (não só pelo CIDR), evitando varreduras enormes por engano.
- **IPv6** — alvos IPv6 validados e passados com `-6` ao nmap.
- **Lynis `chown`** — o relatório em `/var/log/` era entregue a
  `root:<usuário>` assumindo que o grupo primário tem o nome do usuário (falha
  silenciosa em LDAP/AD); agora usa `id -gn`, e a validação do nome aceita
  maiúsculas e ponto.

## Pendências conhecidas

- **Empacotamento RPM (`packaging/`) é experimental** — specs defasadas em
  relação aos `pyproject.toml`, sem specs de `vigia-red`/`vigia-blue`, sem
  tags git. A instalação suportada é pelos scripts em `install/`.
- **Configurações/Ajuda da casca em modo standalone** — quando uma
  ferramenta roda sozinha (fora do VigiaOS), as abas de Configurações e Ajuda
  da casca não estão disponíveis; só o app completo as oferece.
- **3 módulos Red planejados** (wireless, exploit, cracker) ainda são
  esqueleto — aparecem com bolinha cinza "planejado".

## Como repetir

```bash
python3 -m pyflakes tools/*/src
python3 -m pytest tests -q
```

Próximos focos sugeridos: ciclo de vida de widgets GTK (referências após
`destroy`), caching de autorização Polkit (`auth_admin_keep`) e metadados
AppStream para integração com o GNOME Software.
