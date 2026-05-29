# Integridade de Arquivos

## Pra que serve

É o **alarme contra invasão** do seu computador. Funciona assim:

1. Você tira uma **foto** de todos os arquivos importantes (a tecnologia
   chama isso de "baseline" — um catálogo de hashes).
2. Toda vez que você manda **verificar**, ele compara o estado atual
   com a foto.
3. Se alguma coisa mudou que não deveria ter mudado, ele te avisa.

Exemplos do que ele pega:
- Alguém instalou um **programa malicioso** em `/etc/cron.daily/`
- Alguém criou uma **conta nova** editando `/etc/passwd`
- Alguém colocou uma **chave SSH backdoor** em `/root/.ssh/`

A ferramenta também tem um modo **caseiro** pra hashear seus próprios
arquivos (downloads, documentos de cliente) sem precisar de senha de
administrador.

## Quando você usa isso

- **Logo depois de instalar o sistema** (cria o baseline inicial)
- **Toda semana** (verifica se algo mudou — pode até agendar)
- **Depois de uma atualização grande** (verifica, valida, e refaz o
  baseline)
- **Quando suspeita que alguém mexeu** no computador
- **Pra conferir um download** (a aba Hash calcula o SHA256 e você
  compara com o do site oficial)
- **Pra arquivar prova** (snapshot de uma pasta de processo — hash do
  pdf, do .doc, etc.)

## O que você vai ver

A janela tem **6 abas** divididas em dois grupos:

### Grupo 1: AIDE (verifica o sistema todo)

**Status (AIDE)**: mostra se o baseline já existe, quando foi o último
check, quantas coisas mudaram. Tem 3 botões grandes: "Criar baseline",
"Verificar agora", "Atualizar baseline".

**Mudanças (AIDE)**: depois de verificar, lista o que foi adicionado,
removido ou modificado. Vermelho = atenção.

### Grupo 2: Hash (verifica arquivos específicos)

**Hash**: você escolhe um arquivo, escolhe o algoritmo (SHA256 é o
padrão) e ele calcula. Pra usar isso, você não precisa de senha.

**Verificar**: você cola um hash conhecido (de um site oficial, por
exemplo) + escolhe o arquivo. Ele diz se confere ou não.

**Baseline**: snapshot de uma pasta inteira em formato JSON. Você pode
comparar depois — ele aponta o que foi **adicionado, removido,
modificado ou movido** (mesmo arquivo aparecendo em outro lugar). Bom
pra evidenciar que uma pasta de processo não foi mexida. Se você tiver o
`hashdeep` instalado, um botão deixa a comparação mais rápida em pastas
grandes (o resultado é o mesmo).

**Sobre**: explicação detalhada.

## O que cada parte faz

- **Baseline**: é a "foto" inicial. Sem ela, não há o que comparar. Ele
  guarda hashes SHA256 de todos os arquivos do sistema (com o perfil
  Silverblue, foca em `/etc`, `/root`, e cron jobs).
- **Verificar**: compara o estado atual com a foto. Se zero diferenças,
  está tudo certo.
- **Atualizar baseline**: depois de uma atualização **legítima** do
  sistema, você confirma "isso foi eu" e tira uma foto nova.
- **Perfil Silverblue**: a ferramenta vem com um modo otimizado pro
  Fedora Silverblue (que é o sistema do Vigia). Sem ele, o AIDE encheria
  você de alarmes falsos a cada atualização. **Recomendado: ligar o
  perfil Silverblue.**

## Posso quebrar alguma coisa?

**A parte AIDE (sistema):**
- Criar / verificar / atualizar baseline pede **senha de administrador**.
- Não quebra nada — só cria arquivos em `/var/lib/aide/`. Mas demora
  alguns minutos (a verificação precisa ler milhares de arquivos).

**A parte Hash (arquivos):**
- **Não precisa de senha**, não quebra nada. Só lê os arquivos que
  você escolher.

**Cuidado importante**: depois de uma atualização do sistema, a primeira
verificação **vai** mostrar mudanças em `/etc`. Isso é normal! Olhe a
lista, valide ("foi eu mesmo que atualizei"), e clique em "Atualizar
baseline" pra aceitar.

## Dica do dia

**Crie o baseline assim que instalar o Vigia, antes de começar a usar o
computador pra valer.** Assim a foto inicial pega o sistema limpo.

E **escolha o perfil Silverblue** na aba Status. Sem ele, você vai
levar centenas de alarmes falsos a cada atualização do sistema, e vai
desistir de usar a ferramenta. Com o perfil Silverblue, você só é
alertado quando algo realmente importa.

Pra advogados: a aba **Baseline** (hash de pasta) é ótima pra
**cadeia de custódia**. Antes de mandar evidência pra outro escritório,
gere o baseline JSON da pasta. Você tem prova matemática do estado dos
arquivos no momento do envio.
