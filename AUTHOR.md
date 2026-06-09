# Sobre o autor

## André Augusto Azarias De Souza

→ [LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza) · [GitHub](https://github.com/andre28abr) · [Profile completo](https://github.com/andre28abr)

---

## Resumo

Profissional com mais de 18 anos de experiência em **gestão administrativa, compliance, governança da informação e proteção de dados pessoais**, com atuação integrada entre áreas administrativas, tecnologia da informação e conformidade regulatória.

Formação dupla em **Direito (Anhanguera)** e **Análise e Desenvolvimento de Sistemas (Mackenzie)**, complementada por especializações em LGPD, Direito Digital, Segurança Digital e Liderança Ágil.

Exerceu por quase duas décadas a função de **Gerente Administrativo e Encarregado de Dados (DPO)** em organização do setor de saúde suplementar, com atuação na organização da governança, adequação à LGPD, controle documental e apoio às áreas administrativas e tecnológicas.

Atualmente em transição de carreira, com **disponibilidade imediata**, busca posições em DPO (Encarregado de Dados), Compliance, Governança & GRC, Privacy Engineering ou Security Analyst com viés regulatório.

---

## Por que esse projeto existe

O **VigiaOS** nasceu como exercício pessoal de portfólio com três objetivos:

1. **Levar segurança e LGPD para o profissional final, não só pro servidor.** Enquanto o [SentinelBR](https://github.com/andre28abr/SentinelBR-platform) cuida da infraestrutura (SIEM multi-host), o VigiaOS cuida da **estação de trabalho** do advogado, do profissional liberal, do escritório pequeno — onde dados sensíveis de clientes vivem no dia a dia. Hardening, antivírus, integridade de arquivos, controles de privacidade e relatórios de conformidade, tudo em português e com interface gráfica moderna.

2. **Traduzir exigências regulatórias em decisões de produto concretas.** *Minimum surface area* (nada de serviço ligado por padrão), `chmod 0600` em todo relatório sensível, escalonamento de privilégio via Polkit (nunca `sudo` com input do usuário), selo de integridade SHA-256 nos relatórios — cada escolha técnica reflete um princípio de LGPD/auditabilidade, não um detalhe de implementação.

3. **Exercitar orquestração de projeto técnico complexo com auxílio de IA generativa.** A skill emergente do mercado pós-2024 não é "decorar sintaxe" — é saber **definir requisitos, validar arquitetura, traduzir necessidades de negócio em especificações técnicas** e usar IA pra acelerar a entrega. O VigiaOS reúne mais de uma dúzia de ferramentas GTK4 na seção **Hub**, mais as seções Início/Red/Blue numa janela só, com mais de 1.130 testes verdes, gerenciado nesse modelo.

---

## Atuação neste projeto

**Papel:** Product Owner técnico, com auxílio de assistentes de IA generativa para a etapa de codificação.

**Entregas pessoais (sem auxílio de IA):**
- Definição de **requisitos, escopo e roadmap** das ferramentas + do ecossistema Vigia: **VigiaOS** (app unificado: seções Início/Hub/Red/Blue) + **VigiaOps** (multi-host via SSH, produto separado no roadmap)
- **Validação da arquitetura**: app único com rail de seções e ferramentas em modo *embedded* (master-detail), Red/Blue entrando pelo mesmo master-detail via adaptador `Module → ToolEntry`, biblioteca compartilhada `vigia-common`, modelo de privilégio via `pkexec` (argv-list, sem shell), core do Activity Log em Rust + frontends GTK4
- **Tradução de exigências LGPD** para requisitos funcionais: *minimum surface area*, permissões `0600`/`0700`, selo de integridade nos relatórios, pacote de auditoria assinado
- **Decisão de plataforma**: entregar uma suíte de ferramentas sobre o **Fedora Workstation** vanilla (não uma distro), priorizando baixo custo de manutenção e cobertura completa de forense
- **Curadoria de conteúdo em PT-BR**: manuais leigos e técnicos renderizados in-app, descrições do catálogo, glossário de capabilities do kernel
- **Review e decisões de trade-off** em cada fase (HTML+impressão do navegador vs. WeasyPrint nos relatórios; gráficos SVG server-side vs. JS/CDN; remoção do trilho Tor de sistema em favor do Tor Browser)

**Etapa de codificação:** orquestrada com auxílio de IA generativa, sob direção e revisão do autor. A stack do projeto (Python/GTK4/libadwaita, Rust, Jinja2) foi escolhida pela aderência ao caso de uso (desktop Linux moderno, LGPD, escritório), não por domínio prático prévio em escrita de código de produção.

---

## Formação relevante para o domínio

### Formação acadêmica

- **Bacharelado em Direito** — Anhanguera Educacional
- **Análise e Desenvolvimento de Sistemas** — Universidade Presbiteriana Mackenzie

### Pós-graduações ligadas a Privacy / Security / Tech

- **Privacidade e Proteção de Dados Pessoais (LGPD)** — Faculdade Focus
- **Direito, Inovação e Tecnologia** — Faculdade CERS
- **Direito Digital** — Legale Educacional
- **Segurança Digital, Governança e Gestão de Dados** — PUCRS

### Certificações ligadas ao tema deste projeto

- **DPO – Data Protection Officer (LGPD)** — CERS (2020)
- **Cybersecurity Essentials** — Cisco (2022)
- **Cibersegurança – Ameaças e Táticas de Prevenção** — FGV (2023)
- **Crise Cibernética e Continuidade de Negócios** — FGV (2023)
- **Fundamentos na Lei Geral de Proteção de Dados** — Certiprof Summit (2023)
- **Data Mapping: da Teoria à Prática** — IbiJus (2023)
- **AI for Leaders** — StartSe University (2024)
- **Visual Law** — Legale Educacional (2023)

---

## Outros projetos

**[SentinelBR](https://github.com/andre28abr/SentinelBR-platform)** — Plataforma open-source de **SIEM + LGPD** para PMEs brasileiras. Coleta logs e inventário de servidores Linux via agente Go (gRPC mTLS), detecção em tempo real (regras Sigma-style + YARA + OSV.dev), resposta automatizada (SOAR-lite) e compliance LGPD nativa, multi-tenant. Stack: Python 3.12 / FastAPI / Go 1.25 / React 19 / PostgreSQL / Loki. ~19.5k LOC, 149 testes server.

**SC Platform** *(privado, sob NDA — disponível para apresentação em entrevistas mediante solicitação)* — Plataforma SaaS multi-tenant pra gestão de licitações públicas brasileiras (PNCP em tempo real, simulador FSM da Lei 14.133, robô de lances, extração de PDF com IA local, CRM, Telegram). 75k+ linhas, 420 testes. Stack: Python 3.14 + Flask 3 + SQLAlchemy 2 + PostgreSQL 15 + Redis + Playwright + ReportLab + Docling + ChromaDB.

---

→ **[LinkedIn](https://linkedin.com/in/andreaugusto-azariasdesouza)** · [GitHub](https://github.com/andre28abr)
