"""Aba Sobre — manual didatico do Vigia Dashboard."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402


SECTIONS: list[tuple[str, str]] = [
    (
        "O que faz",
        "Dashboard de sistema em tempo real. Mostra <b>CPU</b>, "
        "<b>memoria</b>, <b>disco I/O</b>, <b>rede</b> e <b>processos</b> "
        "com graficos visuais — sem precisar abrir terminal.\n\n"
        "Substitui o uso de <tt>htop</tt>, <tt>btop</tt>, <tt>glances</tt>, "
        "<tt>iotop</tt> e <tt>iftop</tt> em uma UI nativa libadwaita.\n\n"
        "Refresh a cada <b>1 segundo</b> (CPU, RAM, disco, rede) ou "
        "<b>2 segundos</b> (processos). Historico de 60 segundos mantido em "
        "memoria — sem persistencia em disco."
    ),
    (
        "Tabs",
        "<b>Visao Geral</b>: hostname, kernel, uptime, load average, e "
        "sparklines de CPU/RAM/Rede dos ultimos 60s. Topo de processos. "
        "Uso de disco por mountpoint.\n\n"
        "<b>Recursos</b>: graficos detalhados.\n"
        "- CPU: linha por core + frequencia atual + temperatura\n"
        "- Memoria: barra segmentada (usada/cache/livre) + swap\n"
        "- Disco I/O: read e write em MB/s\n"
        "- Rede: RX/TX por interface\n\n"
        "<b>Processos</b>: top 30 por defaut, com filtros (search por nome, "
        "ordenacao, 'so meus'). Kill com confirmacao (SIGTERM ou SIGKILL). "
        "Processos de outros users requerem admin (pkexec)."
    ),
    (
        "Como ler os numeros",
        "<b>Load average (1/5/15 min)</b>: numero medio de processos na "
        "fila de execucao. Verde se &lt; 70% de N cores; amarelo 70-150%; "
        "vermelho &gt; 150%.\n\n"
        "<b>CPU%</b>: tempo do core nao-idle no ultimo intervalo. 100% = "
        "1 core saturado. Multi-core: pode passar de 100% no agregado.\n\n"
        "<b>Memoria 'usada' vs 'cache'</b>: o kernel usa RAM ociosa como "
        "cache de filesystem. Esse cache e' descartavel — quando app pede "
        "RAM, kernel libera cache. 'Usada' = total - available, ja "
        "considerando que cache pode ser liberado.\n\n"
        "<b>Temperatura</b>: maior valor entre todos os sensores de CPU. "
        "Verde &lt; 70°C; amarelo 70-85°C; vermelho &gt; 85°C (thermal "
        "throttling proximo)."
    ),
    (
        "De onde vem os dados",
        "Tudo de <tt>/proc</tt> e <tt>/sys</tt> — interfaces virtuais do "
        "kernel Linux. Leitura e' instantanea (1ms) e nao requer privilegios "
        "para a maioria.\n\n"
        "- <tt>/proc/stat</tt> — CPU times por core\n"
        "- <tt>/proc/meminfo</tt> — memoria\n"
        "- <tt>/proc/loadavg</tt> — load average\n"
        "- <tt>/proc/diskstats</tt> — I/O por device\n"
        "- <tt>/proc/net/dev</tt> — RX/TX por interface\n"
        "- <tt>/proc/&lt;pid&gt;/stat,status,statm,cmdline</tt> — processos\n"
        "- <tt>/sys/class/thermal/thermal_zone*/temp</tt> — temperatura\n"
        "- <tt>/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq</tt> — freq\n\n"
        "<b>Sem pacotes externos</b>: o que voce ja tem no kernel basta. "
        "Apenas <tt>lm_sensors</tt> opcional para sensores extras."
    ),
    (
        "Privilegio admin (pkexec)",
        "A maioria das operacoes nao precisa root:\n"
        "- Leitura de <tt>/proc</tt> e <tt>/sys</tt>: user pode\n"
        "- Listagem de processos: user ve todos (mas detalhes de outros "
        "users podem ser limitados pelo kernel)\n\n"
        "<b>Operacoes que pedem pkexec</b>:\n"
        "- Kill de processo de outro user ou do sistema\n\n"
        "<b>NUNCA</b> a tool roda totalmente como root — segue padrao do "
        "VigiaOS: pkexec opt-in apenas no momento da acao."
    ),
    (
        "Comandos manuais equivalentes (referencia)",
        "Pra quem quer comparar/aprender:\n\n"
        "- <tt>top</tt> ou <tt>htop</tt> — view geral parecida com Visao Geral\n"
        "- <tt>btop</tt> — interface moderna em TUI\n"
        "- <tt>free -h</tt> — info de RAM\n"
        "- <tt>vmstat 1</tt> — CPU + memoria + I/O cada 1s\n"
        "- <tt>iostat -x 1</tt> — I/O detalhado por device\n"
        "- <tt>iftop -i eth0</tt> — rede por interface\n"
        "- <tt>sensors</tt> — temperatura (precisa lm_sensors)\n"
        "- <tt>uptime</tt> — load avg + tempo ligado\n"
        "- <tt>nproc</tt> — numero de cores"
    ),
    (
        "Limitacoes conhecidas",
        "- Sem <b>historico persistente</b>: ao fechar a tool, dados "
        "somem. v0.3 vai persistir em SQLite.\n"
        "- Sem <b>alertas</b>: nao avisa se CPU passar de 95% por 1min. "
        "v0.2 alvo.\n"
        "- Refresh fixo em 1s/2s — sem opcao na UI ainda.\n"
        "- Temperatura: depende de <tt>/sys/class/thermal</tt>. Algumas "
        "VMs nao tem (mostra 'nao disponivel').\n"
        "- Sem <b>per-process I/O</b> (iotop-style). v0.2 alvo.\n"
        "- Sem <b>per-process bandwidth</b> (nethogs-style). v0.2 alvo.\n"
        "- Sem <b>GPU monitoring</b>. Nvidia/AMD: usar nvtop por enquanto."
    ),
    (
        "Privacidade",
        "Tudo <b>100% local</b>. Nenhum dado e' enviado a rede.\n\n"
        "Dashboard nao registra historico em disco — ao fechar, tudo some "
        "(diferente de Activity Log ou Reports que persistem). Voce pode "
        "deixar aberto sem preocupacao com dados sensiveis aparecendo "
        "em arquivos."
    ),
    (
        "Saiba mais",
        "- <tt>man proc</tt> (capitulo 5 do manual)\n"
        "- Linux Kernel Documentation: Documentation/filesystems/proc.rst\n"
        "- Livro 'Systems Performance' por Brendan Gregg\n"
        "- USE Method (Utilization/Saturation/Errors) — http://brendangregg.com/usemethod.html"
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
