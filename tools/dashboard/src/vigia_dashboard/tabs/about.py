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
        "<b>memória</b>, <b>disco I/O</b>, <b>rede</b> e <b>processos</b> "
        "com gráficos visuais — sem precisar abrir terminal.\n\n"
        "Substitui o uso de <tt>htop</tt>, <tt>btop</tt>, <tt>glances</tt>, "
        "<tt>iotop</tt> e <tt>iftop</tt> em uma UI nativa libadwaita.\n\n"
        "Refresh a cada <b>1 segundo</b> (CPU, RAM, disco, rede) ou "
        "<b>2 segundos</b> (processos). Histórico de 60 segundos mantido em "
        "memória — sem persistência em disco."
    ),
    (
        "Tabs",
        "<b>Visão Geral</b>: hostname, kernel, uptime, load average, e "
        "sparklines de CPU/RAM/Rede dos últimos 60s. Topo de processos. "
        "Uso de disco por mountpoint.\n\n"
        "<b>Recursos</b>: gráficos detalhados.\n"
        "- CPU: linha por core + frequência atual + temperatura\n"
        "- Memória: barra segmentada (usada/cache/livre) + swap\n"
        "- Disco I/O: read e write em MB/s\n"
        "- Rede: RX/TX por interface\n\n"
        "<b>Processos</b>: top 30 por defaut, com filtros (search por nome, "
        "ordenação, 'só meus'). Cada processo mostra <b>I/O em MB/s</b> e "
        "<b>número de conexões</b> (v0.2). Kill com confirmação (SIGTERM "
        "ou SIGKILL). Processos de outros users requerem admin (pkexec).\n\n"
        "<b>Alertas</b> (v0.2): regras configuráveis tipo \"CPU &gt; 95% "
        "por 60s\" disparam notificação desktop. Persistência em "
        "<tt>~/.config/vigia/dashboard-alerts.json</tt> (mode 0600).\n\n"
        "<b>Sobre</b>: este manual."
    ),
    (
        "v0.2 — Per-process I/O e conexões",
        "<b>Per-process I/O</b>: leitura de <tt>/proc/&lt;pid&gt;/io</tt> "
        "campos <tt>read_bytes</tt> e <tt>write_bytes</tt> (cumulativos). "
        "Delta vs leitura anterior → MB/s por PID. Substitui o uso de "
        "<tt>iotop</tt>. Limitação: outros users só se rodando com "
        "<tt>CAP_SYS_PTRACE</tt> ou como root.\n\n"
        "<b>Per-process conexões</b>: parse de <tt>/proc/net/tcp</tt>, "
        "<tt>/proc/net/tcp6</tt>, <tt>/proc/net/udp</tt>, <tt>/proc/net/udp6</tt> "
        "→ mapa <i>inode → tipo de conexão</i>. Para cada PID, lê "
        "<tt>/proc/&lt;pid&gt;/fd/*</tt> (symbolic links como "
        "<tt>socket:[12345]</tt>) → match inode → conta.\n\n"
        "Estados TCP exibidos: ESTABLISHED, LISTEN, UDP. Bytes/s por "
        "processo exigiria eBPF (alvo v0.3)."
    ),
    (
        "v0.2 — Alertas configuráveis",
        "Regras tipo <tt>metric op threshold</tt> + <tt>duration</tt> + "
        "<tt>cooldown</tt>. Quando uma regra dispara, recebe "
        "<b>notificação desktop</b> via <tt>Gio.Notification</tt>.\n\n"
        "<b>Métricas suportadas</b>:\n"
        "- cpu_pct (0-100)\n"
        "- mem_pct (0-100)\n"
        "- swap_pct (0-100)\n"
        "- load_1 (load average 1min, raw)\n"
        "- cpu_temp_c (Celsius)\n"
        "- disk_pct_root, disk_pct_home (%)\n\n"
        "<b>Operadores</b>: <tt>gt</tt> (&gt;) e <tt>lt</tt> (&lt;).\n\n"
        "<b>Duration</b>: tempo mínimo acima do threshold antes de "
        "disparar (evita falsos positivos por picos isolados).\n\n"
        "<b>Cooldown</b>: tempo mínimo entre disparos consecutivos do "
        "mesmo alerta (evita spam de notificação para o mesmo problema)."
    ),
    (
        "Como ler os números",
        "<b>Load average (1/5/15 min)</b>: número médio de processos na "
        "fila de execução. Verde se &lt; 70% de N cores; amarelo 70-150%; "
        "vermelho &gt; 150%.\n\n"
        "<b>CPU%</b>: tempo do core não-idle no último intervalo. 100% = "
        "1 core saturado. Multi-core: pode passar de 100% no agregado.\n\n"
        "<b>Memória 'usada' vs 'cache'</b>: o kernel usa RAM ociosa como "
        "cache de filesystem. Esse cache é descartável — quando app pede "
        "RAM, kernel libera cache. 'Usada' = total - available, já "
        "considerando que cache pode ser liberado.\n\n"
        "<b>Temperatura</b>: maior valor entre todos os sensores de CPU. "
        "Verde &lt; 70°C; amarelo 70-85°C; vermelho &gt; 85°C (thermal "
        "throttling próximo)."
    ),
    (
        "De onde vem os dados",
        "Tudo de <tt>/proc</tt> e <tt>/sys</tt> — interfaces virtuais do "
        "kernel Linux. Leitura é instantânea (1ms) e não requer privilégios "
        "para a maioria.\n\n"
        "- <tt>/proc/stat</tt> — CPU times por core\n"
        "- <tt>/proc/meminfo</tt> — memória\n"
        "- <tt>/proc/loadavg</tt> — load average\n"
        "- <tt>/proc/diskstats</tt> — I/O por device\n"
        "- <tt>/proc/net/dev</tt> — RX/TX por interface\n"
        "- <tt>/proc/&lt;pid&gt;/stat,status,statm,cmdline</tt> — processos\n"
        "- <tt>/sys/class/thermal/thermal_zone*/temp</tt> — temperatura\n"
        "- <tt>/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq</tt> — freq\n\n"
        "<b>Sem pacotes externos</b>: o que você já tem no kernel basta. "
        "Apenas <tt>lm_sensors</tt> opcional para sensores extras."
    ),
    (
        "Privilégio admin (pkexec)",
        "A maioria das operações não precisa root:\n"
        "- Leitura de <tt>/proc</tt> e <tt>/sys</tt>: user pode\n"
        "- Listagem de processos: user vê todos (mas detalhes de outros "
        "users podem ser limitados pelo kernel)\n\n"
        "<b>Operações que pedem pkexec</b>:\n"
        "- Kill de processo de outro user ou do sistema\n\n"
        "<b>NUNCA</b> a tool roda totalmente como root — segue padrão do "
        "VigiaOS: pkexec opt-in apenas no momento da ação."
    ),
    (
        "Comandos manuais equivalentes (referência)",
        "Pra quem quer comparar/aprender:\n\n"
        "- <tt>top</tt> ou <tt>htop</tt> — view geral parecida com Visão Geral\n"
        "- <tt>btop</tt> — interface moderna em TUI\n"
        "- <tt>free -h</tt> — info de RAM\n"
        "- <tt>vmstat 1</tt> — CPU + memória + I/O cada 1s\n"
        "- <tt>iostat -x 1</tt> — I/O detalhado por device\n"
        "- <tt>iftop -i eth0</tt> — rede por interface\n"
        "- <tt>sensors</tt> — temperatura (precisa lm_sensors)\n"
        "- <tt>uptime</tt> — load avg + tempo ligado\n"
        "- <tt>nproc</tt> — número de cores"
    ),
    (
        "Limitações conhecidas",
        "- Sem <b>histórico persistente</b>: ao fechar a tool, dados "
        "somem. v0.3 vai persistir em SQLite.\n"
        "- Sem <b>alertas</b>: não avisa se CPU passar de 95% por 1min. "
        "v0.2 alvo.\n"
        "- Refresh fixo em 1s/2s — sem opção na UI ainda.\n"
        "- Temperatura: depende de <tt>/sys/class/thermal</tt>. Algumas "
        "VMs não têm (mostra 'não disponível').\n"
        "- Sem <b>per-process I/O</b> (iotop-style). v0.2 alvo.\n"
        "- Sem <b>per-process bandwidth</b> (nethogs-style). v0.2 alvo.\n"
        "- Sem <b>GPU monitoring</b>. Nvidia/AMD: usar nvtop por enquanto."
    ),
    (
        "Privacidade",
        "Tudo <b>100% local</b>. Nenhum dado é enviado à rede.\n\n"
        "Dashboard não registra histórico em disco — ao fechar, tudo some "
        "(diferente de Activity Log ou Reports que persistem). Você pode "
        "deixar aberto sem preocupação com dados sensíveis aparecendo "
        "em arquivos."
    ),
    (
        "Saiba mais",
        "- <tt>man proc</tt> (capítulo 5 do manual)\n"
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
