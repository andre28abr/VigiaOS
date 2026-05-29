# Gerenciador de Snapshots

## Pra que serve

Pra **voltar no tempo se uma atualização do sistema der problema**.

Seu computador (Silverblue, Bluefin, Bazzite, Aurora) é diferente dos
Linux comuns: ele é **imutável**. Cada vez que você instala um pacote
ou atualiza, o sistema cria um **snapshot** — uma "foto" completa do
estado anterior.

Esses snapshots se chamam **deployments**, e aparecem no menu do
**GRUB** quando você liga o computador (aquele menu preto/cinza com
opções de boot).

Esta ferramenta **mostra todos os snapshots**, deixa você:

- **Reverter** — voltar pro anterior se o atual deu problema.
- **Proteger** (pin) — fixar um snapshot pra ele nunca ser apagado
  automaticamente.
- **Limpar** — remover snapshots antigos pra liberar espaço.
- **Anotar** — adicionar etiquetas e notas pra lembrar **por que**
  você criou cada snapshot (útil pra LGPD!).

## Quando você usa isso

- **Antes de uma atualização grande** — proteja o snapshot atual
  ("pin") pra ter pra onde voltar se der ruim.
- **Antes de instalar um programa experimental** — protege o snapshot.
- **Depois que algo quebrou** — reverte pra versão anterior que
  funcionava.
- **Quando o disco enche** (`/boot` cheio) — limpa snapshots antigos.
- **Audit LGPD** — anota nos snapshots **quando** e **por que** você
  fez mudanças importantes.

## O que você vai ver

São **3 abas**:

1. **Deployments** — A lista de todos os snapshots:
   - Cada snapshot é uma linha. Você clica pra expandir.
   - **Etiqueta colorida** mostra o status:
     - **ATIVO** (verde) = rodando agora
     - **STAGED** (amarelo) = vai bootar na próxima
     - **ROLLBACK** (cinza) = snapshot anterior, preservado
     - **PIN** (azul) = protegido (não some no limpa)
   - Mostra a versão do sistema, data, e checksum (código único).
   - Expandindo, você pode:
     - **Editar etiqueta** (ex: "Antes do upgrade pra Fedora 42")
     - **Escrever notas** (multilinhas — ex: "Pin pro audit semanal.
       Cliente X teve incidente em 2026-05-20.")
     - Ver pacotes que foram **adicionados** ou **removidos**
       neste snapshot
     - **Reverter** (volta pra ele no próximo boot)
     - **Pin / Despinnar**

2. **Cleanup** — A limpeza:
   - Mostra **espaço em `/boot`** (essa parte é pequena, ~1 GB)
   - Quantos snapshots existem e quantos vão ser limpos
   - Botão **Limpar tudo** — remove snapshots pending, rollback e
     cache (em 1 senha só)
   - **Alerta amarelo** se `/boot` >70%, **vermelho** se >85%

3. **Sobre** — Manual interno detalhado.

## O que cada parte faz

- **Etiqueta colorida** — status visual.
- **Editar etiqueta** — você põe nome fácil de lembrar. Só fica
  salvo no seu computador (em `~/.config/vigia-deployments/state.json`
  com permissão **só você lê**).
- **Notas multilinha** — histórico do que você fez. Ótimo pra
  comprovar LGPD ("eu pinei o snapshot antes do upgrade").
- **Pin** — protege o snapshot. Não some no cleanup automático.
- **Reverter** — escolhe esse snapshot pra bootar da próxima vez.
- **Limpar tudo** — libera espaço. Remove pending, rollback e cache
  metadata.

## Posso quebrar alguma coisa?

**Cuidado.** Algumas ações aqui mudam o sistema. Mas a regra de ouro
do sistema atômico te protege: **se a operação der errado, você
volta no tempo**.

- **Editar etiqueta e notas**: 100% seguro. Só salva texto.
- **Pin / Despinnar**: seguro. Só protege/desprotege do cleanup.
- **Limpar tudo**: seguro. Só remove snapshots que não são o atual
  nem pinados. Atalhe pode liberar 200-400 MB em `/boot`.
- **Reverter**: a ação mais "perigosa". Mas mesmo assim: ela só
  marca outro snapshot pra bootar na próxima. **Você não perde
  nada** — pode reverter de novo se não gostar.

**Importante**:

- **NUNCA pinne todos os snapshots**. `/boot` é pequeno. 2-3 pins
  no máximo.
- **Cuidado com `/boot` cheio**: se `/boot` >85%, **os upgrades param
  de funcionar**. Limpe periodicamente.

## Dica do dia

**Antes de qualquer mudança importante: pin o snapshot atual e
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

Se o upgrade der ruim, você volta nesta tela, clica no snapshot
pinado, clica em **Reverter**. Reinicia. Volta pro estado bom.

**Isso é o superpoder dos sistemas atômicos** (Silverblue, Bluefin,
etc): você **nunca perde o sistema**. Você sempre tem pra onde voltar.
