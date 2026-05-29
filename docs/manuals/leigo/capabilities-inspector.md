# Inspetor de Capabilities

## Pra que serve

Pra **descobrir quais programas no seu computador têm poderes
especiais** — tipo "esse programa pode escutar a rede igual root, mesmo
sem ser root".

No Linux, há um sistema chamado **capabilities** que dá "permissões
pequenas" pra programas. Em vez de o programa virar **root** (poder
total, perigoso), ele recebe só a permissão que precisa. Por exemplo:

- O comando `ping` precisa criar pacotes de rede especiais.
  Antigamente ele rodava como root (perigoso). Hoje só tem a
  capability `cap_net_raw` — bem mais seguro.

Mas se algum programa **inesperado** tem capability perigosa (tipo
`cap_sys_admin`, que é "quase root"), é sinal de problema. Pode ser
malware, configuração errada, ou um exploit deixado por um invasor.

Este Inspetor **lista tudo** e classifica em verde/amarelo/vermelho
pra você ver de um relance.

## Quando você usa isso

- **Depois de uma atualização grande do sistema** — pra ver se algum
  programa novo ganhou poder demais.
- **Quando algo parece estranho** no computador (lento, conexões
  esquisitas) — pode ter sido instalado um shell com poderes especiais.
- **Audit periódico LGPD** — comprovar que você checa periodicamente
  a "superfície de risco" do sistema.
- **Curiosidade** — entender o que cada programa pode fazer.

## O que você vai ver

São **4 abas** no topo:

1. **Visão Geral** — Um número grande no centro:
   - `0` em verde = sistema limpo, nenhum programa com capability
   - Número em vermelho = quantas capabilities de **risco ALTO** você tem
   - Número em amarelo = total de programas com capability (nenhuma de
     risco alto)

   Logo abaixo, KPIs detalhados: total, ALTO, MÉDIO, BAIXO.

   No fim, 2 botões:
   - **Escanear** — pede sua senha 1x, faz scan completo (5-30s)
   - **Quick scan** — sem senha, scan rápido em pastas comuns

2. **Binários** — Lista de cada programa com capability. Você pode:
   - Buscar por nome (ex: `ping`)
   - Filtrar por classe de risco (só ALTO, só MÉDIO, etc)
   - Clicar em qualquer item pra ver TODAS as capabilities dele

3. **Capabilities** — Catálogo educativo. As **41 capabilities do
   Linux** explicadas em português, cada uma com:
   - Descrição curta ("Configurar interfaces de rede")
   - Explicação longa de pra que serve
   - Classe de risco

4. **Sobre** — Manual interno mais detalhado.

## O que cada parte faz

- **Hero card** (número grande na Visão Geral) — sumário do estado.
- **KPIs** (linhas abaixo) — detalhamento por classe de risco.
- **Botão "Escanear"** — varre `/usr`, `/opt`, `/var`, `/srv` (cobertura
  total). Pede senha de admin.
- **Botão "Quick scan"** — varre só `/usr/bin`, `/opt`, etc. Não pede
  senha. Mais rápido mas perde paths em `/var`.
- **Aba Binários** — lista navegável. Cada linha expande pra mostrar
  todas as caps daquele programa.
- **Aba Capabilities** — material de estudo. Você pode aprender o que
  cada capability faz lendo aqui.

## Posso quebrar alguma coisa?

**Não.** Esta ferramenta é **somente leitura** (read-only). Ela só
**olha** as capabilities — não adiciona, não remove, não muda nada.

Você pode apertar todos os botões à vontade. O máximo que pode
acontecer é o scan demorar uns 30 segundos.

A única ação que pede senha é o **scan completo** — e mesmo assim, é
só pra **ler** caps em pastas protegidas. Não escreve nada.

## Dica do dia

**Se um programa em `/tmp`, `/home` ou `/var/tmp` tem QUALQUER
capability — desconfie!**

Esses são paths onde programas legítimos quase nunca moram. Atacante
que comprometeu o sistema pode deixar um shell com `cap_setuid` ali
pra ter acesso root persistente.

**Sinal vermelho gritando**: programa desconhecido com
`cap_sys_admin`, `cap_setuid` ou `cap_dac_override` em path
não-canônico.

Quando achar algo assim:
1. Anote o caminho exato.
2. Cheque a aba **Capabilities** pra entender o risco.
3. Se não reconhecer o programa, pesquise no Google.
4. Se confirmar suspeita, ligue pra alguém que entenda do assunto.
