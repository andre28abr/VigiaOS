"""Testes do parser de `ss -tunap` (vigia_netmon.backend).

Cobre o backend do netmon-gui, que e' headless (NAO importa gi/GTK):
- _parse_ss_output: extracao de process/pid via regex
  (\\("([^"]+)",pid=(\\d+)), fallback "?" sem privilegio, skip de header
  e de linhas truncadas, sockets IPv6.
- NetConnection.is_listening / is_established (logica real do dataclass).
- list_listening / list_established: coletor (subprocess.run) com
  monkeypatch devolvendo stdout fixo + checagem dos filtros.

Nao precisa de `ss` instalado nem de root. Todo subprocess e' monkeypatchado.
"""

from __future__ import annotations

from vigia_netmon import backend


# ============================================================
# Amostras realistas de `ss -tunap`
# ============================================================
#
# Colunas: Netid  State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port  Process
# (separadas por whitespace; o backend usa line.split(None, 6), max 7 campos,
# preservando a coluna Process que contem virgulas/parenteses).

HEADER = (
    "Netid State  Recv-Q Send-Q "
    "Local Address:Port    Peer Address:Port    Process"
)

# UDP UNCONN com info de processo (systemd-resolve). peer wildcard ":*".
UDP_RESOLVED = (
    'udp   UNCONN 0      0      '
    '127.0.0.54:53         0.0.0.0:*            '
    'users:(("systemd-resolve",pid=804,fd=12))'
)

# TCP ESTAB SEM info de processo (caso sem privilegio: coluna Process vazia).
TCP_ESTAB_NOPROC = (
    'tcp   ESTAB  0      0      '
    '192.168.1.5:43210     142.250.78.46:443'
)

# TCP LISTEN com processo. peer e' wildcard "0.0.0.0:*".
TCP_LISTEN = (
    'tcp   LISTEN 0      128    '
    '0.0.0.0:22            0.0.0.0:*            '
    'users:(("sshd",pid=1200,fd=3))'
)

# TCP TIME-WAIT (nem listening, nem established), sem processo.
TCP_TIMEWAIT = (
    'tcp   TIME-WAIT 0   0      '
    '192.168.1.5:50012     93.184.216.34:443'
)

# Socket IPv6: Netid 'tcp6', enderecos com '[::]' e '[::1]'.
TCP6_LISTEN = (
    'tcp6  LISTEN 0      128    '
    '[::]:443              [::]:*               '
    'users:(("nginx",pid=999,fd=6))'
)

TCP6_ESTAB = (
    'tcp6  ESTAB  0      0      '
    '[2001:db8::1]:54321   [2606:4700::1111]:443 '
    'users:(("firefox",pid=4242,fd=88))'
)

# Linha truncada (poucos campos) -> deve ser pulada (len(parts) < 6).
TRUNCATED = "tcp   ESTAB  0"


def _run_returns(stdout: str, returncode: int = 0):
    """Fabrica um substituto de subprocess.run com .returncode/.stdout."""

    class _FakeCompleted:
        def __init__(self) -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def _fake_run(cmd, *args, **kwargs):
        return _FakeCompleted()

    return _fake_run


def _patch_ss(monkeypatch, stdout: str, returncode: int = 0):
    """Faz `ss`/`pkexec` parecerem instalados e injeta stdout fixo."""
    monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/sbin/" + name)
    monkeypatch.setattr(backend.subprocess, "run", _run_returns(stdout, returncode))


# ============================================================
# _parse_ss_output: extracao de processo / pid
# ============================================================


class TestParseProcessInfo:
    def test_udp_with_process_extracts_name_and_pid(self):
        conns = backend._parse_ss_output(UDP_RESOLVED)
        assert len(conns) == 1
        c = conns[0]
        assert c.proto == "udp"
        assert c.state == "UNCONN"
        assert c.local_addr == "127.0.0.54:53"
        assert c.peer_addr == "0.0.0.0:*"
        assert c.process == "systemd-resolve"
        assert c.pid == "804"

    def test_tcp_estab_without_process_falls_back(self):
        # Sem privilegio a coluna Process vem vazia -> process/pid = "?".
        conns = backend._parse_ss_output(TCP_ESTAB_NOPROC)
        assert len(conns) == 1
        c = conns[0]
        assert c.proto == "tcp"
        assert c.state == "ESTAB"
        assert c.local_addr == "192.168.1.5:43210"
        assert c.peer_addr == "142.250.78.46:443"
        assert c.process == "?"
        assert c.pid == "?"

    def test_pid_is_string_type(self):
        # O dataclass declara pid: str — o regex captura como texto.
        c = backend._parse_ss_output(TCP_LISTEN)[0]
        assert isinstance(c.pid, str)
        assert c.pid == "1200"
        assert c.process == "sshd"

    def test_raw_line_preserved(self):
        c = backend._parse_ss_output(UDP_RESOLVED)[0]
        # raw e' a linha original (apos rstrip), com a info de processo inteira.
        assert 'users:(("systemd-resolve",pid=804,fd=12))' in c.raw


# ============================================================
# _parse_ss_output: skip de header e linhas invalidas
# ============================================================


class TestParseSkips:
    def test_header_is_skipped(self):
        assert backend._parse_ss_output(HEADER) == []

    def test_truncated_line_is_skipped(self):
        assert backend._parse_ss_output(TRUNCATED) == []

    def test_blank_lines_are_skipped(self):
        assert backend._parse_ss_output("\n   \n\n") == []

    def test_header_then_data(self):
        out = "\n".join([HEADER, UDP_RESOLVED, TCP_ESTAB_NOPROC])
        conns = backend._parse_ss_output(out)
        # header pulado, 2 linhas de dados parseadas.
        assert len(conns) == 2
        assert conns[0].process == "systemd-resolve"
        assert conns[1].process == "?"

    def test_truncated_mixed_with_valid(self):
        out = "\n".join([HEADER, TRUNCATED, TCP_LISTEN])
        conns = backend._parse_ss_output(out)
        assert len(conns) == 1
        assert conns[0].process == "sshd"

    def test_empty_input(self):
        assert backend._parse_ss_output("") == []


# ============================================================
# IPv6 nao quebra o parse
# ============================================================


class TestIPv6:
    def test_tcp6_listen_parsed(self):
        c = backend._parse_ss_output(TCP6_LISTEN)[0]
        assert c.proto == "tcp6"
        assert c.state == "LISTEN"
        assert c.local_addr == "[::]:443"
        assert c.peer_addr == "[::]:*"
        assert c.process == "nginx"
        assert c.pid == "999"

    def test_tcp6_estab_parsed(self):
        c = backend._parse_ss_output(TCP6_ESTAB)[0]
        assert c.proto == "tcp6"
        assert c.state == "ESTAB"
        assert c.local_addr == "[2001:db8::1]:54321"
        assert c.peer_addr == "[2606:4700::1111]:443"
        assert c.process == "firefox"
        assert c.pid == "4242"

    def test_mixed_ipv4_ipv6(self):
        out = "\n".join([HEADER, UDP_RESOLVED, TCP6_LISTEN, TCP6_ESTAB])
        conns = backend._parse_ss_output(out)
        assert len(conns) == 3
        assert {c.proto for c in conns} == {"udp", "tcp6"}


# ============================================================
# NetConnection.is_listening / is_established
# ============================================================


class TestConnectionFlags:
    def _make(self, state: str, peer: str) -> backend.NetConnection:
        return backend.NetConnection(
            proto="tcp",
            state=state,
            local_addr="0.0.0.0:1",
            peer_addr=peer,
            process="?",
            pid="?",
            raw="",
        )

    def test_is_listening_state_listen(self):
        # state == LISTEN -> listening, mesmo com peer concreto.
        assert self._make("LISTEN", "10.0.0.1:1234").is_listening is True

    def test_is_listening_peer_wildcard_ipv4(self):
        # peer termina em ':*' -> listening, mesmo state != LISTEN (UNCONN).
        assert self._make("UNCONN", "0.0.0.0:*").is_listening is True

    def test_is_listening_peer_wildcard_ipv6(self):
        assert self._make("UNCONN", "[::]:*").is_listening is True

    def test_not_listening_estab_concrete_peer(self):
        assert self._make("ESTAB", "1.2.3.4:443").is_listening is False

    def test_not_listening_timewait_concrete_peer(self):
        assert self._make("TIME-WAIT", "1.2.3.4:443").is_listening is False

    def test_is_established_only_estab(self):
        assert self._make("ESTAB", "1.2.3.4:443").is_established is True

    def test_not_established_listen(self):
        assert self._make("LISTEN", "0.0.0.0:*").is_established is False

    def test_not_established_timewait(self):
        # TIME-WAIT nao e' ESTAB (so o estado exato 'ESTAB' conta).
        assert self._make("TIME-WAIT", "1.2.3.4:443").is_established is False

    def test_not_established_unconn(self):
        assert self._make("UNCONN", "0.0.0.0:*").is_established is False


# ============================================================
# list_listening / list_established (coletor monkeypatchado)
# ============================================================

# Stdout com uma mistura de estados para exercitar os filtros.
FULL_OUTPUT = "\n".join([
    HEADER,
    UDP_RESOLVED,    # UNCONN, peer ':*'  -> listening
    TCP_LISTEN,      # LISTEN             -> listening
    TCP_ESTAB_NOPROC,  # ESTAB           -> established
    TCP_TIMEWAIT,    # TIME-WAIT         -> nenhum
    TCP6_LISTEN,     # LISTEN (v6)        -> listening
    TCP6_ESTAB,      # ESTAB  (v6)        -> established
])


class TestListConnections:
    def test_list_connections_parses_all_data_rows(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        conns = backend.list_connections()
        # 6 linhas de dados (header pulado).
        assert len(conns) == 6

    def test_no_ss_returns_empty(self, monkeypatch):
        # shutil.which("ss") None -> [] sem nem chamar subprocess.
        monkeypatch.setattr(backend.shutil, "which", lambda name: None)

        def _boom(*a, **k):  # pragma: no cover - nao deve ser chamado
            raise AssertionError("subprocess.run nao deveria ser chamado")

        monkeypatch.setattr(backend.subprocess, "run", _boom)
        assert backend.list_connections() == []

    def test_nonzero_returncode_returns_empty(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT, returncode=1)
        assert backend.list_connections() == []

    def test_subprocess_error_returns_empty(self, monkeypatch):
        import subprocess as _sp

        monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/sbin/ss")

        def _raise(*a, **k):
            raise _sp.TimeoutExpired(cmd="ss", timeout=10)

        monkeypatch.setattr(backend.subprocess, "run", _raise)
        assert backend.list_connections() == []


class TestListListening:
    def test_filters_listening_only(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        conns = backend.list_listening()
        # UDP_RESOLVED (UNCONN ':*'), TCP_LISTEN, TCP6_LISTEN -> 3.
        assert len(conns) == 3
        assert all(c.is_listening for c in conns)
        states = {c.state for c in conns}
        assert states == {"UNCONN", "LISTEN"}

    def test_excludes_estab_and_timewait(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        conns = backend.list_listening()
        assert all(c.state not in {"ESTAB", "TIME-WAIT"} for c in conns)

    def test_process_names_present(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        names = {c.process for c in backend.list_listening()}
        assert {"systemd-resolve", "sshd", "nginx"} <= names


class TestListEstablished:
    def test_filters_established_only(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        conns = backend.list_established()
        # TCP_ESTAB_NOPROC + TCP6_ESTAB -> 2.
        assert len(conns) == 2
        assert all(c.state == "ESTAB" for c in conns)

    def test_excludes_listen_and_wildcard(self, monkeypatch):
        _patch_ss(monkeypatch, FULL_OUTPUT)
        conns = backend.list_established()
        # nenhum dos established e' wildcard nem LISTEN.
        assert all(not c.peer_addr.endswith(":*") for c in conns)
        assert all(c.state != "LISTEN" for c in conns)

    def test_established_empty_when_no_estab(self, monkeypatch):
        out = "\n".join([HEADER, TCP_LISTEN, UDP_RESOLVED, TCP_TIMEWAIT])
        _patch_ss(monkeypatch, out)
        assert backend.list_established() == []


# ============================================================
# elevated=True usa pkexec (coletor monkeypatchado)
# ============================================================


class TestElevated:
    def test_elevated_builds_pkexec_cmd(self, monkeypatch):
        captured: dict[str, list[str]] = {}

        monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/bin/" + name)

        class _FakeCompleted:
            returncode = 0
            stdout = FULL_OUTPUT
            stderr = ""

        def _fake_run(cmd, *a, **k):
            captured["cmd"] = cmd
            return _FakeCompleted()

        monkeypatch.setattr(backend.subprocess, "run", _fake_run)
        conns = backend.list_connections(elevated=True)
        assert captured["cmd"][:2] == ["pkexec", "ss"]
        assert len(conns) == 6

    def test_elevated_without_pkexec_returns_empty(self, monkeypatch):
        # ss existe mas pkexec nao -> [].
        def _which(name):
            return None if name == "pkexec" else "/usr/sbin/ss"

        monkeypatch.setattr(backend.shutil, "which", _which)

        def _boom(*a, **k):  # pragma: no cover
            raise AssertionError("nao deveria rodar subprocess sem pkexec")

        monkeypatch.setattr(backend.subprocess, "run", _boom)
        assert backend.list_connections(elevated=True) == []


# ============================================================
# is_ss_available
# ============================================================


class TestIsSsAvailable:
    def test_true_when_present(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", lambda name: "/usr/sbin/ss")
        assert backend.is_ss_available() is True

    def test_false_when_absent(self, monkeypatch):
        monkeypatch.setattr(backend.shutil, "which", lambda name: None)
        assert backend.is_ss_available() is False
