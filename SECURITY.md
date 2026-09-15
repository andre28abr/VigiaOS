# Política de segurança

## Reportando vulnerabilidades

Não abra issue pública para uma vulnerabilidade. Abra um [GitHub Security Advisory privado](https://github.com/andre28abr/VigiaOS/security/advisories/new) ou escreva para o mantenedor pelo e-mail do [perfil](https://github.com/andre28abr).

A resposta sai em até 7 dias. É um projeto de portfólio sem SLA comercial: a gravidade pauta a prioridade.

## Escopo

**São vulnerabilidades reportáveis:** escalada de privilégio pelo caminho Polkit/`pkexec` (execução de comando não previsto, injeção em argumentos), leitura ou escrita de arquivos fora do que a ferramenta declara, relatórios sensíveis gravados com permissão aberta, quebra do selo de integridade dos relatórios, execução de código a partir de conteúdo renderizado nos manuais ou nos relatórios HTML, dependências vulneráveis que afetem o app.

**Não são vulnerabilidades:** as ferramentas ofensivas da seção **Red** fazem o que se propõem; elas ficam atrás de um termo de uso que cita a Lei 12.737/2012 e destinam-se aos próprios sistemas ou a laboratório autorizado. O uso contra terceiros sem autorização é responsabilidade de quem usa.

## Defesas existentes

- Privilégio elevado só via Polkit, com argumentos em lista, nunca por shell com entrada do usuário.
- Nada de serviço ligado por padrão; superfície mínima.
- Relatórios sensíveis com `0600` e diretórios com `0700`; selo de integridade SHA-256 e pacote de auditoria assinado.
- Núcleo do Activity Log em Rust; frontends GTK4 sem execução de conteúdo remoto.
- CI com lint, `pip-audit`, 1460 testes em Python e 28 em Rust.

## Histórico de divulgações

Nenhuma vulnerabilidade reportada até o momento.
