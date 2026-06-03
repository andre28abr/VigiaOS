# Instalador de Ferramentas

## Pra que serve

É uma **loja de aplicativos de segurança** que você abre quando precisa
adicionar mais ferramentas ao seu computador.

Ao invés de você ter que pesquisar "qual antivírus pra Linux?", "como
instala o lynis?", "onde acho o uBlock Origin?", o Vigia já te entrega
uma lista **curada e segura** — são 13 ferramentas selecionadas + 8
extensões de navegador.

Tudo com 1 clique.

## Quando você usa isso

- **Logo depois de instalar o Vigia**: você passeia pelo catálogo e
  instala o que faz sentido pra você.
- **Quando outra ferramenta do Vigia avisa**: "Você precisa instalar
  AIDE pra usar a Integridade de Arquivos" -> você vem aqui e instala.
- **Quando você quer melhorar privacidade do navegador**: a aba
  Extensões lista as melhores opções gratuitas.
- **Quando você vai investigar uma máquina comprometida**: instala
  ClamAV (antivírus) e hashdeep (hash de evidências).
- **De vez em quando, pra manter tudo em dia**: a aba **Atualizações**
  verifica sozinha se há novidades de segurança e deixa você atualizar
  o sistema com 1 clique (ou pelo terminal, se preferir).

## O que você vai ver

A janela tem **4 abas**:

**Catálogo**: lista de ferramentas agrupadas em 5 categorias:
- **Auditoria e hardening** (lynis, AIDE, chkrootkit, rkhunter)
- **Rede** (mtr, nethogs)
- **Monitoramento** (lsof, strace, fail2ban)
- **Privacidade** (VPN OpenVPN, dnscrypt-proxy)
- **Forense** (clamav, hashdeep)

Cada item tem um botão "Instalar" (ou "Remover" se já tiver). Tem busca
no topo pra filtrar.

**Atualizações**: o lugar de **manter o sistema em dia**. Quando você
abre, ele **já verifica sozinho** se há atualizações e te avisa ali
mesmo. Você escolhe como atualizar:
- pelo **painel do Vigia** (botão "Atualizar agora"), ou
- copiando o **comando pro terminal** do sistema (`sudo dnf upgrade`).

A atualização é aplicada **na hora**, sem precisar reiniciar.

A lista embaixo separa o que será atualizado em duas partes: **Sistema**
(pacotes do sistema operacional) e **Programas da suíte Vigia** (as suas
ferramentas de segurança, tipo lynis e ClamAV). Assim você sabe exatamente
o que muda — só o sistema, ou o sistema e os programas junto.

**Extensões**: detecta os navegadores que você tem (Firefox, Chrome,
Brave, etc.) e mostra as **8 extensões recomendadas** pra cada um. Você
clica em "Abrir no Firefox" e o navegador abre na página da extensão —
basta clicar em "Adicionar".

**Sobre**: explicação da ferramenta.

## O que cada parte faz

### A instalação é na hora

No Fedora Workstation (sistema do Vigia) os pacotes são **instalados na
hora**, sem reiniciar. Você clica em "Instalar", digita a senha, e em
alguns instantes a ferramenta já está pronta pra usar.

### Extensões recomendadas (resumo rápido)

- **uBlock Origin**: bloqueia anúncios e rastreadores. O melhor do
  mundo. Instala em todo navegador.
- **Privacy Badger**: anti-rastreamento da Electronic Frontier
  Foundation. Complementa o uBlock.
- **ClearURLs**: limpa aqueles `?utm_source=...` chatos das URLs.
- **LibRedirect**: redireciona YouTube/Twitter pra alternativas
  privadas (só Firefox).
- **Cookie AutoDelete**: apaga cookies de sites que você não usa.
- **Decentraleyes**: faz cache local das bibliotecas que sites usam
  (Google Fonts, jQuery) — Google não sabe mais quais sites você visita.

## Posso quebrar alguma coisa?

**Instalar**: nada quebra. Se não gostar, você remove e fica como antes.

**Remover**: também não quebra. Mas alguns programas, se já estiverem
em uso, podem precisar de configuração manual pra parar de rodar
direito.

**Cuidado**: você precisa **digitar a senha de administrador** pra
instalar/remover. Use isso com calma — não saia clicando em coisas
aleatórias do catálogo.

**Bom saber**: o catálogo só tem ferramentas **conhecidas, auditáveis
e mantidas**. Não tem nada suspeito. As extensões são todas FOSS
(software livre).

## Dica do dia

**Receita pro primeiro dia de Vigia**:

1. Catálogo -> Instalar **lynis** + **aide** + **chkrootkit** +
   **rkhunter** (auditoria de segurança completa).
2. Catálogo -> Instalar **fail2ban** (bloqueia automaticamente IPs que
   tentam invadir).
3. **Atualizações** -> Atualizar agora (deixa o sistema em dia).
4. Abra a ferramenta de **Integridade de Arquivos** e crie o baseline.
5. Volte aqui na aba **Extensões**, abra seu navegador favorito,
   instale **uBlock Origin** + **Privacy Badger** + **ClearURLs**.

Pronto. Sistema decentemente blindado em 30 minutos.
