# Atualizações

## Pra que serve

É onde você **mantém o sistema e os programas em dia**. Fica em
**Configurações → Atualizações** (uma das abas). Quando você abre,
ele já verifica sozinho se há atualizações de segurança — e deixa você
aplicar com 1 clique (ou pelo terminal, se preferir).

## Quando você usa isso

- **De vez em quando, pra manter tudo atualizado**: abra e clique em
  "Atualizar agora".
- **Quando quiser conferir** se há novidades de segurança pendentes.

## O que você vai ver

A janela tem **2 abas**:

**Atualizações**: o lugar de manter tudo em dia. Quando você abre, ele
**já verifica sozinho** e te avisa ali mesmo. Você escolhe como atualizar:
- pelo **painel do Vigia** (botão "Atualizar agora"), ou
- copiando o **comando pro terminal** (`sudo dnf upgrade`).

A atualização é aplicada **na hora**, sem reiniciar.

A lista embaixo separa o que vai mudar em duas partes: **Sistema** (pacotes
do sistema operacional) e **Programas da suíte Vigia** (suas ferramentas de
segurança, tipo lynis e ClamAV). Assim você sabe exatamente o que muda.

**Sobre**: explicação da área.

## E pra instalar uma ferramenta nova?

Você não precisa instalar as ferramentas uma a uma. O **instalador completo**
(`./install/bootstrap.sh`, no terminal) já deixa tudo pronto: as ferramentas
do Hub + as do Blue (forense). E cada seção (Hub, Blue, Red) mostra, com
uma **bolinha verde ou vermelha** ao lado de cada ferramenta, se as
dependências dela estão OK — então você vê num relance o que falta.

## Posso quebrar alguma coisa?

**Atualizar não quebra nada** e **não liga nenhum serviço** — é seguro. Você
só precisa digitar a senha de administrador uma vez (pra aplicar pelo painel).

## Dica do dia

Abra esta área **uma vez por semana** e clique em "Atualizar agora". Sistema
e ferramentas de segurança sempre na última versão, em 1 clique.
