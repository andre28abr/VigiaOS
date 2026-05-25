"""Aba Sobre — manual didatico do Vigia Antivirus."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Antivirus on-demand para Linux desktop usando o engine <b>ClamAV</b>. "
        "Escaneia arquivos e diretorios sob demanda, mantem a base de "
        "assinaturas atualizada e mostra findings em UI moderna.\n\n"
        "Substitui o <tt>clamtk</tt> (UI envelhecida, quebra com GTK4) com "
        "interface nativa libadwaita. Pensado para quem precisa rodar scan "
        "ocasional em arquivos baixados/recebidos — nao e' antivirus "
        "real-time (Linux desktop nao precisa de AV real-time como Windows)."
    ),
    (
        "Como usar",
        "<b>Antes do primeiro scan</b>:\n"
        "1. Va a aba <i>Base de dados</i>\n"
        "2. Clique <i>Atualizar base agora</i> — pede senha admin\n"
        "3. Aguarde 30-90s (download de ~250 MB de assinaturas)\n\n"
        "<b>Escanear arquivos</b>:\n"
        "1. Aba <i>Scan</i>\n"
        "2. Digite um caminho ou clique em um atalho (Home, Downloads, etc.)\n"
        "3. Clique <i>Iniciar scan</i>\n"
        "4. Findings aparecem na lista conforme detectados\n"
        "5. Veja resultado final no rodape (X arquivos, Y infectados)\n\n"
        "<b>Verificar historico</b>:\n"
        "1. Aba <i>Status</i> mostra ate 5 scans recentes\n"
        "2. Reports completos em <tt>~/.local/share/vigia-antivirus/</tt> "
        "com permissoes 0600 (so voce le)"
    ),
    (
        "O que ClamAV detecta",
        "ClamAV identifica:\n"
        "- <b>Malware Windows</b> (PE, .exe, .dll) — muito util pra escanear "
        "downloads antes de mandar pra clientes ou enviar por email\n"
        "- <b>Documentos com macros maliciosas</b> (Office, PDF)\n"
        "- <b>Shell scripts maliciosos</b>, exploits conhecidos\n"
        "- <b>Phishing kits</b> e cavalos-de-troia comuns\n\n"
        "<i>Nao detecta</i> ameacas zero-day nem APTs sofisticadas — para "
        "isso voce precisa EDRs comerciais. ClamAV e' baseline."
    ),
    (
        "Por que usar isso num Linux?",
        "Linux desktop raramente e' alvo de malware nativo, mas voce pode:\n\n"
        "- <b>Compartilhar arquivos</b> com usuarios Windows e nao querer "
        "passar virus adiante (ex: PDF infectado que voce baixou)\n"
        "- <b>Escritorio LGPD</b>: regulamento exige diligencia. Logs de "
        "scan periodico sao evidencia de processo de seguranca\n"
        "- <b>Servidor de arquivos</b> ou backup com material recebido de "
        "terceiros (clientes, parceiros)\n"
        "- <b>Maquina compartilhada</b> entre user e dev (testes com "
        "executaveis suspeitos isolados em VM)"
    ),
    (
        "Conceitos importantes",
        "<b>Base de assinaturas</b>: ~250 MB de fingerprints de malware "
        "conhecido. Atualizada via <tt>freshclam</tt>. Recomendado 1x/semana "
        "no minimo (idealmente diario via systemd timer).\n\n"
        "<b>clamscan vs clamdscan</b>:\n"
        "- <tt>clamscan</tt> (usado aqui): standalone, carrega base na "
        "memoria a cada scan (~30s overhead). Simples, sem daemon.\n"
        "- <tt>clamdscan</tt>: usa daemon <tt>clamd</tt> que mantem base "
        "pre-carregada. Scans sao instantaneos. Mais memoria residente.\n\n"
        "<b>Exit codes</b>: 0 = limpo, 1 = malware encontrado, 2 = erro "
        "interno. Vigia trata 0 e 1 como sucesso de execucao.\n\n"
        "<b>Falsos positivos</b>: ClamAV ocasionalmente alarma em packers "
        "legitimos (UPX) e PUAs. Confira sempre antes de deletar."
    ),
    (
        "Limitacoes conhecidas",
        "- Sem <b>quarentena visual</b> nesta v0.1. Apaga/move manual.\n"
        "- Sem <b>scheduled scans</b> via UI. Use <tt>systemctl enable "
        "clamav-clamonacc</tt> ou cron.\n"
        "- Sem <b>scan em background</b> com daemon. Forca uso do "
        "<tt>clamscan</tt> standalone.\n"
        "- <b>Sem real-time protection</b>. Linux desktop nao precisa.\n"
        "- Sem integracao com Activity Log (v0.3 alvo)."
    ),
    (
        "LGPD e privacidade",
        "<b>Reports sao locais</b>. Nenhum dado e' enviado pra nuvem. ClamAV "
        "trabalha 100% offline (base baixada do mirror).\n\n"
        "<b>Permissoes restritas</b>: reports em "
        "<tt>~/.local/share/vigia-antivirus/</tt> com mode 0600 (apenas "
        "voce le). Diretorio com mode 0700.\n\n"
        "<b>Conteudo dos arquivos</b>: ClamAV processa bytes mas nao "
        "transmite. Voce pode escanear documentos sensiveis com tranquilidade."
    ),
    (
        "Saiba mais",
        "- <tt>man clamscan</tt>, <tt>man freshclam</tt>\n"
        "- Site oficial: https://www.clamav.net\n"
        "- Comparativos: nao confunda com Norton/Kaspersky — ClamAV e' "
        "baseline, util pra escaneamento on-demand de arquivos\n"
        "- Documentacao: https://docs.clamav.net"
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
