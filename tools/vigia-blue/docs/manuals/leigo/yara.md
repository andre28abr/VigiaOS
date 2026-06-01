# Vigia YARA — caça a malware (para leigos)

## O que é

O **Vigia YARA** vasculha seus arquivos procurando **malware** — coisas como
*webshells* (páginas que dão controle do site a um invasor), *miners* (programas
que usam sua máquina pra minerar criptomoeda escondido), *ransomware* e backdoors.

Ele usa o **YARA**, uma ferramenta que funciona como um "detector de padrões":
em vez de comparar com uma lista de vírus conhecidos (como o antivírus comum),
o YARA procura **trechos e características** típicas de código malicioso. É muito
usado por times de segurança pra **caçar ameaças** (*threat hunting*).

## Para que serve

- Verificar uma pasta suspeita (ex: a pasta de um site, `/var/www`, ou um
  pendrive) antes de confiar nela.
- Procurar webshells e scripts maliciosos depois de um incidente.
- Confirmar se um arquivo que você baixou casa com algum padrão perigoso.

## Como usar

1. **Escolha a pasta ou arquivo** que quer examinar (botão de selecionar pasta).
2. Clique em **Escanear**.
3. Aguarde — o Vigia YARA passa todas as **regras** por cada arquivo.
4. Veja os **resultados**:
   - **Nenhum alerta** → nada suspeito casou com as regras. 👍
   - **Um ou mais alertas** → cada alerta é um **botão**: aparece o **nome do
     arquivo** e a **severidade** (Teste / Suspeito / Alto…). **Clique no alerta**
     pra abrir os detalhes:
     - **O que é** — explicação em português do que foi encontrado;
     - **Arquivo** — o caminho completo;
     - **Regra (técnico)** — o nome da regra YARA + tags, pra quem quer o detalhe.
   - No fim da lista há um **"Saída do yara"** (recolhido) com o resultado bruto
     da ferramenta, caso queira ver exatamente o que ela imprimiu.

> Um alerta **não é prova absoluta** de vírus — é um aviso de que aquele arquivo
> tem características suspeitas e merece um olhar humano. A descrição em "O que é"
> ajuda a entender o risco.

## As regras

O Vigia YARA já vem com um conjunto **inicial** de regras (o arquivo de teste
EICAR, heurísticas de webshell PHP e de *reverse shell*). Você pode adicionar as
suas (ou conjuntos da comunidade) na pasta `~/.local/share/vigia-yara/rules/` —
quando houver regras suas ali, elas têm prioridade sobre as que já vêm.

## Privacidade

Roda **100% na sua máquina**. O Vigia YARA **não envia** nenhum arquivo nem
resultado pra internet. Cada scan fica salvo localmente (só você lê — permissão
`0600`), pra você ter histórico e, se precisar, documentar.

## Faz parte do VigiaBlue

O Vigia YARA é o módulo de **caça a ameaças** do **VigiaBlue**, a suíte de defesa
(*blue team*) do ecossistema Vigia.
