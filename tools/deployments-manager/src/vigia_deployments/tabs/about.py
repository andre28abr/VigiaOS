"""Aba Sobre — manual didatico sobre rpm-ostree deployments."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que são deployments",
        "Em sistemas Fedora Atomic (Silverblue, Kinoite, Bluefin, Bazzite, "
        "Aurora) o sistema operacional é <b>imutável</b>. Cada vez que você "
        "instala um pacote (<tt>rpm-ostree install</tt>) ou faz upgrade "
        "(<tt>rpm-ostree upgrade</tt>), o sistema cria um <b>novo deployment</b> "
        "— um snapshot completo da nova versão.\n\n"
        "O deployment anterior fica preservado como <b>rollback</b>. No menu "
        "do <b>GRUB</b> ao bootar, você pode escolher qual deployment usar.\n\n"
        "<i>Atomic</i>: ou a operação deu certo 100%, ou você volta pro estado "
        "anterior. Sem updates pela metade."
    ),
    (
        "Quantos deployments existem?",
        "Normalmente <b>2</b>: o atual (booted) + o anterior (rollback). "
        "Quando você faz <tt>rpm-ostree install</tt>, um terceiro aparece "
        "como <b>staged</b> (pending) — vira o atual no próximo boot.\n\n"
        "Você pode <b>pinnar</b> deployments adicionais (limite ~5 por causa "
        "do espaço em <tt>/boot</tt>). Deployments pinados NÃO são removidos "
        "automaticamente no upgrade."
    ),
    (
        "Status dos deployments",
        "<b>ATIVO</b> (verde): rodando agora. Não pode ser removido.\n\n"
        "<b>STAGED</b> (amarelo): pending. Vai virar ATIVO no próximo boot. "
        "Cleanup remove com <tt>cleanup -p</tt>.\n\n"
        "<b>ROLLBACK</b> (cinza): deployment anterior. Cleanup remove com "
        "<tt>cleanup -r</tt>. Geralmente o sistema preserva pra emergência.\n\n"
        "<b>PIN</b> (azul): protegido. NUNCA é removido automaticamente. "
        "Use pra preservar um estado conhecido como bom antes de mudanças "
        "arriscadas."
    ),
    (
        "Quando pinnar?",
        "Recomendado <b>pinnar</b> antes de:\n\n"
        "• Instalar pacote experimental (<tt>rpm-ostree install</tt>)\n"
        "• Upgrade major do Fedora (ex: 41 -> 42)\n"
        "• Rebase pra outra variant (Silverblue -> Kinoite)\n"
        "• Layer drivers proprietários (NVIDIA, etc.)\n\n"
        "Depois, se algo quebrar, você sabe que tem um estado bom pra "
        "voltar via <b>Reverter</b>."
    ),
    (
        "Cuidado com /boot",
        "A partição <tt>/boot</tt> em sistemas atômicos é pequena "
        "(geralmente 600MB-1GB). Cada deployment usa 100-200MB lá dentro "
        "(kernel + initramfs).\n\n"
        "Com 5+ deployments pinados, <tt>/boot</tt> pode encher e <b>impedir "
        "upgrades futuros</b>. Solução: cleanup periódico ou despinnar "
        "deployments antigos.\n\n"
        "A aba <b>Cleanup</b> mostra alerta amarelo (>70%) ou vermelho "
        "(>85%) e botão pra liberar espaço em 1 clique."
    ),
    (
        "Rollback vs reverter",
        "Os termos são usados quase como sinônimos no Vigia:\n\n"
        "• <b>Rollback automático</b>: GRUB oferece bootar deployment "
        "anterior se o atual não iniciar. Acontece sozinho.\n\n"
        "• <b>Reverter manual</b>: você escolhe via UI (esta tool) ou "
        "<tt>rpm-ostree rollback</tt>. Toma efeito no próximo boot. "
        "Pode ser revertido novamente (voltar pro que era antes)."
    ),
    (
        "Labels e notas (LGPD/audit)",
        "rpm-ostree identifica deployments por <b>checksum SHA-256</b> + "
        "timestamp. Não tem campo 'nome customizado'.\n\n"
        "O Vigia adiciona <b>label</b> e <b>notas multilinha</b> que ficam "
        "salvos LOCAL em <tt>~/.config/vigia-deployments/state.json</tt> "
        "com <tt>mode 0600</tt> (owner-only — LGPD).\n\n"
        "<b>Uso pra audit</b>: documentar contexto de cada deployment "
        "importante. Ex: <i>'Pré instalação do dnscrypt-proxy pro cliente "
        "X. Backup antes do audit semanal LGPD.'</i>"
    ),
    (
        "O que NÃO consegue fazer",
        "Limitações técnicas do rpm-ostree (não da tool):\n\n"
        "• <b>Criar snapshot manual</b> ('snapshot agora'): não existe. "
        "Deployments só nascem via <tt>install/upgrade/rebase</tt>. "
        "Workaround: faça um <tt>rpm-ostree install --idempotent</tt> com "
        "um pacote já instalado pra forçar um novo deployment.\n\n"
        "• <b>Renomear de verdade</b>: o label do Vigia é display only, "
        "não muda nada no rpm-ostree.\n\n"
        "• <b>Deletar deployment específico</b>: cleanup remove pending, "
        "rollback ou cache. Pra remover um pinado, primeiro despinne."
    ),
    (
        "LGPD e privacidade",
        "<b>100% offline</b>. Nenhum dado vai pra rede.\n\n"
        "<b>State local</b>: labels e notas em "
        "<tt>~/.config/vigia-deployments/state.json</tt> com mode 0600.\n\n"
        "<b>Operações elevadas</b>: usa <tt>pkexec</tt> (in-app polkit dialog). "
        "Nunca <tt>sudo</tt> ou shell escape.\n\n"
        "<b>Audit trail</b>: rpm-ostree mantém histórico completo de "
        "deployments com checksums. Combinado com notas + labels, você tem "
        "evidência de processo de mudanças (LGPD-friendly)."
    ),
    (
        "Saiba mais",
        "• <tt>man rpm-ostree</tt>, <tt>man ostree</tt>\n"
        "• Docs Silverblue: https://docs.fedoraproject.org/en-US/fedora-silverblue/\n"
        "• Background: https://www.ostree.io/"
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
