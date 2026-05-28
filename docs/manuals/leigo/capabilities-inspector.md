# Inspetor de Capabilities

## Pra que serve

Pra **descobrir quais programas no seu computador tem poderes
especiais** — tipo "esse programa pode escutar a rede igual root, mesmo
sem ser root".

No Linux, ha um sistema chamado **capabilities** que da "permissoes
pequenas" pra programas. Em vez de o programa virar **root** (poder
total, perigoso), ele recebe so a permissao que precisa. Por exemplo:

- O comando `ping` precisa criar pacotes de rede especiais.
  Antigamente ele rodava como root (perigoso). Hoje so tem a
  capability `cap_net_raw` — bem mais seguro.

Mas se algum programa **inesperado** tem capability perigosa (tipo
`cap_sys_admin`, que e "quase root"), e sinal de problema. Pode ser
malware, configuracao errada, ou um exploit deixado por um invasor.

Este Inspetor **lista tudo** e classifica em verde/amarelo/vermelho
pra voce ver de um relance.

## Quando voce usa isso

- **Depois de uma atualizacao grande do sistema** — pra ver se algum
  programa novo ganhou poder demais.
- **Quando algo parece estranho** no computador (lento, conexoes
  esquisitas) — pode ter sido instalado um shell com poderes especiais.
- **Audit periodico LGPD** — comprovar que voce checa periodicamente
  a "superficie de risco" do sistema.
- **Curiosidade** — entender o que cada programa pode fazer.

## O que voce vai ver

Sao **4 abas** no topo:

1. **Visao Geral** — Um numero grande no centro:
   - `0` em verde = sistema limpo, nenhum programa com capability
   - Numero em vermelho = quantas capabilities de **risco ALTO** voce tem
   - Numero em amarelo = total de programas com capability (nenhuma de
     risco alto)

   Logo abaixo, KPIs detalhados: total, ALTO, MEDIO, BAIXO.

   No fim, 2 botoes:
   - **Escanear** — pede sua senha 1x, faz scan completo (5-30s)
   - **Quick scan** — sem senha, scan rapido em pastas comuns

2. **Binarios** — Lista de cada programa com capability. Voce pode:
   - Buscar por nome (ex: `ping`)
   - Filtrar por classe de risco (so ALTO, so MEDIO, etc)
   - Clicar em qualquer item pra ver TODAS as capabilities dele

3. **Capabilities** — Catalogo educativo. As **41 capabilities do
   Linux** explicadas em portugues, cada uma com:
   - Descricao curta ("Configurar interfaces de rede")
   - Explicacao longa de pra que serve
   - Classe de risco

4. **Sobre** — Manual interno mais detalhado.

## O que cada parte faz

- **Hero card** (numero grande na Visao Geral) — sumario do estado.
- **KPIs** (linhas abaixo) — detalhamento por classe de risco.
- **Botao "Escanear"** — varre `/usr`, `/opt`, `/var`, `/srv` (cobertura
  total). Pede senha de admin.
- **Botao "Quick scan"** — varre so `/usr/bin`, `/opt`, etc. Nao pede
  senha. Mais rapido mas perde paths em `/var`.
- **Aba Binarios** — lista navegavel. Cada linha expande pra mostrar
  todas as caps daquele programa.
- **Aba Capabilities** — material de estudo. Voce pode aprender o que
  cada capability faz lendo aqui.

## Posso quebrar alguma coisa?

**Nao.** Esta ferramenta e **somente leitura** (read-only). Ela so
**olha** as capabilities — nao adiciona, nao remove, nao muda nada.

Voce pode apertar todos os botoes a vontade. O maximo que pode
acontecer e o scan demorar uns 30 segundos.

A unica acao que pede senha e o **scan completo** — e mesmo assim, e
so pra **ler** caps em pastas protegidas. Nao escreve nada.

## Dica do dia

**Se um programa em `/tmp`, `/home` ou `/var/tmp` tem QUALQUER
capability — desconfie!**

Esses sao paths onde programas legitimos quase nunca moram. Atacante
que comprometeu o sistema pode deixar um shell com `cap_setuid` ali
pra ter acesso root persistente.

**Sinal vermelho gritando**: programa desconhecido com
`cap_sys_admin`, `cap_setuid` ou `cap_dac_override` em path
nao-canonico.

Quando achar algo assim:
1. Anote o caminho exato.
2. Cheque a aba **Capabilities** pra entender o risco.
3. Se nao reconhecer o programa, pesquise no Google.
4. Se confirmar suspeita, ligue pra alguem que entenda do assunto.
