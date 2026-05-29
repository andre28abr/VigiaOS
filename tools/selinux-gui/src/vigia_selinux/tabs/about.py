"""Aba Sobre — manual didatico do Vigia SELinux Manager."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Substituto visual do <tt>system-config-selinux</tt> antigo (GTK2). "
        "<b>6 tabs</b> cobrem as operações essenciais do dia-a-dia com "
        "SELinux:\n\n"
        "- <b>Status</b>: ver/mudar modo (Enforcing/Permissive/Disabled) "
        "tanto runtime quanto persistente\n"
        "- <b>Booleans</b>: ~300 toggles com descrições pt-BR\n"
        "- <b>Denials</b>: lista de AVC blocks recentes + gerador automático "
        "de policy via <tt>audit2allow</tt>\n"
        "- <b>Files</b>: <tt>restorecon</tt> em um path (resolve 90% dos "
        "'movi arquivo e parou de funcionar')\n"
        "- <b>Network</b>: port mappings (read-only v0.2)\n"
        "- <b>Processes</b>: contextos SELinux dos processos ativos"
    ),
    (
        "Como usar",
        "<b>Cenário 1 — Serviço não funciona após mudança</b>:\n"
        "1. Vá para a aba <i>Denials</i> e clique 'Carregar denials'\n"
        "2. Ache o denial relacionado ao seu app (filtra por <tt>comm</tt>)\n"
        "3. Clique <i>Gerar</i> ao lado do denial para ver a policy sugerida\n"
        "4. Aplique a policy via terminal (instruções no dialog)\n\n"
        "<b>Cenário 2 — Habilitar boolean conhecido</b>:\n"
        "1. Aba <i>Booleans</i>, busca pelo nome (ex: <tt>httpd_can_network_connect</tt>)\n"
        "2. Lê a descrição pt-BR\n"
        "3. Toggle on/off — muda imediatamente E persiste via <tt>setsebool -P</tt>\n\n"
        "<b>Cenário 3 — Mudei arquivo de lugar e quebrou</b>:\n"
        "1. Aba <i>Files</i>, digita o path\n"
        "2. Marca <i>Recursivo</i> + <i>Verbose</i>\n"
        "3. <i>Restaurar contextos</i> — pede senha admin"
    ),
    (
        "Conceitos importantes",
        "<b>SELinux</b> (Security-Enhanced Linux) é um MAC framework — "
        "controla quais processos podem fazer o que, mesmo sendo root. "
        "Cada arquivo e processo tem um <i>contexto</i> tipo "
        "<tt>system_u:object_r:httpd_sys_content_t:s0</tt>.\n\n"
        "<b>Modos</b>:\n"
        "- <i>Enforcing</i>: SELinux bloqueia o que não for permitido\n"
        "- <i>Permissive</i>: SELinux apenas LOGA o que bloquearia (debug)\n"
        "- <i>Disabled</i>: SELinux completamente desligado (NÃO recomendado)\n\n"
        "<b>Booleans</b>: flags pré-definidas pelos packagers que ligam/"
        "desligam permissões específicas sem editar policy. Ex: "
        "<tt>httpd_can_network_connect=on</tt> permite Apache fazer conexões."
    ),
    (
        "Limitações conhecidas",
        "- Booleans <i>persistent</i> recompilam a policy — pode levar "
        "vários segundos por toggle\n"
        "- <i>Files</i> tab roda <tt>restorecon</tt> sync — em árvores "
        "grandes pode levar minutos\n"
        "- <i>Network</i> e <i>Processes</i> são read-only nesta versão "
        "(edição via <tt>semanage port</tt> em v0.3)"
    ),
    (
        "Saiba mais",
        "- <tt>man selinux</tt>, <tt>man semanage</tt>, <tt>man audit2allow</tt>\n"
        "- Fedora SELinux User Guide: https://docs.fedoraproject.org/en-US/"
        "quick-docs/selinux-getting-started/\n"
        "- <tt>sealert</tt> (no pacote setroubleshoot) — alertas detalhados"
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
