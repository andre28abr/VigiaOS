# Vigia Cracker — manual técnico

Módulo de **Senhas & Hashes** do **VigiaRed**. Auditoria **DEFENSIVA** de senhas:
dado um arquivo de hashes que o operador **já possui** (ex.: `/etc/shadow` do
próprio servidor), testa quais senhas caem num ataque de dicionário — para exigir
a troca das fracas. Wrapper de dois engines consagrados: **`john`** (CPU, sem
setup) e **`hashcat`** (GPU, mais rápido). Não serve para "descobrir senha dos
outros".

> **Pacote:** vigia-red 0.7.0 · **Status:** `pronto`. Padrão do ecossistema:
> *backend puro/testável + `page.py` via `Module.impl`*, atrás do portão de termo
> de uso (`gate.build_gated`). Usa o runner cancelável compartilhado
> `vigia_red.runner.ScanProcess`.

## Arquivos

```
tools/vigia-red/src/vigia_red/modules/cracker/
├── __init__.py     # mínimo (sem gi)
├── backend.py      # catálogo + validação + cmd + parser --show + relatórios (PURO)
└── page.py         # GUI: build_content() → abas Auditar/Histórico/Sobre

tests/red/test_cracker_backend.py   # 23 testes
```

## Dependência

- **`john`** (John the Ripper) **ou** **`hashcat`**. Registry `Dependency`
  (gerenciador `rpm`, pacote `john`): `john` roda em CPU sem setup; `hashcat` usa
  GPU (`sudo dnf install hashcat`). Detecção: `john_available()` /
  `hashcat_available()` = `shutil.which(...)`; `any_engine_available()` cobre os
  dois; `engine_available(engine)` escolhe.

## Backend (`backend.py`)

### Catálogo de tipos de hash (puro)

`HASH_TYPES: list[HashType]` cura os tipos mais comuns numa auditoria BR, cada um
mapeando o **`--format=` do john** e o **`-m` do hashcat**: `auto` (só john —
autodetecção), `md5`/`sha1`/`sha256`/`sha512` (cru), `ntlm` (Windows), `bcrypt`,
e os de `/etc/shadow` — `md5crypt` (`$1$`), `sha256crypt` (`$5$`), `sha512crypt`
(`$6$`, padrão no Linux atual). `find_hash_type(id)` resolve; `DEFAULT_HASH_TYPE
= "auto"`.

### Perfis e engines (puro)

- `PROFILES`: `dicionario` (wordlist como está) e `regras` (`use_rules=True` →
  `--rules` no john / `-r <best64.rule>` no hashcat). Default `dicionario`.
- `ENGINES = ("john", "hashcat")`, default `john`.

### Validação (puro)

- `validate_hashfile(path)` / `validate_wordlist(path)` — caminho não vazio +
  arquivo legível (`_is_readable_file`, tolera `OSError`).
- `count_hashes(path)` — nº de linhas não vazias (para o total/`weak_ratio`);
  nunca levanta.

### Montadores de comando (puro — argv em lista, nunca shell)

- `build_john_cmd(hashfile, wordlist, hash_type, use_rules)` →
  `john --wordlist=… [--format=…] [--rules] <hashfile>`.
- `build_john_show_cmd(hashfile, hash_type)` → `john --show [--format=…] <hashfile>`.
- `build_hashcat_cmd(hashfile, wordlist, hash_type, use_rules, rules_path)` →
  `hashcat -m <modo> -a 0 --quiet <hashfile> <wordlist> [-r <best64.rule>]`.
- `build_hashcat_show_cmd(hashfile, hash_type)` → `hashcat -m <modo> --show …`.

### Parsers (puro — nunca levantam)

- `parse_john_show(text)` → `list[Cracked]`: linhas `usuario:senha:…`; ignora a
  linha-resumo (`N password hashes cracked, M left`); senha = 2º campo.
- `parse_hashcat_show(text)` → `list[Cracked]`: linhas `hash:senha`, senha = tudo
  após o 1º `:`; `identifier` = hash truncado em 32 chars.

### Execução (toca o sistema)

`run_crack(hashfile, wordlist, *, engine, hash_type, profile_id, timeout=1800,
handle=None) -> CrackResult` — valida arquivos/engine/disponibilidade (e bloqueia
`hashcat + auto`, que não tem autodetecção), roda o ataque via `handle.run`
(cancelável) ou `proc.run`, e **em seguida roda `--show`** para ler o que caiu na
*pot file*. `john`/`hashcat` saem `!= 0` mesmo em sucesso (nada quebrado /
"exhausted"), então **quem manda é o `--show`**. Só marca `ran = False` quando a
saída acusa erro real ("unknown ciphertext format", "no hashes loaded", "no such
file", "separator unset"). `CrackResult` expõe `cracked_count` e `weak_ratio`.

## Runner cancelável

`vigia_red.runner.ScanProcess` roda via `subprocess.Popen`; `cancel()` encerra o
processo numa thread daemon sem congelar a GUI. Padrão do projeto: sem shell.

## Relatórios / permissões

- **`save_report`** → `~/.local/share/vigia-cracker/cracker-<ts>.json`, **0600**
  (via `save_json_0600`).
- **Minimização/LGPD**: `result_to_dict` **NÃO grava a senha em claro** — só
  `weak_identifiers` (os identificadores dos hashes fracos), `total_hashes` e
  `cracked_count`. A senha aparece apenas na tela e no export TXT.
- **`result_to_text(r)`** → laudo legível (percentual de senhas fracas + a lista
  "troque estas já"); `raw` (saída do `--show`) alimenta o **Exportar** e não vai
  no JSON.
- **`list_recent_reports(limit=20)`** → mais novos primeiro.
- **Central de Relatórios**: `events.record("cracker", …, category="scan",
  severity="high" se caiu alguma senha, senão "ok")`. Falha engolida.

## GUI (`page.py`)

`build_content()` = `gate.build_gated(_build_tool)` — o termo (`consent.py`,
Lei 12.737/2012) destrava a ferramenta. Segue o padrão dos módulos Red:
`ViewSwitcher` + `ViewStack` com abas **Auditar** (seletor de arquivo de hashes,
wordlist, tipo de hash, engine, perfil; iniciar vira **Cancelar**; **Exportar**),
**Histórico** e **Sobre** (Uso responsável + revogação do termo). Trabalho pesado
em `threading.Thread` → `GLib.idle_add`.

## Limitações

- Cobertura = a wordlist usada; "zero quebrado" ≠ "senhas fortes".
- `hashcat` não tem autodetecção — exige tipo explícito.
- `bcrypt`/`sha512crypt` são lentos por design; wordlists grandes podem estourar
  o `timeout` (1800 s).
- O material de entrada (hashes, wordlist) é sensível — responsabilidade do
  operador.

## Testes

`tests/red/test_cracker_backend.py` — **23 testes**: catálogo/`find_hash_type`,
`validate_hashfile`/`validate_wordlist`/`count_hashes`, `build_john_cmd` e
`build_hashcat_cmd` (formato, `--rules`/`-r`, modos), `parse_john_show` e
`parse_hashcat_show` (linha-resumo ignorada, senha com `:`) e relatórios (sem
senha em claro). Rodam headless (sem john/hashcat nem GTK).
