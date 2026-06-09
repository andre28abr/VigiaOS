# Bem-vindo ao VigiaOS

## O que é isso?

O **VigiaOS** é **um programa só** que ajuda você a cuidar da
segurança do seu computador e dos dados dos seus clientes.

Foi pensado especialmente para **escritórios de advocacia** e outros
profissionais que precisam mostrar diligência no cuidado com dados
pessoais (LGPD).

## Por que usar?

Imagine que você guarda informações sensíveis dos seus clientes
(documentos, processos, dados pessoais). A lei (LGPD) obriga você a
**cuidar** desses dados — usar antivírus, ter senhas fortes, registrar
o que acontece no computador, fazer cópias de segurança.

O VigiaOS reúne **14 ferramentas** que cuidam disso pra você, **num
único lugar fácil de usar** — a seção **Hub**.

## Como funciona?

Você abre o **VigiaOS** (um ícone só no menu de aplicativos) e ele já
abre numa janela única. Do lado esquerdo tem uma barrinha que troca de
**seção**; em cada uma, você clica na ferramenta que quer e ela aparece
**dentro da mesma janela** — sem precisar abrir vários programas.

### A barra lateral troca de seção:

🏠 **Início** — o painel que mostra o computador funcionando agora
   (memória, processador, internet) em tempo real
🔲 **Hub** — todas as 14 ferramentas de segurança e privacidade
🔴 **Red** — ferramentas de teste de invasão (em construção)
🔵 **Blue** — detecção e resposta a ameaças (para quem é da área)

Lá no rodapé dessa barra ficam:

⚙️ **Configurações** — ajustes do VigiaOS (tema, senha, atualizações,
   e a **Ajuda** com este manual)
🔔 **Notificações** — o sininho que avisa quando há atualizações

### Facilidades do app

- 🔍 **Busca rápida (Ctrl+K)** — aperte **Ctrl+K** de qualquer lugar e
  digite o que procura (uma ferramenta, uma seção, uma configuração). Dá
  Enter e ele te leva lá. É o jeito mais rápido de navegar.
- 🎨 **Tema "Terminal"** — em **Configurações → Aparência**, dá pra trocar o
  visual *Padrão* (claro/escuro do GNOME) por um tema *Terminal* (fundo
  escuro com verde-neon, estilo "hacker"). Só visual, não muda o que as
  ferramentas fazem.
- 🔔 **Notificações de segurança** — em **Configurações → Aplicação**, o
  VigiaOS pode te avisar com uma **notificação do sistema** (aquele balão do
  GNOME) quando há atualizações pendentes. Clicar no aviso abre a tela certa.
- 🦠 **Varredura de vírus semanal** — também em **Configurações → Aplicação**,
  você pode ligar uma **checagem automática de vírus** que roda **1x por
  semana** nas suas pastas (sem precisar de senha de admin) e te avisa se
  achar algo. Vem **desligada** por padrão.

## O que cada ferramenta faz?

Vou agrupar por categoria pra ficar mais fácil:

### ✅ Visão geral

**Responde de relance: meu computador está seguro?**

- **Tudo Certo?** — Um **semáforo 🟢🟡🔴** que checa de uma vez as 4 coisas
  mais importantes (atualizações, firewall, antivírus, privacidade). Cada
  item fora do lugar tem um botão **Resolver** que te leva direto pra
  ferramenta certa. É a primeira parada recomendada.

### 👁️ Observação

**Sabe quem entrou e o que mexeu no seu computador.**

- **Dashboard** — Mostra como o computador está agora (memória,
  processador, internet)
- **Registro de Atividades** — Lista o que aconteceu (quem fez login,
  quem instalou programa, etc)
- **Monitor de Rede** — Mostra com qual site/serviço seu computador
  está conversando agora

### 🔐 Privacidade

**Decide o que sai do seu computador.**

- **Controles de Privacidade** — Liga/desliga rastreamento, localização,
  bluetooth, etc.
- **Gerenciador de DNS** — Esconde dos provedores quais sites você
  visita (usa DNS criptografado)

### 🛡️ Proteção

**Defende contra invasores e infecções.**

- **SELinux** — Sistema de proteção que isola programas perigosos
- **Firewall** — Bloqueia conexões indesejadas vindas da internet
- **Verificação de Hardening** — Faz um "check-up" do computador
- **Integridade de Arquivos** — Avisa se alguém mexeu nos arquivos
  importantes
- **Inspetor de Capabilities** — Mostra programas com poderes
  especiais (admin)
- **Antivírus** — Procura vírus nos arquivos (ClamAV)
- **Verificador de Rootkit** — Procura programas escondidos que
  espionam você

### ⚙️ Sistema

**Cuida da manutenção do computador.**

- **Atualizações** — Mantém o sistema e as ferramentas de segurança em
  dia (fica em Configurações → Atualizações)

### 📄 Relatórios

**Comprova o que você fez (importante pra LGPD).**

- **Relatórios** — Gera PDFs com tudo que aconteceu no seu sistema
  (pode usar como prova de auditoria)

## Como começar?

1. **Clique em "Hub"** no canto esquerdo (a seção com as ferramentas)
2. **Escolha uma ferramenta** na lista (recomendo começar pela seção
   **Início** — é só ver o computador funcionando, não muda nada)
3. **Explore** os botões e as abas dentro de cada ferramenta
4. Cada ferramenta tem uma aba **"Sobre"** explicando ela em detalhes

## Posso quebrar alguma coisa?

⚠️ **Sim, com algumas ferramentas.** Por isso elas pedem **senha de
administrador** quando você vai fazer mudanças importantes.

✅ **Mas você pode "ver" tudo sem mexer.** A seção **Início**, o Activity
Log, o Network Monitor, o Antivírus e a maioria das outras ferramentas têm
modo "só leitura" — você só observa.

## Quer começar com calma?

Se você é novo aqui, sugiro essa ordem:

1. **Início** — Ver o computador funcionando
2. **Registro de Atividades** — Ver o que acontece no sistema
3. **Controles de Privacidade** — Desligar coisas que você não quer
4. **Antivírus** — Rodar um scan de teste

Depois explore as outras conforme tiver interesse. Cada uma tem uma
explicação detalhada na aba **Ajuda** (dentro de Configurações): Manual
técnico ou Manual simples, como você está vendo agora.

## Onde guardo dúvidas?

- Vá em **Configurações → Ajuda** (no rodapé da barra esquerda)
- Cada ferramenta tem sua aba **Sobre** com explicação interna
- Acesse o repositório: **https://github.com/andre28abr/VigiaOS**

Tudo é **software livre**, código aberto, auditável. Apache 2.0.
