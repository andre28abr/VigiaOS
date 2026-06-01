/*
 * Vigia YARA — regras LGPD (descoberta de dados pessoais em arquivos).
 *
 * Sinalizam ARQUIVOS QUE CONTÊM dado pessoal (PII) — útil pra escritório saber
 * "onde estão os dados de clientes". Cada match é um ALERTA PARA REVISÃO, não
 * uma confirmação: YARA casa o PADRÃO (ex: formato de CPF), não valida o dígito.
 *
 * LIMITE IMPORTANTE: YARA lê os BYTES do arquivo. Em texto puro (.txt, .csv,
 * .log, .sql, .eml, código) funciona muito bem. Em .docx/.xlsx (que são ZIP) e
 * em muitos .pdf, o texto está COMPRIMIDO/codificado e o YARA NÃO enxerga — a
 * extração de texto desses formatos fica para o módulo "Vigia LGPD / Higiene de
 * Dados" (futuro, no VigiaHub), que extrai o texto antes de casar os padrões.
 */

rule LGPD_CPF : lgpd pii
{
    meta:
        description = "Contém CPF (formato 000.000.000-00) — dado pessoal. Revise se este arquivo deveria guardar dados de clientes e se está protegido."
        severity = "suspeito"
    strings:
        $cpf = /[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}/
    condition:
        $cpf
}

rule LGPD_CNPJ : lgpd pii
{
    meta:
        description = "Contém CNPJ (00.000.000/0000-00) — dado de pessoa jurídica."
        severity = "baixo"
    strings:
        $cnpj = /[0-9]{2}\.[0-9]{3}\.[0-9]{3}\/[0-9]{4}-[0-9]{2}/
    condition:
        $cnpj
}

rule LGPD_Email : lgpd pii
{
    meta:
        description = "Contém endereço de e-mail — dado pessoal (LGPD)."
        severity = "baixo"
    strings:
        $email = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/
    condition:
        $email
}

rule LGPD_Telefone_BR : lgpd pii
{
    meta:
        description = "Contém telefone brasileiro (DDD entre parênteses + número) — dado pessoal."
        severity = "baixo"
    strings:
        $tel = /\([0-9]{2}\) ?9?[0-9]{4}-[0-9]{4}/
    condition:
        $tel
}

rule LGPD_Cartao_Credito : lgpd pii
{
    meta:
        description = "Possível número de cartão de crédito (16 dígitos) — dado sensível. Atenção redobrada (LGPD + PCI-DSS); este arquivo provavelmente não deveria existir em texto."
        severity = "alto"
    strings:
        $cc = /[0-9]{4}[ -][0-9]{4}[ -][0-9]{4}[ -][0-9]{4}/
    condition:
        $cc
}
