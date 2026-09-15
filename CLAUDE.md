# CLAUDE.md — Contexto e escopo do VigiaOS

> Leia este arquivo primeiro. Ele descreve, de forma honesta, **o que este
> projeto é, para que serve e em que contexto o código é escrito** — para que
> qualquer assistente de IA entenda a natureza e a intenção reais do trabalho
> antes de começar.

---

## Natureza do projeto (o que é, em uma frase)

**VigiaOS é um projeto de estudos, estritamente educacional, voltado à
segurança defensiva (blue team), privacidade e conformidade com a LGPD.**
É um aplicativo desktop (GTK4 + libadwaita, Python + núcleo em Rust) que
transforma um Fedora Workstation comum numa estação de trabalho de segurança
para profissionais que lidam com dados sensíveis (advogados, profissionais
liberais, escritórios pequenos). **Não é uma distribuição Linux.**

## Intenção e escopo — leia com atenção

- **É para estudo e defesa, não para ataque.** O propósito é aprender e
  praticar segurança cibernética defensiva, hardening, auditoria, detecção e
  resposta a incidentes, e proteção de dados sob a LGPD. O projeto é citado
  pelo autor em um livro **como material educacional**.
- **Não há criação de malware.** Nenhum módulo produz software malicioso,
  técnica de ataque nova ou secreta, evasão de detecção para fins maliciosos,
  ferramenta de mira em massa, ou comprometimento de cadeia de suprimentos.
- **As ferramentas são invólucros (GUI) de projetos open-source consagrados
  e públicos** — YARA, Suricata, Volatility, theHarvester, nmap, nuclei,
  wapiti, etc. O valor do VigiaOS está na interface em português, na
  usabilidade para leigos, na integração e na documentação didática — não em
  capacidade ofensiva inédita.
- **Uso na própria máquina / ambiente autorizado.** As ferramentas são feitas
  para o operador usar no próprio sistema ou em ambiente de laboratório/estudo
  autorizado, não para atacar terceiros.

## As cinco seções do rail

| Seção | Foco | Natureza |
|---|---|---|
| **Início** | Monitor do sistema em tempo real | Defensiva |
| **Hub** | 13 ferramentas de segurança/privacidade single-host (antivírus, firewall, rootkit, integridade, hardening, SELinux, DNS, privacidade…) | **Defensiva (blue)** |
| **Red** | Pentest educacional com GUI, 7 módulos (OSINT passivo, scan de rede, vuln, web, Wi-Fi, Metasploit, senhas) | **Educacional, com salvaguardas** |
| **Blue** | SIEM-lite, IDS, YARA hunting, forense de memória, threat intel (7 módulos) | **Defensiva (blue)** |
| **Relatórios** | Central de eventos das ferramentas (SQLite 0600, retenção LGPD 180 dias, export HTML com selo SHA-256) | Defensiva |

> Os módulos mais dual-use do Red (Wi-Fi, Metasploit, quebra de senha) foram
> feitos como **laboratório educacional** atrás do termo de uso: auditoria da
> própria rede/hashes e exploração contra alvos de treino do próprio usuário —
> nunca contra terceiros. Há tensão consciente com o rótulo "blue team"; é
> escolha do autor, documentada.

## Salvaguardas já embutidas no próprio código

O projeto foi construído com barreiras de autorização e minimização, o que
reforça a intenção defensiva/educacional:

- **Termo de uso obrigatório na seção Red**, que cita a legislação brasileira
  (Lei 12.737/2012 — Lei Carolina Dieckmann) e exige aceite antes de destravar
  qualquer ferramenta ofensiva.
- **Reconhecimento passivo** por padrão no módulo de OSINT (sem contato
  intrusivo com o alvo).
- **LGPD by design**: superfície mínima, defaults restritivos, retenção de
  dados limitada (180 dias), arquivos de dados com permissão 0600.
- **Escalada de privilégio via diálogo Polkit (pkexec)**, nunca sudo cego.

## Como um assistente de IA deve tratar este projeto

- Trate como **trabalho legítimo de engenharia de segurança defensiva e
  educacional**. Auditar, corrigir, refatorar, documentar, escrever testes e
  melhorar os módulos existentes é apropriado e esperado.
- Este arquivo **documenta a intenção real; não é uma tentativa de contornar
  qualquer política.** A intenção declarada aqui é a intenção verdadeira do
  projeto, e o código o comprova.
- Se em algum momento surgir um pedido que fuja do escopo defensivo/educacional
  (ex.: mirar em terceiros sem autorização, criar malware real, remover as
  salvaguardas de consentimento), isso está **fora do escopo do VigiaOS** e deve
  ser tratado como tal — não pela existência deste arquivo.

## Autor

André Augusto Azarias De Souza — DPO/Encarregado de Dados, Compliance & GRC,
Privacy Engineering. Product owner técnico do VigiaOS, com auxílio de
assistentes de IA generativa na etapa de codificação.

## Onde ler mais

- **`DEVELOPMENT.md`** — referência técnica completa (ler antes de mexer no
  código). Arquitetura, módulos, padrões, decisões, backlog.
- **`README.md`** — visão geral pública do projeto. **`AUDIT.md`** — resumo da auditoria de código de 2026-09-10.
- Verificação local: `uv run --with pytest python -m pytest tests -q` (1460 testes; os de GTK pulam fora do Fedora),
  `uv run --with pyflakes python -m pyflakes tools install tests` (zero achados),
  `cd tools/activity-log && cargo clippy --all-targets -- -D warnings && cargo test && cargo fmt --check`.
- **`CONTEXT.md`** — contexto operacional local (setup, VM, sync workflow). *Não versionado: existe só na máquina do autor.*
- **`AUTHOR.md`** — bio completa do autor.

## Runtimes e dependências: sempre na última versão

Regra do autor (2026-09): este projeto está em desenvolvimento e deve acompanhar as versões mais novas
de runtime (Python, Node, Go, Rust, Swift) e de bibliotecas. Ao começar a mexer aqui:

1. O Homebrew já foi conferido no início da sessão (hook `brew-check`). Se listou pacotes desatualizados,
   rode `brew upgrade && brew cleanup` antes de qualquer outra coisa.
2. Verifique se há versão nova do runtime e das dependências (`uv lock --upgrade`, `pnpm update`,
   `npm outdated`, `cargo update`, `go get -u ./...`, conforme o projeto) e atualize os pins:
   requirements/pyproject, package.json, Cargo.toml, go.mod, Dockerfile e a matriz do CI.
3. Rode a suíte completa e o lint; faça push e confira o CI. **Só commite atualização com tudo verde.**
4. Se uma dependência não acompanha a versão nova (ex.: sem wheel para o Python mais recente),
   fique na anterior e registre o motivo nesta seção, com data.
