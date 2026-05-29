"""Backend Dashboard: le /proc, /sys e processos.

Sem subprocess para a maioria das metricas (tudo via /proc — kernel
interface user-readable). pkexec apenas para 'kill' de processos
de outros users.

API publica:
- get_system_info() -> SystemInfo
- get_cpu_snapshot(prev) -> CpuSnapshot   (per-core %, frequencia, temp)
- get_mem_snapshot() -> MemSnapshot       (total, used, free, cache, swap)
- get_disk_snapshot(prev) -> DiskSnapshot (mountpoints + I/O por device)
- get_net_snapshot(prev) -> NetSnapshot   (RX/TX por interface)
- list_processes() -> list[ProcessInfo]
- kill_process(pid, signal=15) -> (ok, err)
- get_load_avg() -> tuple[float, float, float]
"""

from __future__ import annotations

import os
import pwd
import re
import shutil
import signal as _signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================
# Dataclasses
# ============================================================


@dataclass
class SystemInfo:
    hostname: str = ""
    kernel: str = ""
    distro: str = ""
    uptime_sec: int = 0
    boot_time_epoch: int = 0
    users_logged: int = 0
    n_cpus: int = 1


@dataclass
class CpuTimes:
    """Tempos cumulativos por core (user+nice+system+idle+iowait+...).

    Usado como 'prev' na chamada seguinte para calcular delta.
    """
    timestamp: float = 0.0
    # Lista de tuples: (user, nice, system, idle, iowait, irq, softirq, steal)
    # cores[0] = total agregado; cores[1..] = cores individuais
    cores: list[tuple[int, ...]] = field(default_factory=list)


@dataclass
class CpuSnapshot:
    """Snapshot com delta calculado vs CpuTimes anterior."""
    times: CpuTimes = field(default_factory=CpuTimes)
    # percentages por core (0-100); index 0 = total agregado
    per_core_pct: list[float] = field(default_factory=list)
    # global %
    total_pct: float = 0.0
    # frequencia atual em MHz (media dos cores)
    freq_mhz: float = 0.0
    # temperatura em Celsius (None se nao disponivel)
    temp_c: float | None = None


@dataclass
class MemSnapshot:
    total_kb: int = 0
    free_kb: int = 0
    available_kb: int = 0      # MemAvailable — best estimate de "livre" real
    buffers_kb: int = 0
    cached_kb: int = 0
    used_kb: int = 0           # total - available
    swap_total_kb: int = 0
    swap_free_kb: int = 0
    swap_used_kb: int = 0


@dataclass
class DiskUsage:
    mountpoint: str
    device: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


@dataclass
class DiskIo:
    """Cumulativo desde boot (sectors_read/written x 512). Calculamos delta."""
    timestamp: float = 0.0
    # device -> (sectors_read, sectors_written)
    devices: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class DiskSnapshot:
    io: DiskIo = field(default_factory=DiskIo)
    # device -> (MB/s read, MB/s write)
    rates: dict[str, tuple[float, float]] = field(default_factory=dict)
    mounts: list[DiskUsage] = field(default_factory=list)


@dataclass
class NetIo:
    timestamp: float = 0.0
    # interface -> (rx_bytes, tx_bytes)
    ifaces: dict[str, tuple[int, int]] = field(default_factory=dict)


@dataclass
class NetSnapshot:
    io: NetIo = field(default_factory=NetIo)
    # interface -> (MB/s rx, MB/s tx)
    rates: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class ProcessInfo:
    pid: int
    user: str
    cpu_pct: float
    mem_pct: float
    rss_kb: int
    comm: str
    cmdline: str
    state: str         # R, S, D, Z, T
    nice: int = 0
    # v0.2 — Per-process I/O (de /proc/<pid>/io, calculado vs prev call)
    read_mbs: float = 0.0
    write_mbs: float = 0.0
    # v0.2 — Per-process conexoes (de /proc/<pid>/fd/* + /proc/net/tcp{,6}/udp{,6})
    n_tcp_established: int = 0
    n_tcp_listen: int = 0
    n_udp: int = 0


# ============================================================
# System info
# ============================================================


_SYSTEM_INFO_CACHE: SystemInfo | None = None
_DISTRO_CACHE: str | None = None


def _read_distro() -> str:
    global _DISTRO_CACHE
    if _DISTRO_CACHE is not None:
        return _DISTRO_CACHE
    p = Path("/etc/os-release")
    pretty = ""
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    pretty = line.split("=", 1)[1].strip().strip('"')
                    break
    except OSError:
        pretty = "Linux"
    _DISTRO_CACHE = pretty or "Linux"
    return _DISTRO_CACHE


_USERS_LOGGED_CACHE: tuple[float, int] = (0.0, 0)
_USERS_LOGGED_TTL_SEC = 30.0


def _count_logged_users() -> int:
    """Conta usuarios logados (lendo /proc/*/loginuid).

    PERF: cache TTL 30s — antes esta funcao abria ~200 files a cada
    call do Overview (1Hz). users_logged muda raramente (login/logout
    eh evento ocasional), 30s de stale e' aceitavel.
    """
    global _USERS_LOGGED_CACHE
    now = time.time()
    cached_at, cached_n = _USERS_LOGGED_CACHE
    if now - cached_at < _USERS_LOGGED_TTL_SEC:
        return cached_n

    seen = set()
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                with open(pid_dir / "loginuid", "r") as f:
                    uid = f.read().strip()
                if uid and uid != "4294967295":  # -1 (no login)
                    seen.add(uid)
            except (OSError, PermissionError):
                continue
    except OSError:
        pass

    _USERS_LOGGED_CACHE = (now, len(seen))
    return len(seen)


def get_system_info() -> SystemInfo:
    """Coleta informacoes estaticas + uptime (dinamico)."""
    global _SYSTEM_INFO_CACHE
    if _SYSTEM_INFO_CACHE is None:
        info = SystemInfo()
        try:
            with open("/proc/sys/kernel/hostname") as f:
                info.hostname = f.read().strip()
        except OSError:
            info.hostname = "?"
        try:
            with open("/proc/sys/kernel/osrelease") as f:
                info.kernel = f.read().strip()
        except OSError:
            info.kernel = "?"
        info.distro = _read_distro()
        info.n_cpus = os.cpu_count() or 1
        _SYSTEM_INFO_CACHE = info

    info = _SYSTEM_INFO_CACHE
    # Dinamicos
    try:
        with open("/proc/uptime", "r") as f:
            info.uptime_sec = int(float(f.read().split()[0]))
    except OSError:
        info.uptime_sec = 0
    info.boot_time_epoch = int(time.time()) - info.uptime_sec
    info.users_logged = _count_logged_users()
    return info


def get_load_avg() -> tuple[float, float, float]:
    try:
        with open("/proc/loadavg", "r") as f:
            parts = f.read().split()
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except (OSError, ValueError, IndexError):
        return (0.0, 0.0, 0.0)


# ============================================================
# CPU
# ============================================================


def _read_cpu_times() -> CpuTimes:
    """Le /proc/stat e retorna tempos cumulativos por core."""
    times = CpuTimes(timestamp=time.time())
    try:
        with open("/proc/stat", "r") as f:
            for line in f:
                if not line.startswith("cpu"):
                    continue
                parts = line.split()
                # parts[0] = "cpu" (total) ou "cpu0", "cpu1", ...
                vals = tuple(int(x) for x in parts[1:8])  # user nice sys idle iowait irq softirq
                times.cores.append(vals)
                if not parts[0].startswith("cpu") or len(parts[0]) > 6:
                    break
    except OSError:
        pass
    return times


def _read_cpu_freq() -> float:
    """Le frequencia atual media (MHz) — /proc/cpuinfo ou /sys."""
    freqs = []
    # Tenta /sys/devices/.../cpufreq/scaling_cur_freq primeiro (kHz)
    try:
        for p in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq"):
            try:
                val = int(p.read_text().strip())
                freqs.append(val / 1000.0)  # kHz → MHz
            except (OSError, ValueError):
                continue
    except OSError:
        pass

    if freqs:
        return sum(freqs) / len(freqs)

    # Fallback: /proc/cpuinfo
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("cpu MHz"):
                    val = float(line.split(":", 1)[1].strip())
                    freqs.append(val)
    except (OSError, ValueError):
        pass

    return sum(freqs) / len(freqs) if freqs else 0.0


def _read_cpu_temp() -> float | None:
    """Tenta ler temperatura da CPU. /sys/class/thermal/."""
    candidates = []
    try:
        for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
            try:
                # Filtra zonas de CPU (tipo contem 'cpu' ou 'x86_pkg' ou 'coretemp')
                type_path = zone / "type"
                if not type_path.exists():
                    continue
                z_type = type_path.read_text().strip().lower()
                if any(k in z_type for k in ("cpu", "x86", "core", "k10", "package")):
                    temp_path = zone / "temp"
                    val = int(temp_path.read_text().strip())
                    candidates.append(val / 1000.0)  # millidegree → degree
            except (OSError, ValueError):
                continue
    except OSError:
        pass

    if candidates:
        return max(candidates)  # maior (mais quente)

    # Fallback: /sys/class/hwmon/
    try:
        for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
            try:
                name_p = hwmon / "name"
                if not name_p.exists():
                    continue
                name = name_p.read_text().strip().lower()
                if name in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
                    for t_file in hwmon.glob("temp*_input"):
                        try:
                            val = int(t_file.read_text().strip())
                            candidates.append(val / 1000.0)
                        except (OSError, ValueError):
                            continue
            except (OSError, ValueError):
                continue
    except OSError:
        pass

    return max(candidates) if candidates else None


def get_cpu_snapshot(prev: CpuTimes | None = None) -> CpuSnapshot:
    """Calcula snapshot atual vs prev (None na primeira chamada)."""
    snapshot = CpuSnapshot()
    snapshot.times = _read_cpu_times()
    snapshot.freq_mhz = _read_cpu_freq()
    snapshot.temp_c = _read_cpu_temp()

    if prev is None or not prev.cores or len(prev.cores) != len(snapshot.times.cores):
        # Primeira chamada — sem delta
        snapshot.per_core_pct = [0.0] * len(snapshot.times.cores)
        snapshot.total_pct = 0.0
        return snapshot

    for i, (curr, prv) in enumerate(zip(snapshot.times.cores, prev.cores)):
        total_curr = sum(curr)
        total_prv = sum(prv)
        idle_curr = curr[3] + (curr[4] if len(curr) > 4 else 0)  # idle + iowait
        idle_prv = prv[3] + (prv[4] if len(prv) > 4 else 0)
        total_delta = total_curr - total_prv
        idle_delta = idle_curr - idle_prv
        if total_delta <= 0:
            pct = 0.0
        else:
            pct = max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0))
        snapshot.per_core_pct.append(pct)

    snapshot.total_pct = snapshot.per_core_pct[0] if snapshot.per_core_pct else 0.0
    return snapshot


# ============================================================
# Memory
# ============================================================


def get_mem_snapshot() -> MemSnapshot:
    snapshot = MemSnapshot()
    try:
        with open("/proc/meminfo", "r") as f:
            fields = {}
            for line in f:
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                val_str = parts[1].strip().split()[0]
                try:
                    fields[key] = int(val_str)
                except ValueError:
                    continue
    except OSError:
        return snapshot

    snapshot.total_kb = fields.get("MemTotal", 0)
    snapshot.free_kb = fields.get("MemFree", 0)
    snapshot.available_kb = fields.get("MemAvailable", snapshot.free_kb)
    snapshot.buffers_kb = fields.get("Buffers", 0)
    snapshot.cached_kb = fields.get("Cached", 0) + fields.get("SReclaimable", 0)
    snapshot.used_kb = max(0, snapshot.total_kb - snapshot.available_kb)

    snapshot.swap_total_kb = fields.get("SwapTotal", 0)
    snapshot.swap_free_kb = fields.get("SwapFree", 0)
    snapshot.swap_used_kb = max(0, snapshot.swap_total_kb - snapshot.swap_free_kb)

    return snapshot


# ============================================================
# Disk
# ============================================================


def _read_diskstats() -> DiskIo:
    """Le /proc/diskstats. Retorna sectors_read e sectors_written por device."""
    io = DiskIo(timestamp=time.time())
    try:
        with open("/proc/diskstats", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                device = parts[2]
                # Ignora particoes (sda1, sda2, ...) — manter so device pai (sda, nvme0n1)
                if re.match(r"^(sd[a-z]+|nvme\d+n\d+|vd[a-z]+|mmcblk\d+)$", device) is None:
                    continue
                try:
                    sectors_read = int(parts[5])
                    sectors_written = int(parts[9])
                    io.devices[device] = (sectors_read, sectors_written)
                except ValueError:
                    continue
    except OSError:
        pass
    return io


def _read_mounts() -> list[DiskUsage]:
    """Le mountpoints relevantes (filtra tmpfs, /proc, etc.)."""
    out: list[DiskUsage] = []
    ignored_fs = {"tmpfs", "devtmpfs", "proc", "sysfs", "cgroup",
                  "cgroup2", "devpts", "mqueue", "debugfs", "tracefs",
                  "fusectl", "configfs", "ramfs", "hugetlbfs", "pstore",
                  "bpf", "autofs", "securityfs", "selinuxfs", "binfmt_misc",
                  "rpc_pipefs", "fuse.gvfsd-fuse", "fuse.portal"}

    try:
        with open("/proc/mounts", "r") as f:
            mounts = f.readlines()
    except OSError:
        return out

    seen_devices = set()
    for line in mounts:
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mountpoint, fstype = parts[0], parts[1], parts[2]
        if fstype in ignored_fs:
            continue
        if not device.startswith("/"):
            continue
        # Evita duplicatas (mesma device em mounts diferentes — bind mounts etc)
        if device in seen_devices:
            continue
        seen_devices.add(device)

        try:
            stat = os.statvfs(mountpoint)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - (stat.f_bfree * stat.f_frsize)
            if total == 0:
                continue
            out.append(DiskUsage(
                mountpoint=mountpoint,
                device=device,
                fstype=fstype,
                total_bytes=total,
                used_bytes=used,
                free_bytes=free,
            ))
        except (OSError, PermissionError):
            continue

    return out


def get_disk_snapshot(prev: DiskIo | None = None) -> DiskSnapshot:
    snapshot = DiskSnapshot()
    snapshot.io = _read_diskstats()
    snapshot.mounts = _read_mounts()

    if prev is None or not prev.devices:
        return snapshot

    dt = snapshot.io.timestamp - prev.timestamp
    if dt <= 0:
        return snapshot

    SECTOR_BYTES = 512
    for device, (sr, sw) in snapshot.io.devices.items():
        prev_vals = prev.devices.get(device)
        if prev_vals is None:
            continue
        prev_sr, prev_sw = prev_vals
        rd_bps = (sr - prev_sr) * SECTOR_BYTES / dt
        wr_bps = (sw - prev_sw) * SECTOR_BYTES / dt
        # Bytes/s → MB/s
        snapshot.rates[device] = (rd_bps / 1024 / 1024, wr_bps / 1024 / 1024)

    return snapshot


# ============================================================
# Network
# ============================================================


def _read_net_io() -> NetIo:
    io = NetIo(timestamp=time.time())
    try:
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()[2:]  # skip 2 header lines
    except OSError:
        return io

    for line in lines:
        if ":" not in line:
            continue
        iface, vals = line.split(":", 1)
        iface = iface.strip()
        # Ignora loopback (sempre)
        if iface == "lo":
            continue
        parts = vals.split()
        if len(parts) < 16:
            continue
        try:
            rx_bytes = int(parts[0])
            tx_bytes = int(parts[8])
            io.ifaces[iface] = (rx_bytes, tx_bytes)
        except ValueError:
            continue

    return io


def get_net_snapshot(prev: NetIo | None = None) -> NetSnapshot:
    snapshot = NetSnapshot()
    snapshot.io = _read_net_io()

    if prev is None or not prev.ifaces:
        return snapshot

    dt = snapshot.io.timestamp - prev.timestamp
    if dt <= 0:
        return snapshot

    for iface, (rx, tx) in snapshot.io.ifaces.items():
        prev_vals = prev.ifaces.get(iface)
        if prev_vals is None:
            continue
        prev_rx, prev_tx = prev_vals
        rx_bps = (rx - prev_rx) / dt
        tx_bps = (tx - prev_tx) / dt
        # bytes/s → MB/s
        snapshot.rates[iface] = (rx_bps / 1024 / 1024, tx_bps / 1024 / 1024)

    return snapshot


# ============================================================
# Processes
# ============================================================


# Cache user lookup (uid → name)
_USER_CACHE: dict[int, str] = {}


def _uid_to_name(uid: int) -> str:
    if uid in _USER_CACHE:
        return _USER_CACHE[uid]
    try:
        name = pwd.getpwuid(uid).pw_name
    except KeyError:
        name = str(uid)
    _USER_CACHE[uid] = name
    return name


# Cache de CPU time anterior por PID, para calcular % de CPU
_PROC_CPU_PREV: dict[int, tuple[int, float]] = {}  # pid → (total_time_ticks, snap_time)
# Cache de I/O bytes anterior por PID, para calcular MB/s (v0.2)
_PROC_IO_PREV: dict[int, tuple[int, int, float]] = {}  # pid → (read_bytes, write_bytes, snap_time)
_CLOCK_TICKS = os.sysconf(os.sysconf_names.get("SC_CLK_TCK", -1)) if hasattr(os, "sysconf_names") else 100
if _CLOCK_TICKS <= 0:
    _CLOCK_TICKS = 100


# ============================================================
# Per-process connections (v0.2)
# ============================================================


# PERF: cache de socket inodes (4 arquivos /proc/net/*) com TTL 1s.
# Sockets nao mudam de inode rapidamente — releitura a 1Hz e' suficiente.
# Sistemas com 500+ conexoes parseiam 2000 linhas/call sem cache.
_SOCK_INODES_CACHE: tuple[float, dict[int, str]] = (0.0, {})
_SOCK_INODES_TTL_SEC = 1.0


def _read_socket_inodes_to_conn() -> dict[int, str]:
    """Le /proc/net/tcp{,6}/udp{,6} e retorna mapa inode -> tipo.

    Tipos: 'tcp_established', 'tcp_listen', 'tcp_other', 'udp'.

    PERF: cacheado por 1s.
    """
    global _SOCK_INODES_CACHE
    now = time.time()
    cached_at, cached_map = _SOCK_INODES_CACHE
    if now - cached_at < _SOCK_INODES_TTL_SEC:
        return cached_map

    inode_to_type: dict[int, str] = {}

    # TCP states do kernel:
    # 01 ESTABLISHED, 02 SYN_SENT, 03 SYN_RECV, 04 FIN_WAIT1, 05 FIN_WAIT2,
    # 06 TIME_WAIT, 07 CLOSE, 08 CLOSE_WAIT, 09 LAST_ACK, 0A LISTEN, 0B CLOSING

    for path, proto in (("/proc/net/tcp", "tcp"),
                         ("/proc/net/tcp6", "tcp"),
                         ("/proc/net/udp", "udp"),
                         ("/proc/net/udp6", "udp")):
        try:
            with open(path, "r") as f:
                next(f, None)  # skip header
                for line in f:
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    try:
                        state = parts[3]
                        inode = int(parts[9])
                    except (ValueError, IndexError):
                        continue
                    if inode == 0:
                        continue
                    if proto == "tcp":
                        if state == "01":
                            inode_to_type[inode] = "tcp_established"
                        elif state == "0A":
                            inode_to_type[inode] = "tcp_listen"
                        else:
                            inode_to_type[inode] = "tcp_other"
                    else:
                        inode_to_type[inode] = "udp"
        except (OSError, PermissionError):
            continue

    _SOCK_INODES_CACHE = (now, inode_to_type)
    return inode_to_type


def _get_pid_sockets(pid: int) -> list[int]:
    """Le /proc/<pid>/fd/* e retorna lista de socket inodes do PID.

    /proc/<pid>/fd/N e' simbolic link tipo 'socket:[12345]'.
    """
    inodes: list[int] = []
    try:
        fd_dir = Path("/proc") / str(pid) / "fd"
        for entry in fd_dir.iterdir():
            try:
                target = os.readlink(str(entry))
                if target.startswith("socket:["):
                    # 'socket:[12345]' → 12345
                    inode_str = target[8:-1]
                    inodes.append(int(inode_str))
            except (OSError, ValueError):
                continue
    except (OSError, PermissionError):
        # Sem permissao em /proc/<pid>/fd/ (outro user e sem CAP_SYS_PTRACE)
        pass
    return inodes


def list_processes(include_connections: bool = True, include_io: bool = True) -> list[ProcessInfo]:
    """Lista processos ativos com %CPU calculado vs ultima call.

    Args:
        include_connections: se True, conta TCP/UDP por PID (v0.2).
                            Mais lento (le /proc/<pid>/fd/* para cada PID).
        include_io: se True, le /proc/<pid>/io e calcula MB/s vs ultima call (v0.2).
    """
    now = time.time()
    procs: list[ProcessInfo] = []

    mem_total_kb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_kb = int(line.split()[1])
                    break
    except (OSError, ValueError, IndexError):
        mem_total_kb = 1

    # Pre-carrega socket inodes uma vez (eficiente — varios PIDs reusam)
    inode_to_conn: dict[int, str] = {}
    if include_connections:
        inode_to_conn = _read_socket_inodes_to_conn()

    seen_pids: set[int] = set()

    try:
        pid_dirs = list(Path("/proc").iterdir())
    except OSError:
        return procs

    for pid_dir in pid_dirs:
        if not pid_dir.name.isdigit():
            continue
        pid = int(pid_dir.name)
        seen_pids.add(pid)

        try:
            # Read /proc/<pid>/stat — parsing tricky por causa de (comm)
            with open(pid_dir / "stat", "r") as f:
                stat = f.read()
            # comm pode ter espacos e parenteses; achar ultimo ')' como divisor
            l_paren = stat.find("(")
            r_paren = stat.rfind(")")
            if l_paren < 0 or r_paren < 0:
                continue
            comm = stat[l_paren + 1:r_paren]
            rest = stat[r_paren + 2:].split()
            # Indices (apos `)` + space, 0-based, man proc(5) field# - 3):
            # rest[0]=state, rest[11]=utime, rest[12]=stime,
            # rest[15]=priority, rest[16]=nice
            state = rest[0] if rest else "?"
            utime = int(rest[11]) if len(rest) > 11 else 0
            stime = int(rest[12]) if len(rest) > 12 else 0
            nice = int(rest[16]) if len(rest) > 16 else 0
            total_ticks = utime + stime

            # uid via /proc/<pid>/status
            uid = 0
            try:
                with open(pid_dir / "status", "r") as f:
                    for line in f:
                        if line.startswith("Uid:"):
                            uid = int(line.split()[1])
                            break
                        if line.startswith("VmRSS:"):
                            break  # Uid sempre vem antes; nao deveria chegar aqui
            except (OSError, ValueError):
                pass

            # RSS via /proc/<pid>/statm
            rss_kb = 0
            try:
                with open(pid_dir / "statm", "r") as f:
                    statm_parts = f.read().split()
                if len(statm_parts) >= 2:
                    rss_pages = int(statm_parts[1])
                    rss_kb = rss_pages * 4  # 4 KB / page
            except (OSError, ValueError):
                pass

            # cmdline
            cmdline = ""
            try:
                with open(pid_dir / "cmdline", "rb") as f:
                    raw = f.read()
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
                if not cmdline:
                    cmdline = f"[{comm}]"  # kernel thread
            except OSError:
                cmdline = comm

            # Calcula %CPU vs snap anterior
            cpu_pct = 0.0
            prev = _PROC_CPU_PREV.get(pid)
            if prev is not None:
                prev_ticks, prev_time = prev
                dt = now - prev_time
                if dt > 0:
                    cpu_pct = max(0.0, min(100.0,
                        (total_ticks - prev_ticks) / _CLOCK_TICKS / dt * 100.0
                    ))
            _PROC_CPU_PREV[pid] = (total_ticks, now)

            mem_pct = (rss_kb / mem_total_kb * 100.0) if mem_total_kb else 0.0

            # v0.2 — I/O de /proc/<pid>/io
            read_mbs = 0.0
            write_mbs = 0.0
            if include_io:
                try:
                    read_bytes = 0
                    write_bytes = 0
                    with open(pid_dir / "io", "r") as f:
                        for io_line in f:
                            if io_line.startswith("read_bytes:"):
                                read_bytes = int(io_line.split(":")[1].strip())
                            elif io_line.startswith("write_bytes:"):
                                write_bytes = int(io_line.split(":")[1].strip())
                    prev_io = _PROC_IO_PREV.get(pid)
                    if prev_io is not None:
                        prev_r, prev_w, prev_io_time = prev_io
                        dt = now - prev_io_time
                        if dt > 0:
                            read_mbs = max(0.0,
                                (read_bytes - prev_r) / dt / 1024 / 1024
                            )
                            write_mbs = max(0.0,
                                (write_bytes - prev_w) / dt / 1024 / 1024
                            )
                    _PROC_IO_PREV[pid] = (read_bytes, write_bytes, now)
                except (OSError, PermissionError, ValueError):
                    # /proc/<pid>/io requer CAP_SYS_PTRACE para outros users
                    pass

            # v0.2 — Conexoes: olha quais sockets do PID estao na tabela tcp/udp
            n_tcp_est = 0
            n_tcp_listen = 0
            n_udp = 0
            if include_connections and inode_to_conn:
                pid_sockets = _get_pid_sockets(pid)
                for inode in pid_sockets:
                    ctype = inode_to_conn.get(inode)
                    if ctype == "tcp_established":
                        n_tcp_est += 1
                    elif ctype == "tcp_listen":
                        n_tcp_listen += 1
                    elif ctype == "udp":
                        n_udp += 1

            procs.append(ProcessInfo(
                pid=pid,
                user=_uid_to_name(uid),
                cpu_pct=cpu_pct,
                mem_pct=mem_pct,
                rss_kb=rss_kb,
                comm=comm,
                cmdline=cmdline,
                state=state,
                nice=nice,
                read_mbs=read_mbs,
                write_mbs=write_mbs,
                n_tcp_established=n_tcp_est,
                n_tcp_listen=n_tcp_listen,
                n_udp=n_udp,
            ))
        except (OSError, ValueError, IndexError):
            continue

    # Limpa cache de PIDs que sumiram
    dead_pids = set(_PROC_CPU_PREV.keys()) - seen_pids
    for d in dead_pids:
        _PROC_CPU_PREV.pop(d, None)
        _PROC_IO_PREV.pop(d, None)

    return procs


def kill_process(pid: int, sig: int = _signal.SIGTERM) -> tuple[bool, str]:
    """Tenta matar processo. Se EPERM, tenta via pkexec.

    Retorna (ok, err_message).
    """
    if pid <= 0:
        return False, "PID inválido."
    try:
        os.kill(pid, sig)
        return True, ""
    except ProcessLookupError:
        return False, "Processo não existe mais."
    except PermissionError:
        # Tenta via pkexec
        if shutil.which("pkexec") is None:
            return False, "Sem permissão e pkexec não encontrado."
        sig_name = "TERM"
        if sig == _signal.SIGKILL:
            sig_name = "KILL"
        elif sig == _signal.SIGHUP:
            sig_name = "HUP"
        try:
            result = subprocess.run(
                ["pkexec", "kill", f"-{sig_name}", str(pid)],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode in (126, 127):
                return False, "Autenticação cancelada."
            if result.returncode != 0:
                return False, (result.stderr or result.stdout).strip()[:300]
            return True, ""
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, f"Erro pkexec: {e}"
    except OSError as e:
        return False, f"Erro do kernel: {e}"


# ============================================================
# Formatters
# ============================================================


def format_uptime(seconds: int) -> str:
    """123456 → '1d 10h 17m'."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    if days > 0:
        return f"{days}d {hours % 24}h {minutes % 60}m"
    if hours > 0:
        return f"{hours}h {minutes % 60}m"
    return f"{minutes}m"


def format_kb(kb: int) -> str:
    """KB → '12.3 GB' etc."""
    if kb >= 1024 * 1024:
        return f"{kb / 1024 / 1024:.1f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} KB"


def format_bytes(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024 ** 2:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b} B"


def format_mbps(mbps: float) -> str:
    """Mb/s pode ser 0.0001 ou 1234.56."""
    if mbps >= 1024:
        return f"{mbps / 1024:.1f} GB/s"
    if mbps >= 1:
        return f"{mbps:.1f} MB/s"
    if mbps >= 0.001:
        return f"{mbps * 1024:.0f} KB/s"
    return f"{mbps * 1024 * 1024:.0f} B/s"
