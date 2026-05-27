"""Aba Sobre — manual didatico do Vigia Rootkit Scanner."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Procura por <b>rootkits</b>, <b>backdoors</b> e <b>sinais de "
        "comprometimento</b> no seu sistema usando dois scanners classicos "
        "de Linux:\n\n"
        "- <b>chkrootkit</b> — rapido (~30s), faz checks especificos por "
        "binario (busca por assinaturas conhecidas em <tt>/bin</tt>, "
        "<tt>/sbin</tt>, modulos do kernel, interfaces de rede, etc.)\n"
        "- <b>Rootkit Hunter (rkhunter)</b> — completo (2-5min), 200+ "
        "checks: hashes de arquivos do sistema, permissoes, configs SSH, "
        "processos escondidos, suspicious files\n\n"
        "Os dois sao <b>complementares</b>. Rode periodicamente "
        "(ex: semanalmente) e olhe o Historico pra mudancas suspeitas."
    ),
    (
        "Como usar",
        "<b>Primeira vez</b>:\n"
        "1. Instale via <b>Vigia Tool Installer</b>:\n"
        "   - <tt>chkrootkit</tt> (categoria Auditoria)\n"
        "   - <tt>rkhunter</tt> (categoria Auditoria)\n"
        "2. Reinicie (rpm-ostree precisa reboot)\n\n"
        "<b>Rodar scan</b>:\n"
        "1. Aba <i>chkrootkit</i> ou <i>Rootkit Hunter</i>\n"
        "2. Clique <i>Iniciar scan</i>\n"
        "3. Digite senha admin (pkexec)\n"
        "4. Aguarde — output streama em tempo real\n"
        "5. Linhas em <span foreground='#fbbf24'>amarelo</span> = warnings, "
        "<span foreground='#f87171'>vermelho</span> = potencial infectado\n"
        "6. Resultado eh salvo no <i>Historico</i> automaticamente"
    ),
    (
        "O que sao rootkits?",
        "<b>Rootkit</b> = software malicioso que se esconde do sistema "
        "operacional pra manter acesso persistente. Tecnicas:\n\n"
        "- <b>Userland rootkit</b>: substitui binarios como <tt>ps</tt>, "
        "<tt>ls</tt>, <tt>netstat</tt> por versoes que escondem processos "
        "do atacante. chkrootkit eh especialista em achar isso (compara "
        "hashes/strings com versoes conhecidas maliciosas).\n\n"
        "- <b>Kernel rootkit (LKM)</b>: carrega modulo do kernel que "
        "intercepta syscalls. Muito mais dificil de detectar — rkhunter "
        "tenta via <tt>/proc</tt> consistency checks.\n\n"
        "- <b>Bootkit/UEFI</b>: persistencia em nivel pre-OS. Nao "
        "detectavel por esses scanners (precisa de boot integrity check)."
    ),
    (
        "Interpretando resultados",
        "<b>Limpo</b>: nenhum sinal detectado. Sistema parece OK.\n\n"
        "<b>Warning</b>: chkrootkit/rkhunter encontrou algo que merece "
        "atencao mas pode ser falso positivo. Causas comuns:\n"
        "- Arquivos modificados apos <tt>rpm-ostree upgrade</tt> "
        "(hashes mudaram legitimamente) → rode <tt>rkhunter --propupd</tt>\n"
        "- Modules do kernel proprietarios (NVIDIA, VirtualBox)\n"
        "- Configs SSH 'inseguras' que sao OK no seu contexto\n\n"
        "<b>Infected</b>: alta probabilidade de comprometimento. Acoes:\n"
        "1. Desconectar da rede\n"
        "2. Salvar o report (esta no Historico)\n"
        "3. Rodar AIDE (Vigia File Integrity) pra cruzar findings\n"
        "4. Considerar reinstalar o sistema (rootkit kernel-level "
        "raramente eh removivel com confianca)"
    ),
    (
        "Falsos positivos comuns",
        "<b>rkhunter</b> reclama de:\n"
        "- <tt>/dev/.udev</tt>, <tt>/dev/.initramfs</tt> → normais em "
        "sistemas modernos com systemd\n"
        "- <tt>/etc/.pwd.lock</tt>, <tt>/etc/.cron.deny</tt> → arquivos "
        "ocultos legitimos\n"
        "- <tt>SSH PermitRootLogin</tt> warning → checa <tt>sshd_config</tt> "
        "e ajuste pra <tt>prohibit-password</tt> se necessario\n"
        "- Hashes de binarios pos-upgrade → rode <tt>rkhunter --propupd</tt>\n\n"
        "<b>chkrootkit</b> pode dar falso positivo em:\n"
        "- Interfaces em modo promiscuous (Wireshark, libvirt)\n"
        "- Sistemas com containers Podman/Docker (LKM detection)"
    ),
    (
        "LGPD e privacidade",
        "<b>100% offline</b>: nenhum dado vai pra rede. Scanners trabalham "
        "localmente comparando arquivos com signatures que ja existem no "
        "sistema.\n\n"
        "<b>Reports protegidos</b>: arquivos JSON em "
        "<tt>~/.local/share/vigia-rootkit/scans/</tt> com mode 0600 "
        "(somente voce le). Diretorio com mode 0700.\n\n"
        "<b>Output dos scans</b> pode conter paths de arquivos do sistema "
        "(via 'suspicious files'). Eh OK manter local — eh evidencia "
        "valida pra LGPD."
    ),
    (
        "Limitacoes conhecidas",
        "- <b>Sem scheduled scans</b> via UI nesta v0.1. Use cron ou "
        "systemd timer manualmente.\n"
        "- <b>Sem botao de update do rkhunter</b> (planejado v0.2)\n"
        "- <b>Sem AIDE integration</b> direta — use Vigia File Integrity "
        "em separado pra hash baseline\n"
        "- <b>Rootkits avancados ja em uso</b> (kernel-level) podem "
        "esconder do scanner. Considere reboot em live USB pra scan "
        "definitivo."
    ),
    (
        "Saiba mais",
        "- <tt>man chkrootkit</tt>, <tt>man rkhunter</tt>\n"
        "- chkrootkit: http://www.chkrootkit.org\n"
        "- rkhunter: https://rkhunter.sourceforge.net\n"
        "- Comparativo: ferramentas como Tripwire/AIDE/OSSEC sao "
        "complementares (file integrity), nao substitutas\n"
        "- Para LGPD/compliance: agende scan semanal e mantenha "
        "Historico arquivado pelo menos 90 dias"
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
