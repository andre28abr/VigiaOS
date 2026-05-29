# Relatórios

## Pra que serve

Gera **relatórios em PDF** com o que aconteceu no seu computador — quem
fez login, quem usou senha de administrador, quais IPs foram bloqueados.

É o documento que você mostra pra:
- **Auditor de LGPD** ("como vocês monitoram acessos?")
- **Cliente desconfiado** ("quem mexeu nos dados do meu processo?")
- **Você mesmo no fim do mês** (revisão de segurança)

## Quando você usa isso

- **Toda virada de mês**: gera relatório dos últimos 30 dias, salva PDF
  numa pasta de auditoria.
- **Quando algo estranho aconteceu**: relatório das últimas 24h pra
  isolar o que rolou.
- **Antes de reunião com cliente**: prova que você monitora.
- **Quando o auditor vem**: pacote dos últimos 90 dias.

## O que você vai ver

A janela tem **3 abas**:

**Gerar**: você escolhe o que entra no relatório e clica em "Gerar".
Algumas opções:
- Modelo: "Atividade geral" (panorama) ou "Eventos de autenticação"
  (focado em quem entrou)
- Período: 24 horas, 7 dias, 30 dias, ou 90 dias
- **Modo admin** (interruptor): liga pra pegar dados completos (vai
  pedir sua senha 1x)

Clicou em Gerar -> aparece uma barra de progresso por uns segundos ->
o relatório abre **automaticamente** no Firefox.

**Biblioteca**: lista todos os relatórios que você já gerou. Cada um
tem botões "Abrir" e "Excluir". Tem também um botão "Abrir pasta" pra
ver onde os arquivos estão.

**Sobre**: explicação da ferramenta com mais detalhes.

## O que cada parte faz

- **Atividade geral**: mostra um panorama — quantos logins SSH bem
  sucedidos, quantas falhas, quem usou administrador, IPs bloqueados.
  Bom pra revisão mensal.
- **Eventos de autenticação**: detalha cada login, cada uso de senha
  de administrador, cada tentativa falhada. Bom pra auditoria LGPD
  formal.
- **Modo admin**: quando ligado, a ferramenta consegue ver também as
  **tentativas de login que falharam** (importante!) e o registro
  completo do sistema. Sem isso, vai faltar parte da história.

### Como virar PDF

O relatório abre no Firefox. Pra salvar como PDF:
1. `Ctrl+P` (ou menu Arquivo -> Imprimir)
2. Destino: "Salvar como PDF"
3. Pronto

## Posso quebrar alguma coisa?

**Não.** Essa ferramenta só **lê** o que o sistema já registrou. Ela
não muda nada, não mexe em arquivos, não reinicia serviço.

O único cuidado: os relatórios contêm dados sensíveis (IPs, nomes de
usuário, comandos administrativos). A ferramenta salva eles num lugar
seguro (`~/.local/share/vigia-reports/`) com permissões restritivas —
**só você lê**. Não guarde em pasta sincronizada na nuvem
(Dropbox/iCloud/OneDrive) sem pensar duas vezes.

## Dica do dia

**Crie uma rotina mensal**: todo dia 1, gera o relatório "Atividade
geral" dos últimos 30 dias com modo admin ligado, salva como PDF numa
pasta `Auditoria/2026-XX/`. Em 1 ano você tem 12 PDFs que provam
diligência em qualquer fiscalização.

Se você é advogado lidando com LGPD, isso é literalmente prova
documental de **medidas técnicas e administrativas** (art. 46 da LGPD).
