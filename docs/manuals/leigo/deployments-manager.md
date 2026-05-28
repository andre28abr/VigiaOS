# Gerenciador de Snapshots

## Pra que serve

Pra **voltar no tempo se uma atualizacao do sistema der problema**.

Seu computador (Silverblue, Bluefin, Bazzite, Aurora) e diferente dos
Linux comuns: ele e **imutavel**. Cada vez que voce instala um pacote
ou atualiza, o sistema cria um **snapshot** — uma "foto" completa do
estado anterior.

Esses snapshots se chamam **deployments**, e aparecem no menu do
**GRUB** quando voce liga o computador (aquele menu preto/cinza com
opcoes de boot).

Esta ferramenta **mostra todos os snapshots**, deixa voce:

- **Reverter** — voltar pro anterior se o atual deu problema.
- **Proteger** (pin) — fixar um snapshot pra ele nunca ser apagado
  automaticamente.
- **Limpar** — remover snapshots antigos pra liberar espaco.
- **Anotar** — adicionar etiquetas e notas pra lembrar **por que**
  voce criou cada snapshot (util pra LGPD!).

## Quando voce usa isso

- **Antes de uma atualizacao grande** — proteja o snapshot atual
  ("pin") pra ter pra onde voltar se der ruim.
- **Antes de instalar um programa experimental** — protege o snapshot.
- **Depois que algo quebrou** — reverte pra versao anterior que
  funcionava.
- **Quando o disco enche** (`/boot` cheio) — limpa snapshots antigos.
- **Audit LGPD** — anota nos snapshots **quando** e **por que** voce
  fez mudancas importantes.

## O que voce vai ver

Sao **3 abas**:

1. **Deployments** — A lista de todos os snapshots:
   - Cada snapshot e uma linha. Voce clica pra expandir.
   - **Etiqueta colorida** mostra o status:
     - **ATIVO** (verde) = rodando agora
     - **STAGED** (amarelo) = vai bootar na proxima
     - **ROLLBACK** (cinza) = snapshot anterior, preservado
     - **PIN** (azul) = protegido (nao some no limpa)
   - Mostra a versao do sistema, data, e checksum (codigo unico).
   - Expandindo, voce pode:
     - **Editar etiqueta** (ex: "Antes do upgrade pra Fedora 42")
     - **Escrever notas** (multilinhas — ex: "Pin pro audit semanal.
       Cliente X teve incidente em 2026-05-20.")
     - Ver pacotes que foram **adicionados** ou **removidos**
       neste snapshot
     - **Reverter** (volta pra ele no proximo boot)
     - **Pin / Despinnar**

2. **Cleanup** — A limpeza:
   - Mostra **espaco em `/boot`** (essa parte e pequena, ~1 GB)
   - Quantos snapshots existem e quantos vao ser limpos
   - Botao **Limpar tudo** — remove snapshots pending, rollback e
     cache (em 1 senha soh)
   - **Alerta amarelo** se `/boot` >70%, **vermelho** se >85%

3. **Sobre** — Manual interno detalhado.

## O que cada parte faz

- **Etiqueta colorida** — status visual.
- **Editar etiqueta** — voce poe nome facil de lembrar. So fica
  salvo no seu computador (em `~/.config/vigia-deployments/state.json`
  com permissao **so voce le**).
- **Notas multilinha** — historico do que voce fez. Otimo pra
  comprovar LGPD ("eu pinei o snapshot antes do upgrade").
- **Pin** — protege o snapshot. Nao some no cleanup automatico.
- **Reverter** — escolhe esse snapshot pra bootar da proxima vez.
- **Limpar tudo** — libera espaco. Remove pending, rollback e cache
  metadata.

## Posso quebrar alguma coisa?

**Cuidado.** Algumas acoes aqui mudam o sistema. Mas a regra de ouro
do sistema atomico te protege: **se a operacao der errado, voce
volta no tempo**.

- **Editar etiqueta e notas**: 100% seguro. So salva texto.
- **Pin / Despinnar**: seguro. So protege/desprotege do cleanup.
- **Limpar tudo**: seguro. Soh remove snapshots que nao sao o atual
  nem pinados. Atalhe pode liberar 200-400 MB em `/boot`.
- **Reverter**: a acao mais "perigosa". Mas mesmo assim: ela soh
  marca outro snapshot pra bootar na proxima. **Voce nao perde
  nada** — pode reverter de novo se nao gostar.

**Importante**:

- **NUNCA pinne todos os snapshots**. `/boot` e pequeno. 2-3 pins
  no maximo.
- **Cuidado com `/boot` cheio**: se `/boot` >85%, **os upgrades param
  de funcionar**. Limpe periodicamente.

## Dica do dia

**Antes de qualquer mudanca importante: pin o snapshot atual e
escreva uma nota.**

Exemplo de fluxo:

1. Abra o **Gerenciador de Snapshots**
2. Aba **Deployments**
3. Encontre o **ATIVO** (verde)
4. Clica pra expandir
5. Em **Editar etiqueta**, escreve "Antes do upgrade Fedora 42"
6. Em **Notas**, escreve algo tipo: "Pin antes do upgrade major.
   Cliente X aguarda. Audit LGPD em 2026-06-01."
7. Clica em **Pin**
8. Pronto. Pode atualizar tranquilo.

Se o upgrade der ruim, voce volta nesta tela, clica no snapshot
pinado, clica em **Reverter**. Reinicia. Volta pro estado bom.

**Isso e o superpoder dos sistemas atomicos** (Silverblue, Bluefin,
etc): voce **nunca perde o sistema**. Voce sempre tem pra onde voltar.
