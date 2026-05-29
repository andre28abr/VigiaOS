# Integridade de Arquivos

## Pra que serve

E' o **alarme contra invasao** do seu computador. Funciona assim:

1. Voce tira uma **foto** de todos os arquivos importantes (a tecnologia
   chama isso de "baseline" — um catalogo de hashes).
2. Toda vez que voce manda **verificar**, ele compara o estado atual
   com a foto.
3. Se alguma coisa mudou que nao deveria ter mudado, ele te avisa.

Exemplos do que ele pega:
- Alguem instalou um **programa malicioso** em `/etc/cron.daily/`
- Alguem criou uma **conta nova** editando `/etc/passwd`
- Alguem colocou uma **chave SSH backdoor** em `/root/.ssh/`

A ferramenta tambem tem um modo **caseiro** pra hashear seus proprios
arquivos (downloads, documentos de cliente) sem precisar de senha de
administrador.

## Quando voce usa isso

- **Logo depois de instalar o sistema** (cria o baseline inicial)
- **Toda semana** (verifica se algo mudou — pode ate agendar)
- **Depois de uma atualizacao grande** (verifica, valida, e refaz o
  baseline)
- **Quando suspeita que alguem mexeu** no computador
- **Pra conferir um download** (a aba Hash calcula o SHA256 e voce
  compara com o do site oficial)
- **Pra arquivar prova** (snapshot de uma pasta de processo — hash do
  pdf, do .doc, etc.)

## O que voce vai ver

A janela tem **6 abas** divididas em dois grupos:

### Grupo 1: AIDE (verifica o sistema todo)

**Status (AIDE)**: mostra se o baseline ja existe, quando foi o ultimo
check, quantas coisas mudaram. Tem 3 botoes grandes: "Criar baseline",
"Verificar agora", "Atualizar baseline".

**Mudancas (AIDE)**: depois de verificar, lista o que foi adicionado,
removido ou modificado. Vermelho = atencao.

### Grupo 2: Hash (verifica arquivos especificos)

**Hash**: voce escolhe um arquivo, escolhe o algoritmo (SHA256 e' o
padrao) e ele calcula. Pra usar isso, voce nao precisa de senha.

**Verificar**: voce cola um hash conhecido (de um site oficial, por
exemplo) + escolhe o arquivo. Ele diz se confere ou nao.

**Baseline**: snapshot de uma pasta inteira em formato JSON. Voce pode
comparar depois — ele aponta o que foi **adicionado, removido,
modificado ou movido** (mesmo arquivo aparecendo em outro lugar). Bom
pra evidenciar que uma pasta de processo nao foi mexida. Se voce tiver o
`hashdeep` instalado, um botao deixa a comparacao mais rapida em pastas
grandes (o resultado e' o mesmo).

**Sobre**: explicacao detalhada.

## O que cada parte faz

- **Baseline**: e' a "foto" inicial. Sem ela, nao ha o que comparar. Ele
  guarda hashes SHA256 de todos os arquivos do sistema (com o perfil
  Silverblue, foca em `/etc`, `/root`, e cron jobs).
- **Verificar**: compara o estado atual com a foto. Se zero diferencas,
  esta tudo certo.
- **Atualizar baseline**: depois de uma atualizacao **legitima** do
  sistema, voce confirma "isso foi eu" e tira uma foto nova.
- **Perfil Silverblue**: a ferramenta vem com um modo otimizado pro
  Fedora Silverblue (que e' o sistema do Vigia). Sem ele, o AIDE encheria
  voce de alarmes falsos a cada atualizacao. **Recomendado: ligar o
  perfil Silverblue.**

## Posso quebrar alguma coisa?

**A parte AIDE (sistema):**
- Criar / verificar / atualizar baseline pede **senha de administrador**.
- Nao quebra nada — so cria arquivos em `/var/lib/aide/`. Mas demora
  alguns minutos (a verificacao precisa ler milhares de arquivos).

**A parte Hash (arquivos):**
- **Nao precisa de senha**, nao quebra nada. So le os arquivos que
  voce escolher.

**Cuidado importante**: depois de uma atualizacao do sistema, a primeira
verificacao **vai** mostrar mudancas em `/etc`. Isso e' normal! Olhe a
lista, valide ("foi eu mesmo que atualizei"), e clique em "Atualizar
baseline" pra aceitar.

## Dica do dia

**Crie o baseline assim que instalar o Vigia, antes de comecar a usar o
computador pra valer.** Assim a foto inicial pega o sistema limpo.

E **escolha o perfil Silverblue** na aba Status. Sem ele, voce vai
levar centenas de alarmes falsos a cada atualizacao do sistema, e vai
desistir de usar a ferramenta. Com o perfil Silverblue, voce so e'
alertado quando algo realmente importa.

Pra advogados: a aba **Baseline** (hash de pasta) e' otima pra
**cadeia de custodia**. Antes de mandar evidencia pra outro escritorio,
gere o baseline JSON da pasta. Voce tem prova matematica do estado dos
arquivos no momento do envio.
