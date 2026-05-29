# Instalador de Ferramentas

## Pra que serve

E' uma **loja de aplicativos de seguranca** que voce abre quando precisa
adicionar mais ferramentas ao seu computador.

Ao inves de voce ter que pesquisar "qual antivirus pra Linux?", "como
instala o lynis?", "onde acho o uBlock Origin?", o Vigia ja te entrega
uma lista **curada e segura** — sao 16 ferramentas selecionadas + 8
extensoes de navegador.

Tudo com 1 clique.

## Quando voce usa isso

- **Logo depois de instalar o Vigia**: voce passeia pelo catalogo e
  instala o que faz sentido pra voce.
- **Quando outra ferramenta do Vigia avisa**: "Voce precisa instalar
  AIDE pra usar a Integridade de Arquivos" -> voce vem aqui e instala.
- **Quando voce quer melhorar privacidade do navegador**: a aba
  Extensoes lista as melhores opcoes gratuitas.
- **Quando voce vai investigar uma maquina comprometida**: instala
  ClamAV (antivirus) e hashdeep (hash de evidencias).

## O que voce vai ver

A janela tem **4 abas**:

**Catalogo**: lista de ferramentas agrupadas em 5 categorias:
- **Auditoria e hardening** (lynis, AIDE, chkrootkit, rkhunter)
- **Rede** (mtr, nethogs, iftop)
- **Monitoramento** (lsof, strace, fail2ban)
- **Privacidade** (tor, torsocks, wireguard, dnscrypt-proxy)
- **Forense** (clamav, hashdeep)

Cada item tem um botao "Instalar" (ou "Remover" se ja tiver). Tem busca
no topo pra filtrar.

**Pendentes**: depois de instalar algo, aparece aqui dizendo "Tal coisa
vai ser instalada no proximo boot". Tem um botao "Reiniciar agora" pra
aplicar.

**Extensoes**: detecta os navegadores que voce tem (Firefox, Chrome,
Brave, etc.) e mostra as **8 extensoes recomendadas** pra cada um. Voce
clica em "Abrir no Firefox" e o navegador abre na pagina da extensao —
basta clicar em "Adicionar".

**Sobre**: explicacao da ferramenta.

## O que cada parte faz

### Por que precisa reiniciar?

O Fedora Silverblue (sistema do Vigia) e' **atomico** — pacotes nao sao
"instalados na hora". Eles ficam em **camadas** que so tomam efeito
depois de reiniciar. E' menos pratico que o jeito tradicional, mas
**muito mais seguro**: se algo der errado, voce volta atras com 1
clique.

A boa estrategia: **instala varios de uma vez, depois reinicia 1 vez
so**.

### Extensoes recomendadas (resumo rapido)

- **uBlock Origin**: bloqueia anuncios e rastreadores. O melhor do
  mundo. Instala em todo navegador.
- **Privacy Badger**: anti-rastreamento da Electronic Frontier
  Foundation. Complementa o uBlock.
- **ClearURLs**: limpa aqueles `?utm_source=...` chatos das URLs.
- **LibRedirect**: redireciona YouTube/Twitter pra alternativas
  privadas (so Firefox).
- **Cookie AutoDelete**: apaga cookies de sites que voce nao usa.
- **Decentraleyes**: faz cache local das bibliotecas que sites usam
  (Google Fonts, jQuery) — Google nao sabe mais quais sites voce visita.

## Posso quebrar alguma coisa?

**Instalar**: nada quebra. Cada instalacao vira uma camada nova. Se nao
gostar, voce remove e fica como antes.

**Remover**: tambem nao quebra. Mas alguns programas, se ja estiverem
em uso, podem precisar de configuracao manual pra parar de rodar
direito.

**Cuidado**: voce precisa **digitar a senha de administrador** pra
instalar/remover. Use isso com calma — nao saia clicando em coisas
aleatorias do catalogo.

**Bom saber**: o catalogo so tem ferramentas **conhecidas, auditaveis
e mantidas**. Nao tem nada suspeito. As extensoes sao todas FOSS
(software livre).

## Dica do dia

**Receita pro primeiro dia de Vigia**:

1. Catalogo -> Instalar **lynis** + **aide** + **chkrootkit** +
   **rkhunter** (auditoria de seguranca completa).
2. Catalogo -> Instalar **fail2ban** (bloqueia automaticamente IPs que
   tentam invadir).
3. **Pendentes** -> Reiniciar agora.
4. Depois do boot, abra a ferramenta de **Integridade de Arquivos** e
   crie o baseline.
5. Volte aqui na aba **Extensoes**, abra seu navegador favorito,
   instale **uBlock Origin** + **Privacy Badger** + **ClearURLs**.

Pronto. Sistema decentemente blindado em 30 minutos.
