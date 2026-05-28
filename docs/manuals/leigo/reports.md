# Relatorios

## Pra que serve

Gera **relatorios em PDF** com o que aconteceu no seu computador — quem
fez login, quem usou senha de administrador, quais IPs foram bloqueados.

E' o documento que voce mostra pra:
- **Auditor de LGPD** ("como vocem monitoram acessos?")
- **Cliente desconfiado** ("quem mexeu nos dados do meu processo?")
- **Voce mesmo no fim do mes** (revisao de seguranca)

## Quando voce usa isso

- **Toda virada de mes**: gera relatorio dos ultimos 30 dias, salva PDF
  numa pasta de auditoria.
- **Quando algo estranho aconteceu**: relatorio das ultimas 24h pra
  isolar o que rolou.
- **Antes de reuniao com cliente**: prova que voce monitora.
- **Quando o auditor vem**: pacote dos ultimos 90 dias.

## O que voce vai ver

A janela tem **3 abas**:

**Gerar**: voce escolhe o que entra no relatorio e clica em "Gerar".
Algumas opcoes:
- Modelo: "Atividade geral" (panorama) ou "Eventos de autenticacao"
  (focado em quem entrou)
- Periodo: 24 horas, 7 dias, 30 dias, ou 90 dias
- **Modo admin** (interruptor): liga pra pegar dados completos (vai
  pedir sua senha 1x)

Clicou em Gerar -> aparece uma barra de progresso por uns segundos ->
o relatorio abre **automaticamente** no Firefox.

**Biblioteca**: lista todos os relatorios que voce ja gerou. Cada um
tem botoes "Abrir" e "Excluir". Tem tambem um botao "Abrir pasta" pra
ver onde os arquivos estao.

**Sobre**: explicacao da ferramenta com mais detalhes.

## O que cada parte faz

- **Atividade geral**: mostra um panorama — quantos logins SSH bem
  sucedidos, quantas falhas, quem usou administrador, IPs bloqueados.
  Bom pra revisao mensal.
- **Eventos de autenticacao**: detalha cada login, cada uso de senha
  de administrador, cada tentativa falhada. Bom pra auditoria LGPD
  formal.
- **Modo admin**: quando ligado, a ferramenta consegue ver tambem as
  **tentativas de login que falharam** (importante!) e o registro
  completo do sistema. Sem isso, vai faltar parte da historia.

### Como virar PDF

O relatorio abre no Firefox. Pra salvar como PDF:
1. `Ctrl+P` (ou menu Arquivo -> Imprimir)
2. Destino: "Salvar como PDF"
3. Pronto

## Posso quebrar alguma coisa?

**Nao.** Essa ferramenta so **le** o que o sistema ja registrou. Ela
nao muda nada, nao mexe em arquivos, nao reinicia servico.

O unico cuidado: os relatorios contem dados sensiveis (IPs, nomes de
usuario, comandos administrativos). A ferramenta salva eles num lugar
seguro (`~/.local/share/vigia-reports/`) com permissoes restritivas —
**so voce le**. Nao guarde em pasta sincronizada na nuvem
(Dropbox/iCloud/OneDrive) sem pensar duas vezes.

## Dica do dia

**Crie uma rotina mensal**: todo dia 1, gera o relatorio "Atividade
geral" dos ultimos 30 dias com modo admin ligado, salva como PDF numa
pasta `Auditoria/2026-XX/`. Em 1 ano voce tem 12 PDFs que provam
diligencia em qualquer fiscalizacao.

Se voce e' advogado lidando com LGPD, isso e' literalmente prova
documental de **medidas tecnicas e administrativas** (art. 46 da LGPD).
