/*
 * Vigia YARA — regras de partida (starter).
 *
 * Conjunto mínimo e SEGURO para o primeiro uso/demo. São heurísticas simples,
 * não um ruleset de produção — o usuário pode adicionar/atualizar regras em
 * ~/.local/share/vigia-yara/rules/ (que têm prioridade sobre estas).
 *
 * Nenhuma destas regras contém malware real: a EICAR é o arquivo-teste padrão
 * de antivírus (inofensivo), e as demais casam *padrões* de código suspeito.
 */

rule EICAR_Test_File
{
    meta:
        description = "Arquivo de teste EICAR (padrão de antivírus). Inofensivo, serve para validar o scanner."
        reference   = "https://www.eicar.org/download-anti-malware-testfile/"
        severity    = "teste"
    strings:
        $eicar = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    condition:
        $eicar
}

rule Suspicious_PHP_Webshell : webshell php
{
    meta:
        description = "Heurística simples de webshell PHP (execução dinâmica + ofuscação)."
        severity    = "suspeito"
    strings:
        $php  = "<?php"
        $a    = "eval("          nocase
        $b    = "base64_decode(" nocase
        $c    = "system("        nocase
        $d    = "shell_exec("    nocase
        $e    = "passthru("      nocase
        $f    = "$_POST["        nocase
        $g    = "$_GET["         nocase
    condition:
        $php and 2 of ($a, $b, $c, $d, $e) and 1 of ($f, $g)
}

rule Linux_Reverse_Shell_OneLiner : shell
{
    meta:
        description = "Padrões comuns de reverse shell em scripts (bash/python/nc)."
        severity    = "suspeito"
    strings:
        $bash = "/dev/tcp/"                       nocase
        $nc   = "nc -e"                           nocase
        $py   = "socket.socket("                  nocase
        $py2  = "subprocess.call("                nocase
        $sh   = "/bin/sh -i"                      nocase
    condition:
        ($bash and $sh) or $nc or ($py and $py2 and $sh)
}
