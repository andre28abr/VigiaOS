# Verificação de Hardening

## Pra que serve

**Hardening** quer dizer "endurecer" — deixar o computador mais
resistente a ataques. Esta ferramenta faz um **check-up completo**
de segurança e te dá uma nota.

Imagina o **check-up médico anual**: você não vai ao médico todo
dia, mas uma vez por ano vale a pena fazer exame pra ver como está
a saúde. Esta ferramenta é o **check-up anual de segurança** do
seu computador.

Ela usa uma ferramenta consagrada chamada **Lynis** (~250 testes
de segurança) e mostra o resultado de um jeito visual e em
português, em vez de uma tela de terminal cheia de texto.

## Quando você usa isso

Não precisa rodar todo dia. Recomendado:

1. **Uma vez por mês ou trimestre** — pra acompanhar evolução
2. **Antes de auditoria externa** (advogado conferindo postura
   LGPD, por exemplo) — pra ter relatório recente como evidência
3. **Depois de mexer em coisa importante** (instalar serviço novo,
   mudar configuração) — ver se introduziu problema

## O que você vai ver

A tela principal tem uma **nota gigante** (0 a 100) — é o seu
**Hardening Index**. Quanto **maior**, melhor. Embaixo, abas com
detalhes:

| Aba | Pra que serve |
|---|---|
| **Resumo** | A nota + estatísticas + botão "Executar" |
| **Warnings** | Lista do que é **crítico** — corrigir primeiro |
| **Suggestions** | Lista de **melhorias** — pra aperfeiçoar |
| **Categorias** | Visão por área (autenticação, kernel, rede...) |

## O que cada parte faz

### Resumo

O coração da ferramenta:

- **Nota grande** (ex: 78) — quanto mais alta, melhor
- **Label de severidade**: Excelente / Bom / Razoável / Insuficiente
  / Crítico
- **Estatísticas**: quantos warnings, quantas suggestions, quantos
  testes rodaram, quando foi a última execução
- **Botão "Executar"** — começa um novo check-up. Pede senha
  (precisa de privilégio pra ler arquivos sensíveis). Demora
  **2 a 5 minutos** rodando.

Escala de notas:

| Faixa | Nível |
|---|---|
| 85-100 | Excelente |
| 75-84 | Bom |
| 60-74 | Razoável |
| 40-59 | Insuficiente |
| 0-39 | Crítico |

### Warnings (atenção)

São problemas que merecem ser tratados **primeiro**. Cada item tem
um código (ex: `KRNL-5820`) — você pode pesquisar esse código no
Google pra ver instruções oficiais de como resolver.

### Suggestions (melhorias)

São **dicas de aperfeiçoamento**. Não são urgentes, mas se
implementar melhora a nota. Tipo "configurar tempo mínimo de senha"
ou "instalar ferramenta X".

### Categorias

Mostra tudo agrupado por área. Útil pra entender onde estão os
maiores problemas: tem 10 warnings de "Kernel", mas só 1 de
"Autenticação"? Foco na primeira.

## Posso quebrar alguma coisa?

**Não!** Esta ferramenta é **só de leitura** — só faz a auditoria
e mostra resultado. **Não muda nada no sistema**.

Ela pede senha porque precisa **ler** arquivos sensíveis (lista de
usuários, configurações do kernel, etc.), mas só **lê**, não
escreve.

O relatório que ela gera fica protegido em `/var/log/` com
permissões pra que só você e o administrador leiam — não fica
exposto pra outros usuários do sistema.

## Dica do dia

> Rode uma auditoria **agora** e anote a nota. Daqui a 1 mês,
> rode de novo. Se a nota **subiu** = você (ou seu técnico) está
> melhorando a postura. Se **caiu** = alguma coisa mudou pra pior.
>
> Pra **escritórios de advocacia** (LGPD): essa nota + relatório
> são **boas evidências** de diligência. Salva PDF do relatório
> pela ferramenta **Reports** (do Vigia) periodicamente — é prova
> de que você cuida da segurança do escritório.
