# Tudo Certo?

## Pra que serve

Pra responder, **de relance**, uma pergunta simples: **meu computador
está seguro?**

É o **primeiro item do Hub** (na categoria *Visão geral*) e funciona como
um **semáforo de segurança**. Em vez de você abrir cinco ferramentas
diferentes pra conferir se está tudo no lugar, o **Tudo Certo?** olha as
**4 coisas mais importantes** de uma vez e mostra o resultado num
**🟢 verde / 🟡 amarelo / 🔴 vermelho** bem grande no topo.

Pensa nele como o **painel do carro**: você não precisa abrir o capô pra
saber que está tudo bem — basta olhar se alguma luz acendeu.

## Quando você usa isso

- **Toda vez que abrir o VigiaOS** — uma olhada de 2 segundos pra ter
  certeza de que nada importante está desligado.
- **Depois de instalar ou mexer no sistema** — pra confirmar que você não
  deixou o firewall desligado ou a privacidade aberta sem querer.
- **Antes de uma auditoria LGPD** — pra checar rápido se as proteções
  básicas estão ativas.
- **Quando algo "parece estranho"** — é o melhor lugar pra começar, antes
  de ir fundo nas ferramentas específicas.

## O que você vai ver

No topo, um **ícone grande + uma frase** que resume tudo:

- 🟢 **Tudo certo!** — Seu PC está com as proteções básicas em dia.
- 🟡 **Alguns pontos de atenção** — Nada grave, mas vale resolver os
  itens abaixo.
- 🔴 **Precisa de atenção** — Há algo importante desligado.

O semáforo geral mostra **sempre o pior caso**: basta um item vermelho pra
o topo ficar vermelho.

Logo abaixo, uma **lista com 4 verificações**, cada uma com seu próprio
sinalzinho (verde/amarelo/vermelho) e uma frase curta explicando:

1. **Atualizações** — se o sistema tem atualizações pendentes.
2. **Firewall** — se o firewall está ligado e protegendo.
3. **Antivírus** — se o ClamAV está instalado e com a base de vírus
   recente (atualizada nos últimos 7 dias).
4. **Privacidade** — se os ajustes recomendados de privacidade estão
   ativos.

## O que cada parte faz

- **O semáforo grande (no topo)** — o resumo de tudo. É o "está tudo bem?"
  respondido numa olhada.
- **Cada linha da lista** — uma verificação individual. O sinalzinho à
  esquerda diz se aquele item está OK (verde), merece atenção (amarelo) ou
  está com problema (vermelho).
- **Botão "Resolver"** — aparece **só nos itens que estão fora do lugar**.
  Em vez de você ter que adivinhar onde mexer, ele **te leva direto pra
  ferramenta certa**, já na aba certa. Por exemplo:
  - Firewall desligado → botão **Ligar firewall** abre o Firewall.
  - Base de vírus velha → botão **Atualizar base** abre o Antivírus já na
    aba *Base de dados*.
  - Atualizações pendentes → botão **Ver Atualizações** abre
    Configurações → Atualizações.
  - Privacidade a ajustar → botão **Abrir Privacidade** abre os Controles
    de Privacidade.
- **Botão "Verificar de novo" (a setinha no topo)** — refaz as checagens
  na hora.

> **Re-checa sozinho.** Toda vez que você volta pra esta tela, ele
> verifica tudo de novo. Então, se você sair, **resolver um item** (tipo
> atualizar a base do antivírus) e voltar, o semáforo já aparece
> atualizado — não fica preso no resultado antigo.

## Posso quebrar alguma coisa?

**Não.** O Tudo Certo? é **só de leitura** — ele apenas **olha** o estado
do sistema (firewall ligado ou não, idade da base de vírus, etc.) e mostra.
Ele **não muda nada sozinho**.

Quem muda as coisas são as ferramentas pra onde os botões **Resolver** te
levam — e mesmo lá, nada acontece sem você clicar e (quando preciso)
digitar a senha de admin.

## Dica do dia

> Deixe o **Tudo Certo?** ser a sua primeira parada sempre que abrir o
> VigiaOS. Se estiver tudo **verde**, ótimo — pode fechar tranquilo. Se
> tiver algum **amarelo ou vermelho**, clique no **Resolver** do item e
> ele te leva exatamente onde precisa mexer. É o caminho mais rápido pra
> manter o escritório em conformidade sem virar especialista.
