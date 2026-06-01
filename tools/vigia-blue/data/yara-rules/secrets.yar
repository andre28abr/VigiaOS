/*
 * Vigia YARA — credenciais & segredos expostos.
 *
 * Sinaliza arquivos que parecem conter SEGREDOS em texto: chaves privadas,
 * tokens de nuvem, senhas hardcoded. Cenário clássico de vazamento (segredo
 * commitado, backup com .env, chave SSH solta). Alerta para revisão.
 */

rule Secret_Private_Key : secrets
{
    meta:
        description = "Chave privada (SSH/TLS/PGP) em texto — não deveria ficar exposta em arquivo comum."
        severity = "alto"
    strings:
        $a = "-----BEGIN RSA PRIVATE KEY-----"
        $b = "-----BEGIN OPENSSH PRIVATE KEY-----"
        $c = "-----BEGIN PRIVATE KEY-----"
        $d = "-----BEGIN EC PRIVATE KEY-----"
        $e = "-----BEGIN PGP PRIVATE KEY BLOCK-----"
    condition:
        any of them
}

rule Secret_AWS_Access_Key : secrets
{
    meta:
        description = "Chave de acesso AWS (AKIA...) — credencial de nuvem exposta."
        severity = "alto"
    strings:
        $aws = /AKIA[0-9A-Z]{16}/
    condition:
        $aws
}

rule Secret_Generic_Password : secrets
{
    meta:
        description = "Possível senha/token em texto (password=, secret=, api_key=, token=)."
        severity = "suspeito"
    strings:
        $a = /(password|passwd|senha|secret|api[_-]?key|token)[ \t]*[:=][ \t]*["'][^"']{6,}["']/ nocase
    condition:
        $a
}
