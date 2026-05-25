"""Aba Sobre — manual didatico do Vigia Hash Tools."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Calcula e verifica <b>hashes criptograficos</b> de arquivos e "
        "diretorios. Wrapper de <tt>hashdeep</tt> e dos utilitarios de "
        "coreutils (<tt>sha256sum</tt>, <tt>sha512sum</tt>, <tt>md5sum</tt>) "
        "com UI moderna.\n\n"
        "Hashes (tambem chamados de <i>digests</i> ou <i>fingerprints</i>) "
        "sao funcoes deterministicas que mapeiam qualquer arquivo para uma "
        "string curta de tamanho fixo. Qualquer mudanca no arquivo gera "
        "hash completamente diferente."
    ),
    (
        "Casos de uso",
        "<b>Verificar download</b>:\n"
        "Voce baixou <tt>fedora.iso</tt>. Site oficial publica o hash "
        "SHA-256. Cole na aba <i>Verificar</i>. Bate → download intacto.\n\n"
        "<b>Forensics</b>:\n"
        "Voce vai analisar evidencia digital. Hashes os arquivos antes de "
        "qualquer manipulacao — fingerprint imutavel da prova original. "
        "Tradicionalmente SHA-256 (MD5/SHA-1 considerados quebrados).\n\n"
        "<b>Detectar mudanca em configs</b>:\n"
        "Aba <i>Baseline</i> hashea todo o conteudo de um diretorio (ex: "
        "<tt>/etc/</tt>). Depois compara contra estado atual — alerta de "
        "qualquer arquivo adicionado, removido ou modificado.\n\n"
        "<b>Comparar duas copias</b>:\n"
        "Voce tem duas copias de um arquivo (backup vs original). Hash de "
        "ambos. Bate: identicos. Nao bate: divergiram."
    ),
    (
        "Algoritmos disponiveis",
        "<b>SHA-256</b> (padrao moderno) — recomendado para tudo. "
        "256-bit output. Considerado seguro contra colisoes ate ~2^128 "
        "operacoes (computacionalmente inviavel hoje).\n\n"
        "<b>SHA-512</b> — variante maior do SHA-2. Em alguns CPUs e' "
        "MAIS rapido que SHA-256 (operacoes 64-bit). Use se quiser "
        "extra paranoia ou estiver hasheando arquivos enormes.\n\n"
        "<b>SHA-1</b> — depreciado para uso criptografico. Colisoes "
        "demonstradas em 2017 (SHAttered). Mantido aqui apenas para "
        "compatibilidade com sistemas antigos.\n\n"
        "<b>MD5</b> — quebrado desde 2004. NAO USE para seguranca. "
        "Mantido para checksums de arquivos em transit (downloads que "
        "ainda publicam MD5) ou compatibilidade legacy."
    ),
    (
        "Conceitos importantes",
        "<b>Propriedades de hash criptografico</b>:\n"
        "1. <b>Pre-image resistance</b>: dado hash H, achar arquivo F tal "
        "que hash(F) = H deve ser computacionalmente inviavel.\n"
        "2. <b>Second pre-image</b>: dado F1, achar F2 != F1 com "
        "hash(F2) = hash(F1) deve ser inviavel.\n"
        "3. <b>Collision resistance</b>: achar dois arquivos quaisquer "
        "F1 e F2 com mesmo hash deve ser inviavel.\n\n"
        "MD5 e SHA-1 falharam em #3. SHA-256+ mantem todas as 3.\n\n"
        "<b>Hex encoding</b>: digest binario representado como string "
        "hexadecimal (0-9a-f). SHA-256 = 64 chars; SHA-1 = 40; MD5 = 32.\n\n"
        "<b>Avalanche effect</b>: mudar 1 bit do input muda ~50% dos bits "
        "do output. Util porque qualquer adulteracao e' visivel."
    ),
    (
        "Hash vs HMAC vs assinatura digital",
        "<b>Hash puro</b> (esta tool): qualquer um pode computar. So "
        "garante integridade contra erro acidental. Atacante pode trocar "
        "arquivo E hash juntos.\n\n"
        "<b>HMAC</b>: hash com chave secreta. So quem tem a chave pode "
        "verificar. Garante integridade + autenticidade. Util para "
        "comunicacao com servidores. (Em v0.2.)\n\n"
        "<b>Assinatura digital</b> (GPG): hash + chave privada do "
        "assinante. Qualquer um com chave publica pode verificar. "
        "Garante integridade + identidade do assinante + non-repudiation. "
        "Para isso, use <tt>gpg</tt>/<tt>signify</tt>."
    ),
    (
        "Limitacoes conhecidas",
        "- Hashes paralelos (multi-thread) via <tt>hashdeep</tt> chegam "
        "em v0.2. Esta v0.1 usa <tt>hashlib</tt> single-threaded — bom "
        "para arquivos individuais, lento para diretorios com 100k+ files.\n"
        "- Sem <b>BLAKE3</b> ainda (hash moderno mais rapido que SHA-256).\n"
        "- Sem <b>HMAC</b> (hash com chave). v0.2 alvo.\n"
        "- Sem <b>integracao com File Integrity</b> (sao tools "
        "complementares mas independentes em v0.1).\n"
        "- Baseline ignora symlinks (so segue arquivos regulares)."
    ),
    (
        "LGPD e privacidade",
        "Todas as operacoes sao locais. Nenhum hash e' enviado a servidores.\n\n"
        "<b>Hashes nao revelam conteudo</b>: voce pode publicar hashes de "
        "arquivos confidenciais (ex: contratos de clientes) num registro "
        "publico — o hash sozinho nao permite reconstruir o documento. "
        "Hash funciona como 'prova de existencia' de um arquivo numa "
        "data, sem expor o conteudo.\n\n"
        "<b>Baselines salvos</b> em <tt>~/.local/share/vigia-hash/</tt> "
        "com permissoes <tt>0600</tt> (apenas voce le)."
    ),
    (
        "Saiba mais",
        "- <tt>man sha256sum</tt>, <tt>man hashdeep</tt>\n"
        "- RFC 6234: US Secure Hash Algorithms\n"
        "- Site BLAKE3: https://github.com/BLAKE3-team/BLAKE3\n"
        "- Livro 'Cryptography Engineering' por Ferguson/Schneier/Kohno\n"
        "- Tutorial pratico: https://www.crypto101.io"
    ),
]


class AboutTab(Adw.Bin):
    def __init__(self) -> None:
        super().__init__()
        page = Adw.PreferencesPage()
        for title, content in SECTIONS:
            group = Adw.PreferencesGroup()
            group.set_title(title)
            label = Gtk.Label()
            label.set_markup(content)
            label.set_wrap(True)
            label.set_xalign(0)
            label.set_selectable(True)
            label.set_margin_start(12)
            label.set_margin_end(12)
            label.set_margin_top(12)
            label.set_margin_bottom(12)
            row = Adw.PreferencesRow()
            row.set_child(label)
            row.set_activatable(False)
            group.add(row)
            page.add(group)
        self.set_child(page)
