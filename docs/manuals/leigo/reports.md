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

A janela tem **4 abas**:

**Gerar**: você escolhe o que entra no relatório e clica em "Gerar".
Algumas opções:
- Modelo: 6 opções — "Atividade geral", "Eventos de autenticação",
  "Resumo executivo", "Acesso administrativo", "Conformidade LGPD" (o
  checklist de segurança) e "Saúde do sistema" (junta os scans de antivírus,
  rootkit e integridade)
- Período: 24 horas, 7 dias, 30 dias, ou 90 dias
- **Modo admin** (interruptor): liga pra pegar dados completos (vai
  pedir sua senha 1x)

Clicou em Gerar -> aparece uma barra de progresso por uns segundos ->
o relatório abre **automaticamente** no Firefox.

**Biblioteca**: lista todos os relatórios que você já gerou. Cada um
tem botões "Abrir" e "Excluir". Tem também "Abrir pasta" e o botão
**"Pacote de auditoria (.zip)"** — junta todos os relatórios num arquivo
só, com os selos de verificação e um passo a passo, pronto pra entregar
ao auditor ou guardar.

**Configurações**: tem duas partes.

- **Identidade**: você coloca o **nome do seu escritório**, um subtítulo (ex:
  OAB e cidade), o **responsável técnico** e até o **logo**. A partir daí, todo
  relatório sai com o cabeçalho do **seu escritório** em vez do nome genérico
  da ferramenta — vira um documento profissional seu, pronto pra entregar a
  cliente ou auditor. Preencha uma vez; vale pra todos os relatórios.
- **Agendamento automático**: um interruptor que, quando ligado, faz o programa
  **gerar um relatório sozinho todo mês** (dia 1) e salvar na Biblioteca. Você
  escolhe qual modelo. Assim, sua trilha de auditoria se monta sozinha — em 1
  ano você tem 12 relatórios mensais sem precisar lembrar de nada. (Use um
  modelo que não peça senha: Conformidade LGPD ou Saúde do sistema.)

**Sobre**: explicação da ferramenta com mais detalhes.

## O que cada parte faz

- **Atividade geral**: mostra um panorama — quantos logins SSH bem
  sucedidos, quantas falhas, quem usou administrador, IPs bloqueados.
  Bom pra revisão mensal.
- **Eventos de autenticação**: detalha cada login, cada uso de senha
  de administrador, cada tentativa falhada. Bom pra auditoria LGPD
  formal.
- **Resumo executivo**: a versão de **uma página** — o selo de status, o
  resumo em português, os gráficos e os destaques, sem as tabelas longas.
  É o que você imprime e entrega pro cliente ou auditor.
- **Acesso administrativo**: foca em **quem usou senha de administrador**
  (sudo/pkexec) — cada comando de admin, quando e por quem. Se mais de uma
  pessoa tem admin, ele avisa (importante pra LGPD).
- **Conformidade LGPD**: um **checklist** da segurança da máquina **agora** —
  firewall ligado? disco criptografado? DNS protegido? telemetria desligada?
  Cada item vem com ✅ "conforme" ou ⚠️ "pendente" e uma explicação do porquê
  importa. É **o documento que você mostra pro auditor** ("quais medidas de
  proteção vocês têm?") e dá uma nota (ex: "7 de 9 itens em conformidade").
- **Saúde do sistema**: junta num documento só o **último resultado de cada
  defesa** — a nota do Hardening (Lynis), se o Antivírus achou vírus, se a
  Integridade detectou arquivo alterado e se o Rootkit Scanner achou algo.
  Cada uma vem com ✅ saudável, ⚠️ atenção, 🔴 ação ou "não executada" (quando
  você ainda não rodou aquela ferramenta). É um raio-X das suas proteções.
- **Modo admin**: quando ligado, a ferramenta consegue ver também as
  **tentativas de login que falharam** (importante!) e o registro
  completo do sistema. Sem isso, vai faltar parte da história.

### Como o relatório fica

No **topo** do relatório, pra você entender tudo em 10 segundos:

- Um **selo colorido** com o veredito: 🟢 *"Sem anomalias"*, 🟡 *"Atenção"*
  ou 🔴 *"Revisar"*.
- Um **resumo em português**, de um parágrafo — o que aconteceu no período,
  sem termo técnico. Ex: *"Nos últimos 7 dias houve 3 acessos bem-sucedidos
  e 142 tentativas falhadas (todas bloqueadas). Nenhuma anomalia."*
- **Gráficos**: barras de tentativas falhadas por dia, um ranking dos IPs
  mais bloqueados, e uma "rosca" mostrando acessos certos × errados.

Aí **embaixo** vêm os cartões com os números e as tabelas com cada evento,
caso você precise do detalhe completo. A ideia é: o topo conta a história,
o resto é a prova.

### Como virar PDF

O relatório abre no Firefox. Pra salvar como PDF:
1. `Ctrl+P` (ou menu Arquivo -> Imprimir)
2. Destino: "Salvar como PDF"
3. Pronto

### Selo de integridade (à prova de adulteração)

Todo relatório agora vem com um **🔒 selo de integridade** no rodapé — um
código SHA-256, que é como uma "impressão digital" única do documento. E,
ao lado de cada relatório salvo, a ferramenta cria um arquivo `.sha256`.

Pra que serve: **provar que ninguém alterou o relatório** depois de gerado.
Se um dia precisar mostrar pra um auditor que o documento é original, um
técnico roda um comando (`sha256sum -c`) e o computador confirma se está
intacto — qualquer mudança de uma vírgula é detectada.

O botão **"Pacote de auditoria (.zip)"** na Biblioteca junta tudo isso num
arquivo só (relatórios + selos + instruções) pra você entregar de uma vez.

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
