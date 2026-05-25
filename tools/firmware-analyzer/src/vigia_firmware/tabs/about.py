"""Aba Sobre — manual didatico do Vigia Firmware Analyzer."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "GUI moderna para o <b>binwalk</b> — ferramenta padrao de analise de "
        "firmware. Detecta arquivos embarcados num blob binario (imagens de "
        "firmware de roteadores, IoT, dispositivos embedded), extrai os "
        "componentes individuais e calcula entropia para identificar regioes "
        "compactadas/criptografadas."
    ),
    (
        "Quando usar",
        "<b>Auditoria de dispositivo</b>:\n"
        "Voce baixou firmware do site do fabricante de um roteador ou camera "
        "IP. Quer saber o que tem dentro antes de instalar. binwalk revela: "
        "kernel Linux, filesystem SquashFS, certificados embarcados, etc.\n\n"
        "<b>Reverse engineering</b>:\n"
        "Voce comprou um dispositivo IoT e quer entender como funciona. "
        "Dump da flash → analise → encontra filesystem → monta → ve binarios "
        "+ scripts + configs.\n\n"
        "<b>Forensics</b>:\n"
        "Investigador acha um arquivo .bin suspeito. binwalk identifica "
        "rapidamente: e' um document Office? Imagem? Executavel? Container?\n\n"
        "<b>Validacao de integridade</b>:\n"
        "Apos extrair um firmware, voce pode comparar arquivos extraidos "
        "contra hashes conhecidos para detectar tampering."
    ),
    (
        "Tabs",
        "<b>Analisar</b>: detecta signatures (magic numbers de tipos de "
        "arquivo conhecidos). Equivalente a <tt>binwalk &lt;arquivo&gt;</tt>. "
        "Listagem com offset (decimal e hex) + tipo identificado.\n\n"
        "<b>Extrair</b>: roda <tt>binwalk -e</tt> para extrair todos os "
        "arquivos identificados num diretorio de saida. Cria subdir "
        "<tt>_&lt;basename&gt;.extracted/</tt>.\n\n"
        "<b>Entropia</b>: calcula entropia ao longo do arquivo. Mostra "
        "edges (pontos de mudanca brusca). Util pra localizar regioes "
        "criptografadas/compactadas vs. estruturadas."
    ),
    (
        "Conceitos importantes",
        "<b>Magic numbers</b>: sequencias de bytes no inicio de arquivos que "
        "identificam o tipo. Ex: <tt>FF D8 FF</tt> = JPEG; <tt>50 4B 03 04</tt> "
        "= ZIP; <tt>7F 45 4C 46</tt> = ELF. binwalk tem catalogo de centenas.\n\n"
        "<b>Entropia (Shannon)</b>: medida de imprevisibilidade. Calculada em "
        "blocos de bytes. Range 0-1 normalizada por binwalk.\n"
        "- ~0.0-0.3: padroes repetitivos (zeros, sequencias)\n"
        "- ~0.3-0.6: dados estruturados (codigo executavel, texto)\n"
        "- ~0.6-0.85: dados densos (imagens JPEG, audio MP3)\n"
        "- ~0.95+: compactado (ZIP, LZMA) ou criptografado (AES)\n\n"
        "<b>SquashFS</b>: filesystem read-only compactado, padrao em "
        "firmware embedded (roteadores Linux). Monta com "
        "<tt>sudo mount -t squashfs &lt;img&gt; /mnt</tt>.\n\n"
        "<b>JFFS2, UBIFS, CramFS</b>: outros filesystems comuns em embedded."
    ),
    (
        "Exemplo de workflow",
        "Voce baixou <tt>router-firmware.bin</tt> (50 MB) do site do "
        "fabricante. Suspeita de backdoor.\n\n"
        "1. Aba <i>Analisar</i> → <tt>router-firmware.bin</tt>\n"
        "   binwalk detecta: uImage, Linux kernel, SquashFS filesystem, "
        "JFFS2 partition.\n\n"
        "2. Aba <i>Entropia</i> → mesmo arquivo\n"
        "   Edges em offsets que correspondem aos limites do filesystem. "
        "Regiao 0x80000-0x800000 tem entropia ~0.99 = SquashFS comprimido.\n\n"
        "3. Aba <i>Extrair</i> → arquivo + outdir <tt>~/router-fw/</tt>\n"
        "   Output: <tt>~/router-fw/_router-firmware.bin.extracted/</tt>\n"
        "   Dentro: <tt>kernel.img</tt>, <tt>squashfs-root/</tt> "
        "(filesystem montavel), <tt>jffs2.bin</tt>.\n\n"
        "4. Browse <tt>squashfs-root/</tt> → encontra <tt>bin/telnetd</tt>, "
        "<tt>etc/passwd</tt> com root sem senha → confirma backdoor.\n\n"
        "(Workflow padrao em research de IoT.)"
    ),
    (
        "Limitacoes conhecidas",
        "- Visualizacao grafica de entropia chega em v0.2. v0.1 mostra so "
        "edges (pontos de mudanca).\n"
        "- Sem <b>filesystem mounting</b> integrado. Apos extrair, voce "
        "monta manual <tt>sudo mount -t squashfs ... /mnt</tt>.\n"
        "- Extracao pode <b>falhar silenciosa</b> em firmware exotico. Output "
        "bruto do binwalk fica disponivel para debug.\n"
        "- binwalk usa muitas tools externas (unsquashfs, jefferson, etc.) — "
        "se nao instaladas, certos tipos nao extraem.\n"
        "- Sem <b>comparativo entre firmwares</b> (delta) — v0.3 alvo."
    ),
    (
        "LGPD e privacidade",
        "Analise e' 100% local. Nenhum dado e' enviado pra rede.\n\n"
        "Dispositivos IoT frequentemente coletam dados pessoais (gravacoes "
        "de camera, audio de assistente). Auditar o firmware antes de "
        "deploy num escritorio de advocacia ajuda a entender o que esses "
        "dispositivos realmente fazem com os dados — relevante pra LGPD."
    ),
    (
        "Uso etico",
        "Reverse engineering de firmware <b>geralmente e' legal</b> para fins "
        "de seguranca/research/interop. Mas atencao a:\n\n"
        "- <b>DMCA/EUCD</b>: extrair firmware para contornar DRM pode violar "
        "lei em alguns paises (mais relevante pros EUA/UE que Brasil).\n"
        "- <b>Contratos de licenca</b> (EULA) de fabricantes frequentemente "
        "proibem RE. Vinculo civil, nao criminal.\n"
        "- <b>Republicar</b> codigo proprietario extraido viola copyright.\n\n"
        "Para uso pessoal/educacional/security research, RE de firmware "
        "que voce comprou e' aceito amplamente."
    ),
    (
        "Saiba mais",
        "- <tt>man binwalk</tt>\n"
        "- Repositorio: https://github.com/ReFirmLabs/binwalk\n"
        "- Livro 'The IoT Hacker's Handbook' por Aditya Gupta\n"
        "- Curso pratico OWASP IoT Security\n"
        "- Comunidade: r/ReverseEngineering"
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
