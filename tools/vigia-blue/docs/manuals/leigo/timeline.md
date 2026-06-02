# Vigia Timeline — a "linha do tempo" do que aconteceu (para leigos)

## O que é

Depois de um incidente, a pergunta mais importante é: **"o que aconteceu, e em que
ordem?"**. O **Vigia Timeline** monta uma **linha do tempo única** juntando
pistas de muitos lugares do sistema — quando arquivos foram criados/abertos,
registros de log, instalações, acessos — e coloca tudo **em ordem cronológica**.

É como pegar todas as câmeras, recibos e registros de um prédio e montar uma única
fita do tempo. A ferramenta por baixo se chama **plaso** (a referência em
"super-timeline" forense).

## Para que serve

- **Reconstruir um incidente**: ver a sequência exata de eventos.
- Descobrir **quando** um arquivo apareceu ou foi modificado.
- Cruzar ações suspeitas que aconteceram **perto no tempo**.

## Como usar

Há três jeitos, do mais simples ao mais completo:

### 1) Abrir um export pronto (mais fácil — não precisa do plaso)
Se você já tem um arquivo de timeline no formato **json_line** (gerado pelo plaso
em outro lugar):
1. Clique em **Abrir** e escolha o arquivo.
2. A linha do tempo aparece na hora.

### 2) Analisar um arquivo .plaso
Se você tem um **storage `.plaso`** (a "caixa" que o plaso cria), o Vigia Timeline
o transforma na linha do tempo para você (precisa do plaso instalado).

### 3) Gerar de uma pasta (mais completo, mais lento)
Aponte uma **pasta ou disco** e o Vigia Timeline **extrai** os eventos e monta a
timeline do zero (precisa do plaso; pode levar minutos).

### Lendo o resultado
Cada linha é um **evento**: aparece a **data/hora**, uma **descrição** do que
aconteceu e uma etiqueta com o **tipo** (arquivo, log do sistema, etc.). Tudo em
ordem do tempo.

## Privacidade

Roda **100% local**. Nada é enviado para fora. O Vigia Timeline só **lê** e
organiza — não muda o sistema.

## Precisa instalar

Para **gerar** timelines, instale o plaso (a aba **Sobre** mostra como:
`pipx install plaso`). Para só **abrir** um export json_line, não precisa.
