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

O Vigia YARA já vem com regras de partida em **três conjuntos**:

- **Malware** — arquivo de teste EICAR, heurísticas de *webshell* PHP e de
  *reverse shell*.
- **LGPD / dados pessoais** — encontram arquivos que **contêm dado pessoal**:
  CPF, CNPJ, e-mail, telefone e número de cartão. Útil pro escritório saber
  *"quais arquivos têm dados de clientes?"*. (É um **alerta para revisão**: o
  YARA reconhece o *formato* do CPF, não confirma se é um CPF real.)
- **Credenciais & segredos** — chaves privadas, tokens de nuvem e senhas em
  texto que não deveriam estar soltos por aí.

No **Scan**, no campo **Conjunto**, você **escolhe o que procurar**: *Tudo*
(busca geral), ou só um conjunto (ex: só LGPD, ou só Malware) — quando você quer
focar numa coisa específica em vez de varrer tudo.

Você pode adicionar as suas regras (ou conjuntos da comunidade) na pasta
`~/.local/share/vigia-yara/rules/` — quando houver regras suas ali, elas têm
prioridade sobre as que já vêm.

> **Importante sobre Word e PDF:** o YARA lê o arquivo "como está". Em texto
> puro (`.txt`, `.csv`, `.log`, e-mails) ele acha os dados pessoais sem
> problema. Mas `.docx`/`.xlsx` são arquivos **compactados** e muitos `.pdf`
> também — nesses, o texto fica "escondido" e o YARA pode **não encontrar**. A
> verificação desses documentos virá no módulo **Vigia LGPD / Higiene de Dados**
> (planejado), que abre o documento antes de procurar.

## Privacidade

Roda **100% na sua máquina**. O Vigia YARA **não envia** nenhum arquivo nem
resultado pra internet. Cada scan fica salvo localmente (só você lê — permissão
`0600`), pra você ter histórico e, se precisar, documentar.

## Faz parte do VigiaBlue

O Vigia YARA é o módulo de **caça a ameaças** do **VigiaBlue**, a suíte de defesa
(*blue team*) do ecossistema Vigia.
