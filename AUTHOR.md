# Sobre o autor

## André Augusto Azarias de Souza

→ [LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza) · [GitHub](https://github.com/andre28abr) · contato@azariasdesouza.com

---

## Quem é

Gestor com **18 anos de atuação como Gerente Administrativo e Encarregado de Dados (DPO)** em organização do setor de saúde suplementar, ambiente regulado pela ANS e pela LGPD. Participou de decisões de diretoria, conduziu a relação com hospitais e operadoras, liderou a modernização dos sistemas administrativos e de segurança da informação e coordenou o programa de adequação à LGPD da organização, com dados sensíveis de saúde sob o Art. 11.

Formado em **Direito** e em **Análise e Desenvolvimento de Sistemas**, com pós-graduações em segurança digital, governança de dados, privacidade, direito digital e liderança ágil.

Atua na interseção entre **Compliance, GRC, privacidade e segurança da informação**: mapeamento de dados e ROPA (Art. 37), RIPD/DPIA (Art. 38), direitos do titular (Art. 18), gestão de operadores e terceiros (Art. 39), resposta a incidentes (Art. 48), interface com a ANPD, e os frameworks NIST CSF, CIS Controls e ISO/IEC 27001/27701. Trabalha com o princípio de que proteção de dados é também arquitetura: Security by Design, Zero Trust, defesa em camadas e menor privilégio.

Desde 2025 conduz, como **product owner técnico**, projetos open-source de segurança e privacidade em Python, Go, Rust e Swift, com a codificação orquestrada por assistentes de IA generativa sob sua direção e revisão. Desenvolve **automações de processos com n8n** e é autor de cinco livros publicados, entre eles *Da Norma à Liderança*, sobre atualização profissional em GRC.

---

## Automação de processos com n8n

Projeta e opera **automações de processos de negócio e jurídicos em n8n**, self-hosted em Docker Compose, com foco em privacidade: processamento local, gravação em disco restrita a pastas definidas, sem envio de dados a serviços de terceiros. Entre o que já construiu:

- **Triagem automática de publicações judiciais**: busca de hora em hora no DJEN (Comunica CNJ) por OAB, classificação por urgência, cálculo de prazo provisório em dias úteis, contexto do processo via DataJud e painel web de tratamento por advogado.
- **Onboarding de clientes**: formulário web que gera em segundos procuração, declaração de hipossuficiência e contrato de honorários em PDF (Gotenberg), com registro do cliente para os fluxos seguintes.
- **Portal e páginas servidas pelo próprio n8n** via webhooks, instaladores para Mac e Windows, variante para servidor com HTTPS automático e autenticação (Caddy) e rotina de backup.
- **Integrações com APIs públicas** (DJEN, DataJud, BrasilAPI) e desenho de fluxos com Code nodes, banco JSON local e controle de estado entre execuções.

---

## Por que esse projeto existe

O **VigiaOS** nasceu como exercício pessoal de portfólio com três objetivos:

1. **Levar segurança e LGPD para o profissional final, não só pro servidor.** Enquanto o [SentinelBR](https://github.com/andre28abr/SentinelBR-platform) cuida da infraestrutura (SIEM multi-host), o VigiaOS cuida da **estação de trabalho** do advogado, do profissional liberal, do escritório pequeno, onde dados sensíveis de clientes vivem no dia a dia. Hardening, antivírus, integridade de arquivos, controles de privacidade e relatórios de conformidade, tudo em português e com interface gráfica moderna.

2. **Traduzir exigências regulatórias em decisões de produto concretas.** *Minimum surface area* (nada de serviço ligado por padrão), `chmod 0600` em todo relatório sensível, escalonamento de privilégio via Polkit (nunca `sudo` com input do usuário), selo de integridade SHA-256 nos relatórios, cada escolha técnica reflete um princípio de LGPD/auditabilidade, não um detalhe de implementação.

3. **Exercitar orquestração de projeto técnico complexo com auxílio de IA generativa.** A skill emergente do mercado pós-2024 não é "decorar sintaxe", é saber **definir requisitos, validar arquitetura, traduzir necessidades de negócio em especificações técnicas** e usar IA pra acelerar a entrega. O VigiaOS reúne 14 ferramentas GTK4 na seção **Hub**, mais as seções Início/Red/Blue numa janela só, com mais de 1.140 testes verdes, gerenciado nesse modelo.

---

## Atuação neste projeto

**Papel:** Product Owner técnico, com auxílio de assistentes de IA generativa para a etapa de codificação.

**Entregas pessoais (sem auxílio de IA):**
- Definição de **requisitos, escopo e roadmap** das 14 ferramentas + do ecossistema Vigia: **VigiaOS** (app unificado: seções Início/Hub/Red/Blue) + **VigiaOps** (multi-host via SSH, produto separado no roadmap)
- **Validação da arquitetura**: app único com rail de seções e ferramentas em modo *embedded* (master-detail), Red/Blue entrando pelo mesmo master-detail via adaptador `Module → ToolEntry`, biblioteca compartilhada `vigia-common`, modelo de privilégio via `pkexec` (argv-list, sem shell), core do Activity Log em Rust + frontends GTK4
- **Tradução de exigências LGPD** para requisitos funcionais: *minimum surface area*, permissões `0600`/`0700`, selo de integridade nos relatórios, pacote de auditoria assinado
- **Decisão de plataforma**: entregar uma suíte de ferramentas sobre o **Fedora Workstation** vanilla (não uma distro), priorizando baixo custo de manutenção e cobertura completa de forense
- **Curadoria de conteúdo em PT-BR**: manuais leigos e técnicos renderizados in-app, descrições do catálogo, glossário de capabilities do kernel
- **Review e decisões de trade-off** em cada fase (HTML+impressão do navegador vs. WeasyPrint nos relatórios; gráficos SVG server-side vs. JS/CDN; remoção do trilho Tor de sistema em favor do Tor Browser)

**Etapa de codificação:** orquestrada com auxílio de IA generativa, sob direção e revisão do autor. A stack do projeto (Python/GTK4/libadwaita, Rust, Jinja2) foi escolhida pela aderência ao caso de uso (desktop Linux moderno, LGPD, escritório), não por domínio prático prévio em escrita de código de produção.

---

## Outros projetos

**[SentinelBR](https://github.com/andre28abr/SentinelBR-platform)** ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) ![Go](https://img.shields.io/badge/-Go-00ADD8?logo=go&logoColor=white) ![React](https://img.shields.io/badge/-React-20232A?logo=react&logoColor=61DAFB)<br>
Plataforma open-source de **SIEM + LGPD** para PMEs brasileiras. Agente Go com gRPC e mTLS, detecção em tempo real, resposta automatizada e compliance LGPD nativa, multi-tenant. 225 testes entre servidor, agente e frontend; CI em 16 jobs.

**[Plataforma LGPD](https://github.com/andre28abr/lgpd-platform)** ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/-Flask-000000?logo=flask&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?logo=postgresql&logoColor=white)<br>
Plataforma web multi-tenant que **treina, avalia e certifica** os setores de uma empresa em LGPD e dá ao DPO as ferramentas de operação: ROPA, RIPD, direitos do titular e incidentes. 121 testes, 95% de cobertura.

**[Peapod](https://github.com/andre28abr/Peapod)** ![Go](https://img.shields.io/badge/-Go-00ADD8?logo=go&logoColor=white) ![Swift](https://img.shields.io/badge/-Swift-F05138?logo=swift&logoColor=white) ![Docker](https://img.shields.io/badge/-Docker-2496ED?logo=docker&logoColor=white)<br>
Sandboxes **isolados e descartáveis para agentes de IA**, dirigidos por MCP, CLI, dashboard web e app nativo de macOS: rede desligada por padrão, allowlist de domínios, trilha de auditoria. Go e Swift, distribuído por Homebrew.

**[Uptend](https://github.com/andre28abr/Uptend)** ![Swift 6](https://img.shields.io/badge/-Swift%206-F05138?logo=swift&logoColor=white) ![macOS](https://img.shields.io/badge/-macOS-000000?logo=apple&logoColor=white)<br>
App nativo de macOS para **configurar e manter o Mac** e **auditar servidores Linux**: coletor portátil, relatórios, correlação com CVEs, MITRE ATT&CK, lente LGPD e playbook de hardening com rollback. Swift 6, 428 testes.

**[banana](https://github.com/andre28abr/banana-releases)** ![Rust](https://img.shields.io/badge/-Rust-000000?logo=rust&logoColor=white) ![Tauri 2](https://img.shields.io/badge/-Tauri%202-24C8D8?logo=tauri&logoColor=white) ![Svelte 5](https://img.shields.io/badge/-Svelte%205-FF3E00?logo=svelte&logoColor=white)<br>
Editor **local-first** de notas Markdown, código e PDF, com vault cifrado (Argon2id + AES-256-GCM). Tauri 2, Rust e Svelte 5, 393 testes.

**SC Platform** *(privado, disponível para apresentação mediante solicitação)* ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/-Flask-000000?logo=flask&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/-PostgreSQL-4169E1?logo=postgresql&logoColor=white)<br>
SaaS multi-tenant para gestão de licitações públicas, com PNCP em tempo real, simulador da Lei 14.133/2021, robô de lances em três modos, extração de PDF com IA local, CRM e Telegram. Cerca de 75 mil linhas e 547 testes.

**AUGRAZ** *(privado, produto da empresa do autor)* ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/-Flask-000000?logo=flask&logoColor=white)<br>
Plataforma de compliance **LGPD + ISO 27001** para assessoria de proteção de dados: 11 módulos por empresa-cliente (ROPA, canal do titular, incidentes, comunicações com a ANPD, fornecedores, treinamentos), biblioteca dos 93 controles do Anexo A da ISO/IEC 27001:2022 com Gap Analysis, relatórios imprimíveis e geradores de política de privacidade, aviso de cookies e termos de uso. Flask, testes em SQLite e PostgreSQL, CI com lint e auditoria de dependências.

**Site AUGRAZ** *(privado, protótipo ainda não publicado)* ![HTML5](https://img.shields.io/badge/-HTML5-E34F26?logo=html5&logoColor=white) ![PHP](https://img.shields.io/badge/-PHP-777BB4?logo=php&logoColor=white)<br>
Site institucional em HTML e PHP com formulário de contato em PDO e prepared statements, credenciais fora do repositório e `.htaccess` com HTTPS forçado, bloqueio de arquivos sensíveis e cabeçalhos de segurança (HSTS, nosniff, X-Frame-Options, Referrer-Policy, Permissions-Policy).

---

→ **[LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza)** · [GitHub](https://github.com/andre28abr)
