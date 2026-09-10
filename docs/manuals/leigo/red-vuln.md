# Vigia Vuln Scanner — vulnerabilidades por templates (para leigos)

## O que é

O **Vigia Vuln Scanner** vai um passo além do Network Scanner: em vez de só dizer
"esta porta está aberta e é o serviço X", ele **procura falhas conhecidas** nesse
alvo — vulnerabilidades já catalogadas (as famosas **CVEs**), painéis
administrativos expostos, senhas padrão, arquivos de configuração vazando, etc.

Ele usa o **nuclei**, uma ferramenta que roda milhares de **templates** (receitas
de verificação) mantidos por uma grande comunidade de segurança. Cada template
sabe reconhecer um problema específico. É uma varredura **ativa**: o nuclei
**conversa com o alvo** para testar cada template.

## Para que serve

- Descobrir se um servidor ou site **seu** tem alguma vulnerabilidade **conhecida**
  ainda não corrigida.
- Confirmar que uma correção resolveu o problema (rodar de novo depois de
  atualizar).
- Aprofundar um host/URL que o **Network Scanner** apontou como interessante.

## Use apenas com autorização

Este módulo faz **varredura ativa**. Só use contra:

- **sistemas seus**; ou
- alvos com **autorização formal por escrito**.

Testar vulnerabilidades em sistemas de terceiros sem permissão é **crime no
Brasil** (**Lei 12.737/2012** — a "Lei Carolina Dieckmann"). Ao abrir qualquer
módulo do **VigiaRed** pela primeira vez, você lê e aceita um **termo de uso** que
reforça isso. Você é o único responsável pelo uso.

## Como usar

1. Abra o Vigia Vuln Scanner (seção **Red**). Na primeira vez, **aceite o termo
   de uso**.
2. Na aba **Varredura**, em *Alvo autorizado*, digite uma **URL** ou **domínio** —
   ex.: `https://exemplo.com.br` ou `exemplo.com.br`.
3. Escolha o **Perfil** (conjunto de templates):
   - **CVEs graves** (padrão) — vulnerabilidades conhecidas de severidade
     alta/crítica; focado e rápido.
   - **Padrão** — CVEs + exposições + configurações erradas (médio para cima).
   - **Exposições** — painéis, logins padrão e arquivos/segredos expostos.
   - **Tecnologias** — só identifica tecnologias e versões (não explora nada).
   - **Completa** — todos os templates; bem mais lento (minutos).
4. Clique em **Escanear**. Durante a varredura o botão vira **Cancelar** — pode
   parar quando quiser.
5. Na **primeira execução**, o nuclei pode baixar sozinho os templates da
   comunidade — isso é normal e só acontece uma vez.

## Como ler os resultados

Os achados aparecem na aba **Achados**, **ordenados por gravidade** — do mais
grave (crítico/alto) para o menos grave (info). Cada achado mostra o **nome**, a
**severidade**, **onde** foi encontrado e uma **descrição**.

- Um achado de severidade **crítica** ou **alta** merece atenção imediata: em
  geral significa uma falha conhecida com correção disponível.
- Achados **info** costumam ser apenas informação (ex.: tecnologia detectada),
  não um problema.
- Use **Exportar** para salvar o laudo e anexar a um relatório.
- Toda varredura fica na aba **Histórico**.

> Um achado **não é prova de invasão** — é um aviso de que aquele ponto tem uma
> característica conhecida e merece revisão por um humano.

## O que NÃO fazer

- **Não** rode contra URLs/sistemas que não são seus e não têm autorização
  escrita.
- **Não** use o resultado para explorar a falha em produção de terceiros — o
  propósito é **encontrar e corrigir** no que é seu.
- **Não** conclua que "zero achados = 100% seguro": significa apenas que os
  templates daquele perfil não encontraram nada.

## Privacidade

O Vuln Scanner roda **na sua máquina**. Os testes vão **só para o alvo que você
digitou**; nada é enviado a servidores da Vigia. Cada varredura é salva
localmente com permissão restrita (**0600** — só você lê), em
`~/.local/share/vigia-vuln/`.

## Faz parte do VigiaRed

O Vigia Vuln Scanner aprofunda, no nível de **vulnerabilidades**, o que o
**Network Scanner** descobriu. Para falhas específicas de **aplicações web**
(formulários, parâmetros), o passo seguinte é o **Vigia Web Scanner**.
