"""Testes do parser do output de `aide --check` (vigia_integrity.backend).

parse_check_output() le o texto cru do AIDE e devolve (CheckSummary, lista
de FileChange). Exercitamos:
- contagem do bloco Summary (Total/Added/Removed/Changed)
- extracao das secoes delimitadas por '-----' (Added/Removed/Changed entries)
- _extract_path_from_line (incl. path com ':' no nome)
- _extract_changed_properties (flags f/p/m/C... -> nomes legiveis)
- parse_conf_watched_paths (paths monitorados no .conf)

Nao precisa de AIDE instalado nem de root.
"""

from __future__ import annotations

from vigia_integrity import backend


# Output realista de `aide --check` com mudancas. As secoes Added/Removed/
# Changed sao delimitadas por linhas de tracos; o Summary aparece antes
# (sem tracos) so com os numeros.
SAMPLE_CHECK = """AIDE 0.16 found differences between database and filesystem!!
Start timestamp: 2026-05-13 12:00:00 -0300 (AIDE 0.16)

Summary:
  Total number of entries:\t1234
  Added entries:\t\t2
  Removed entries:\t\t1
  Changed entries:\t\t3

---------------------------------------------------
Added entries:
---------------------------------------------------

f++++++++++++++++: /etc/newfile.conf
d++++++++++++++++: /etc/newdir

---------------------------------------------------
Removed entries:
---------------------------------------------------

f----------------: /etc/oldfile.conf

---------------------------------------------------
Changed entries:
---------------------------------------------------

f   ...    .C... : /etc/passwd
f   p..    m.... : /etc/ssh/sshd_config
f   ...    .C... : /var/spool/cron/root:backup

---------------------------------------------------
Detailed information about changes:
---------------------------------------------------

(detalhes ignorados pelo parser de overview)

End timestamp: 2026-05-13 12:05:00 -0300 (run time: 5m 0s)
"""

SAMPLE_NO_CHANGES = """AIDE 0.16
Start timestamp: 2026-05-13 12:00:00 -0300 (AIDE 0.16)

Summary:
  Total number of entries:\t1234
  Added entries:\t\t0
  Removed entries:\t\t0
  Changed entries:\t\t0

End timestamp: 2026-05-13 12:00:30 -0300 (run time: 0m 30s)
"""


class TestParseCheckSummary:
    def test_counts(self):
        summary, _ = backend.parse_check_output(SAMPLE_CHECK)
        assert summary.total_entries == 1234
        assert summary.added == 2
        assert summary.removed == 1
        assert summary.changed == 3
        assert summary.has_changes is True

    def test_no_changes(self):
        summary, changes = backend.parse_check_output(SAMPLE_NO_CHANGES)
        assert summary.total_entries == 1234
        assert summary.added == 0
        assert summary.has_changes is False
        # Sem secoes delimitadas por '-----', nenhuma mudanca extraida
        assert changes == []


class TestParseCheckChanges:
    def test_total_changes(self):
        _, changes = backend.parse_check_output(SAMPLE_CHECK)
        assert len(changes) == 6  # 2 added + 1 removed + 3 changed

    def test_change_types(self):
        _, changes = backend.parse_check_output(SAMPLE_CHECK)
        by_type: dict[str, list[str]] = {"added": [], "removed": [], "changed": []}
        for c in changes:
            by_type[c.change_type].append(c.path)
        assert by_type["added"] == ["/etc/newfile.conf", "/etc/newdir"]
        assert by_type["removed"] == ["/etc/oldfile.conf"]
        assert "/etc/passwd" in by_type["changed"]
        assert "/etc/ssh/sshd_config" in by_type["changed"]

    def test_path_with_colon_preserved(self):
        _, changes = backend.parse_check_output(SAMPLE_CHECK)
        paths = [c.path for c in changes]
        # bug antigo: rsplit(':') truncava paths com ':'
        assert "/var/spool/cron/root:backup" in paths

    def test_changed_properties(self):
        _, changes = backend.parse_check_output(SAMPLE_CHECK)
        props = {c.path: c.properties for c in changes if c.change_type == "changed"}
        assert props["/etc/passwd"] == ["checksum"]
        assert props["/etc/ssh/sshd_config"] == ["perms", "mtime"]


class TestExtractPathFromLine:
    def test_file_line(self):
        assert backend._extract_path_from_line("f++++: /etc/hosts") == "/etc/hosts"

    def test_dir_line(self):
        assert backend._extract_path_from_line("d++++: /etc/cron.d") == "/etc/cron.d"

    def test_link_line(self):
        assert backend._extract_path_from_line("l++++: /etc/localtime") == "/etc/localtime"

    def test_path_with_colon(self):
        assert (
            backend._extract_path_from_line("f++: /var/data/file:v2")
            == "/var/data/file:v2"
        )

    def test_garbage_returns_empty(self):
        assert backend._extract_path_from_line("isso nao casa nada") == ""
        assert backend._extract_path_from_line("") == ""


class TestExtractChangedProperties:
    def test_perms_and_mtime(self):
        props = backend._extract_changed_properties("f   p..    m.... : /x")
        assert props == ["perms", "mtime"]

    def test_checksum(self):
        assert backend._extract_changed_properties("f   ...    .C... : /x") == ["checksum"]

    def test_dedup(self):
        # 'p' repetido nao duplica
        assert backend._extract_changed_properties("f pp : /x") == ["perms"]

    def test_no_known_flags(self):
        assert backend._extract_changed_properties("f .... : /x") == []


class TestParseConfWatchedPaths:
    def test_extracts_paths_skips_directives(self, tmp_path, monkeypatch):
        conf = tmp_path / "aide-vigia.conf"
        conf.write_text(
            "# comentario\n"
            "database_in=file:/var/lib/aide/aide.db.gz\n"
            "NORMAL = R+sha256\n"
            "/etc NORMAL\n"
            "/root NORMAL\n"
            "!/etc/mtab NORMAL\n"
            "/var/spool/cron NORMAL\n",
            encoding="utf-8",
        )
        # AIDE_CONF_VIGIA existente => silverblue_profile_active() True =>
        # active_conf_path() retorna esse arquivo.
        monkeypatch.setattr(backend, "AIDE_CONF_VIGIA", conf)
        paths = backend.parse_conf_watched_paths()
        # negacao com grupo (regra "path grupo") e' captada, incl. o '!'
        assert paths == ["/etc", "/root", "!/etc/mtab", "/var/spool/cron"]

    def test_bare_negation_without_group_is_skipped(self, tmp_path, monkeypatch):
        # O regex exige "path<espaco>token"; uma linha de negacao "crua"
        # (so "!/path", sem grupo) nao casa e e' ignorada no overview.
        conf = tmp_path / "aide-vigia.conf"
        conf.write_text("/etc NORMAL\n!/etc/mtab\n/root NORMAL\n", encoding="utf-8")
        monkeypatch.setattr(backend, "AIDE_CONF_VIGIA", conf)
        assert backend.parse_conf_watched_paths() == ["/etc", "/root"]

    def test_missing_conf_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "AIDE_CONF_VIGIA", tmp_path / "nope.conf")
        monkeypatch.setattr(backend, "AIDE_CONF_SYSTEM", tmp_path / "nope2.conf")
        assert backend.parse_conf_watched_paths() == []


class TestCheckResultProperties:
    def test_baseline_match_when_clean(self):
        summary, changes = backend.parse_check_output(SAMPLE_NO_CHANGES)
        res = backend.CheckResult(success=True, summary=summary, changes=changes)
        assert res.baseline_match is True

    def test_no_baseline_match_when_changes(self):
        summary, changes = backend.parse_check_output(SAMPLE_CHECK)
        res = backend.CheckResult(success=True, summary=summary, changes=changes)
        assert res.baseline_match is False

    def test_no_baseline_match_when_failed(self):
        summary, _ = backend.parse_check_output(SAMPLE_NO_CHANGES)
        res = backend.CheckResult(success=False, summary=summary, changes=[])
        assert res.baseline_match is False


class TestFormatAge:
    def test_none(self):
        assert backend.format_age(None) == "Nunca"

    def test_seconds(self):
        assert backend.format_age(30) == "agora mesmo"

    def test_minutes(self):
        assert backend.format_age(120) == "há 2 min"

    def test_hours(self):
        assert backend.format_age(3600 * 5) == "há 5h"

    def test_days(self):
        assert backend.format_age(86400 * 2) == "há 2 dias"
