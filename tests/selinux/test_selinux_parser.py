"""Testes dos parsers do backend SELinux (vigia_selinux.backend).

Todas as funções aqui são puras de I/O externo: lêem stdout de comandos
(ausearch, semanage, getsebool, ps) ou um arquivo (/etc/selinux/config).
Nos testes alimentamos stdout fixo via monkeypatch de `backend.subprocess.run`
e arquivos via tmp_path — nenhum teste precisa de SELinux instalado nem root.

NÃO importa `gi`/GTK: `from vigia_selinux import backend` é headless (o módulo
só usa re/shutil/subprocess/dataclasses). conftest põe tools/*/src no sys.path.
"""

from __future__ import annotations

import subprocess

from vigia_selinux import backend


# ---------------------------------------------------------------------------
# Helpers de fake subprocess
# ---------------------------------------------------------------------------

class FakeCompleted:
    """Imita subprocess.CompletedProcess o suficiente para o backend."""

    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _patch_run(monkeypatch, stdout="", returncode=0, stderr=""):
    """Substitui backend.subprocess.run por um fake com saída fixa.

    Devolve a lista de chamadas (cada item = lista de args do comando), para
    quem quiser inspecionar o comando montado.
    """
    calls = []

    def fake_run(args, *a, **kw):
        calls.append(args)
        return FakeCompleted(stdout=stdout, returncode=returncode, stderr=stderr)

    monkeypatch.setattr(backend.subprocess, "run", fake_run)
    return calls


def _patch_which(monkeypatch, present=True):
    """Faz shutil.which (usado nos guards de semanage) achar/não achar o bin."""
    monkeypatch.setattr(
        backend.shutil, "which",
        lambda name: ("/usr/sbin/" + name) if present else None,
    )


# ===========================================================================
# _parse_ausearch_avc
# ===========================================================================

# Linha AVC realista no formato --raw do ausearch (uma linha só).
AVC_LINE = (
    'type=AVC msg=audit(1716900000.123:456): avc:  denied  { read } '
    'for  pid=1234 comm="httpd" name="index.html" dev="dm-0" ino=98765 '
    'scontext=system_u:system_r:httpd_t:s0 '
    'tcontext=unconfined_u:object_r:user_home_t:s0 tclass=file permissive=0'
)


class TestParseAusearchAvc:
    def test_extracts_all_fields(self):
        denials = backend._parse_ausearch_avc(AVC_LINE)
        assert len(denials) == 1
        d = denials[0]
        assert d.timestamp == "1716900000.123"
        assert d.op == "read"
        assert d.comm == "httpd"
        assert d.pid == "1234"
        assert d.name == "index.html"
        assert d.scontext == "system_u:system_r:httpd_t:s0"
        assert d.tcontext == "unconfined_u:object_r:user_home_t:s0"
        assert d.tclass == "file"
        assert d.permissive is False
        # raw preserva a linha original (sem strip) p/ passar ao audit2allow
        assert d.raw == AVC_LINE

    def test_permissive_one_is_true(self):
        line = AVC_LINE.replace("permissive=0", "permissive=1")
        d = backend._parse_ausearch_avc(line)[0]
        assert d.permissive is True

    def test_permissive_absent_defaults_false(self):
        line = AVC_LINE.replace(" permissive=0", "")
        d = backend._parse_ausearch_avc(line)[0]
        assert d.permissive is False

    def test_non_avc_line_ignored(self):
        line = (
            'type=SYSCALL msg=audit(1716900000.123:456): arch=c000003e '
            'syscall=2 success=no comm="httpd"'
        )
        assert backend._parse_ausearch_avc(line) == []

    def test_blank_and_mixed_lines(self):
        # Bloco com linha em branco + SYSCALL + 2 AVC: só os 2 AVC contam.
        output = "\n".join([
            "",
            'type=SYSCALL msg=audit(1.0:1): comm="x"',
            AVC_LINE,
            "   ",
            AVC_LINE.replace("comm=\"httpd\"", "comm=\"nginx\""),
        ])
        denials = backend._parse_ausearch_avc(output)
        assert [d.comm for d in denials] == ["httpd", "nginx"]

    def test_missing_field_becomes_question_mark(self):
        # Linha AVC mínima: sem comm/pid/name/scontext/tcontext/tclass.
        # Sem msg=audit(...) → timestamp '?'; sem { } → op '?'.
        line = "type=AVC avc:  denied for foo"
        d = backend._parse_ausearch_avc(line)[0]
        assert d.timestamp == "?"
        assert d.op == "?"
        assert d.comm == "?"
        assert d.pid == "?"
        assert d.name == "?"
        assert d.scontext == "?"
        assert d.tcontext == "?"
        assert d.tclass == "?"
        # ausência de permissive=N → False (não '?', é bool)
        assert d.permissive is False

    def test_leading_whitespace_line_still_parsed(self):
        # ausearch --raw às vezes indenta; backend faz .strip() antes do
        # startswith, então linha indentada ainda é reconhecida como AVC.
        d = backend._parse_ausearch_avc("    " + AVC_LINE)[0]
        assert d.comm == "httpd"


# ===========================================================================
# _try_semanage_booleans  (parse de `semanage boolean -l`)
# ===========================================================================

SEMANAGE_BOOL_OUTPUT = """\
SELinux boolean                State  Default Description

httpd_can_network_connect      (off  ,  off)  Allow httpd to network connect
httpd_enable_cgi               (on   ,   on)  Allow httpd to enable cgi
----                           ----   ----    ----
nfs_export_all_rw              (off  ,  off)  Allow nfs to export all rw
"""


class TestSemanageBooleans:
    def test_parses_name_value_description(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout=SEMANAGE_BOOL_OUTPUT, returncode=0)
        bools = backend._try_semanage_booleans()

        by_name = {b.name: b for b in bools}
        # header + separador '----' pulados → só 3 booleans
        assert set(by_name) == {
            "httpd_can_network_connect",
            "httpd_enable_cgi",
            "nfs_export_all_rw",
        }
        off = by_name["httpd_can_network_connect"]
        assert off.value is False
        assert off.description == "Allow httpd to network connect"

        on = by_name["httpd_enable_cgi"]
        assert on.value is True
        assert on.description == "Allow httpd to enable cgi"

    def test_no_semanage_binary_returns_empty(self, monkeypatch):
        # which() devolve None → curto-circuito antes de chamar subprocess.
        _patch_which(monkeypatch, present=False)
        # Se chamasse run, explodiria; garantimos que NÃO chama.
        def boom(*a, **kw):
            raise AssertionError("subprocess.run não deveria ser chamado")
        monkeypatch.setattr(backend.subprocess, "run", boom)
        assert backend._try_semanage_booleans() == []

    def test_empty_stdout_returns_empty(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout="   \n", returncode=0)
        assert backend._try_semanage_booleans() == []

    def test_nonzero_returncode_returns_empty(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout=SEMANAGE_BOOL_OUTPUT, returncode=1)
        assert backend._try_semanage_booleans() == []


class TestListBooleansFallback:
    def test_falls_back_to_getsebool_when_semanage_empty(self, monkeypatch):
        """list_booleans(): semanage vazio → usa getsebool."""
        # semanage some (which None) e getsebool responde.
        monkeypatch.setattr(backend.shutil, "which", lambda name: None)
        _patch_run(monkeypatch, stdout="httpd_can_network_connect --> on\n")
        bools = backend.list_booleans()
        assert len(bools) == 1
        assert bools[0].name == "httpd_can_network_connect"
        assert bools[0].value is True

    def test_prefers_semanage_when_available(self, monkeypatch):
        """list_booleans(): semanage com dados → não cai pro getsebool."""
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout=SEMANAGE_BOOL_OUTPUT, returncode=0)
        bools = backend.list_booleans()
        # descrição só vem do semanage; getsebool não preenche description
        assert any(b.description for b in bools)
        assert {b.name for b in bools} >= {"httpd_can_network_connect"}


# ===========================================================================
# _getsebool_booleans  (parse de `getsebool -a`)
# ===========================================================================

class TestGetseboolBooleans:
    def test_on_becomes_true(self, monkeypatch):
        _patch_run(monkeypatch, stdout="httpd_t --> on\n")
        bools = backend._getsebool_booleans()
        assert len(bools) == 1
        assert bools[0].name == "httpd_t"
        assert bools[0].value is True
        # getsebool não traz descrição
        assert bools[0].description == ""

    def test_off_becomes_false(self, monkeypatch):
        _patch_run(monkeypatch, stdout="ftpd_anon_write --> off\n")
        assert backend._getsebool_booleans()[0].value is False

    def test_line_without_arrow_skipped(self, monkeypatch):
        out = (
            "httpd_can_network_connect --> on\n"
            "linha lixo sem seta\n"
            "ftpd_anon_write --> off\n"
        )
        _patch_run(monkeypatch, stdout=out)
        bools = backend._getsebool_booleans()
        assert [b.name for b in bools] == [
            "httpd_can_network_connect", "ftpd_anon_write",
        ]

    def test_subprocess_error_returns_empty(self, monkeypatch):
        def raiser(*a, **kw):
            raise subprocess.SubprocessError("falhou")
        monkeypatch.setattr(backend.subprocess, "run", raiser)
        assert backend._getsebool_booleans() == []


# ===========================================================================
# get_persistent_mode  (lê /etc/selinux/config — testado via path=tmp_path)
# ===========================================================================

class TestGetPersistentMode:
    def test_enforcing(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.write_text(
            "# comentário\n"
            "SELINUX=enforcing\n"
            "SELINUXTYPE=targeted\n"
        )
        assert backend.get_persistent_mode(str(cfg)) == "enforcing"

    def test_permissive_lowercased(self, tmp_path):
        cfg = tmp_path / "config"
        cfg.write_text("SELINUX=Permissive\n")
        assert backend.get_persistent_mode(str(cfg)) == "permissive"

    def test_selinuxtype_does_not_confuse(self, tmp_path):
        # SELINUXTYPE= aparece ANTES de SELINUX=; não pode casar 'targeted'.
        cfg = tmp_path / "config"
        cfg.write_text(
            "SELINUXTYPE=targeted\n"
            "SELINUX=disabled\n"
        )
        assert backend.get_persistent_mode(str(cfg)) == "disabled"

    def test_only_selinuxtype_present_is_unknown(self, tmp_path):
        # Sem nenhuma linha SELINUX= legítima → unknown (não 'targeted').
        cfg = tmp_path / "config"
        cfg.write_text("SELINUXTYPE=targeted\n")
        assert backend.get_persistent_mode(str(cfg)) == "unknown"

    def test_missing_file_returns_unknown(self, tmp_path):
        assert backend.get_persistent_mode(str(tmp_path / "nao-existe")) == "unknown"

    def test_default_path_is_etc_selinux_config(self):
        # Garante que o refactor manteve o default literal de produção.
        import inspect
        sig = inspect.signature(backend.get_persistent_mode)
        assert sig.parameters["path"].default == "/etc/selinux/config"


# ===========================================================================
# list_ports  (parse de `semanage port -l`)
# ===========================================================================

SEMANAGE_PORT_OUTPUT = """\
SELinux Port Type              Proto    Port Number

http_port_t                    tcp      80, 81, 443, 488, 8008, 8009, 8443, 9000
ssh_port_t                     tcp      22
dns_port_t                     udp      53
----                           ----     ----
"""


class TestListPorts:
    def test_parses_columns(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout=SEMANAGE_PORT_OUTPUT, returncode=0)
        ports = backend.list_ports()

        by_ctx = {p.context: p for p in ports}
        # header e separador '----' pulados
        assert set(by_ctx) == {"http_port_t", "ssh_port_t", "dns_port_t"}
        http = by_ctx["http_port_t"]
        assert http.proto == "tcp"
        # split(None, 2): o 3º campo mantém vírgulas/espaços internos
        assert http.ports == "80, 81, 443, 488, 8008, 8009, 8443, 9000"
        assert by_ctx["dns_port_t"].proto == "udp"

    def test_short_line_skipped(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        out = (
            "http_port_t                    tcp      80\n"
            "linha_curta_so_dois_campos     tcp\n"   # <3 colunas → pulada
            "ssh_port_t                     tcp      22\n"
        )
        _patch_run(monkeypatch, stdout=out, returncode=0)
        ports = backend.list_ports()
        assert [p.context for p in ports] == ["http_port_t", "ssh_port_t"]

    def test_no_semanage_returns_empty(self, monkeypatch):
        _patch_which(monkeypatch, present=False)
        assert backend.list_ports() == []

    def test_nonzero_returncode_returns_empty(self, monkeypatch):
        _patch_which(monkeypatch, present=True)
        _patch_run(monkeypatch, stdout=SEMANAGE_PORT_OUTPUT, returncode=1)
        assert backend.list_ports() == []


# ===========================================================================
# list_processes  (parse de `ps -eZ -o label,pid,user,comm`)
# ===========================================================================

PS_OUTPUT = """\
system_u:system_r:init_t:s0 1 root systemd
system_u:system_r:httpd_t:s0 1234 apache httpd
unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023 4321 andre bash
"""


class TestListProcesses:
    def test_parses_four_columns(self, monkeypatch):
        _patch_run(monkeypatch, stdout=PS_OUTPUT, returncode=0)
        procs = backend.list_processes()
        assert len(procs) == 3
        p0 = procs[0]
        assert p0.context == "system_u:system_r:init_t:s0"
        assert p0.pid == "1"
        assert p0.user == "root"
        assert p0.comm == "systemd"
        # comm com espaço (split None,3) preserva o resto na 4ª coluna
        assert procs[1].comm == "httpd"

    def test_comm_with_spaces_kept_whole(self, monkeypatch):
        # split(None, 3): só os 3 primeiros são separados; o resto vira comm.
        line = "ctx_t 99 root my long process name\n"
        _patch_run(monkeypatch, stdout=line, returncode=0)
        p = backend.list_processes()[0]
        assert p.pid == "99"
        assert p.user == "root"
        assert p.comm == "my long process name"

    def test_short_line_skipped(self, monkeypatch):
        out = (
            "system_u:system_r:init_t:s0 1 root systemd\n"
            "ctx_t 2 root\n"   # só 3 campos → <4 → pulada
            "ctx_t 3 root bash\n"
        )
        _patch_run(monkeypatch, stdout=out, returncode=0)
        procs = backend.list_processes()
        assert [p.pid for p in procs] == ["1", "3"]

    def test_limit_truncates(self, monkeypatch):
        lines = "\n".join(f"ctx_t {i} root proc{i}" for i in range(10))
        _patch_run(monkeypatch, stdout=lines + "\n", returncode=0)
        procs = backend.list_processes(limit=3)
        assert len(procs) == 3
        assert [p.pid for p in procs] == ["0", "1", "2"]

    def test_nonzero_returncode_returns_empty(self, monkeypatch):
        _patch_run(monkeypatch, stdout=PS_OUTPUT, returncode=1)
        assert backend.list_processes() == []


# ===========================================================================
# Boolean.display_description  (prioridade pt-BR > semanage > fallback)
# ===========================================================================

class TestDisplayDescription:
    def test_ptbr_dict_wins_over_semanage(self):
        # httpd_can_network_connect está no dict pt-BR; deve ignorar a
        # description vinda do semanage.
        b = backend.Boolean(
            name="httpd_can_network_connect",
            value=True,
            description="Allow httpd to network connect",  # inglês do semanage
        )
        expected = backend.BOOLEAN_DESCRIPTIONS_PT["httpd_can_network_connect"]
        assert b.display_description == expected
        assert "Permite" in b.display_description  # confirma que é o pt-BR

    def test_semanage_description_when_not_in_dict(self):
        # Nome inexistente no dict pt-BR → usa a description do semanage.
        b = backend.Boolean(
            name="boolean_inexistente_xyz",
            value=False,
            description="Some upstream description",
        )
        assert b.display_description == "Some upstream description"

    def test_fallback_when_no_dict_and_no_description(self):
        b = backend.Boolean(name="boolean_inexistente_xyz", value=False)
        assert b.display_description == "Sem descrição disponível."

    def test_empty_description_treated_as_missing(self):
        # description="" é falsy → cai no fallback (não retorna string vazia).
        b = backend.Boolean(name="outro_xyz", value=False, description="")
        assert b.display_description == "Sem descrição disponível."
