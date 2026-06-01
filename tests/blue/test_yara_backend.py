"""Testes do backend do Vigia YARA (vigia_blue.modules.yara.backend).

Tudo headless (não precisa do `yara` instalado nem de gi):
- parse_yara_output — parser da saída do yara (plano, com tags, ruído).
- build_scan_cmd — argv (lista, -- antes do alvo, regras na ordem).
- list_rules / bundled_rules / effective_rules — descoberta de regras.
- scan — orquestração com proc.run mockado.
- save_report / list_recent_reports — round-trip em tmp.
"""

from __future__ import annotations

from vigia_blue.modules.yara import backend


class TestParse:
    def test_match_simples(self):
        out = "EICAR_Test_File /home/user/eicar.txt"
        m = backend.parse_yara_output(out)
        assert len(m) == 1
        assert m[0].rule == "EICAR_Test_File"
        assert m[0].path == "/home/user/eicar.txt"
        assert m[0].tags == []

    def test_match_com_tags(self):
        out = "Suspicious_PHP_Webshell [webshell,php] /var/www/x.php"
        m = backend.parse_yara_output(out)
        assert len(m) == 1
        assert m[0].rule == "Suspicious_PHP_Webshell"
        assert m[0].tags == ["webshell", "php"]
        assert m[0].path == "/var/www/x.php"

    def test_varios_matches(self):
        out = (
            "RuleA /a/file1\n"
            "RuleB /b/file2\n"
            "RuleA /c/file3\n"
        )
        m = backend.parse_yara_output(out)
        assert [x.rule for x in m] == ["RuleA", "RuleB", "RuleA"]
        assert [x.path for x in m] == ["/a/file1", "/b/file2", "/c/file3"]

    def test_path_com_espacos(self):
        out = "RuleX /home/user/Área de Trabalho/arquivo.txt"
        m = backend.parse_yara_output(out)
        assert len(m) == 1
        assert m[0].path == "/home/user/Área de Trabalho/arquivo.txt"

    def test_ignora_linhas_de_strings_casadas(self):
        # com -s, abaixo do match vêm linhas "0x...:$var: bytes" indentadas.
        out = (
            "RuleA /a/file1\n"
            "0x10:$s1: 4d 5a\n"
            "    0x20:$s2: 90 90\n"
        )
        m = backend.parse_yara_output(out)
        assert len(m) == 1
        assert m[0].rule == "RuleA"

    def test_ignora_erros_e_avisos(self):
        out = (
            "error: rule \"x\" syntax error\n"
            "warning: rule \"y\" deprecated\n"
            "RuleA /a/file1\n"
        )
        m = backend.parse_yara_output(out)
        assert len(m) == 1 and m[0].rule == "RuleA"

    def test_vazio(self):
        assert backend.parse_yara_output("") == []
        assert backend.parse_yara_output("   \n\n") == []

    def test_linha_so_com_regra_ignorada(self):
        # uma palavra só (sem path) não é um match válido.
        assert backend.parse_yara_output("RuleSemPath\n") == []


class TestBuildCmd:
    def test_recursivo_default(self):
        cmd = backend.build_scan_cmd(["/r/rules.yar"], "/alvo")
        assert cmd[0] == "yara"
        assert "-r" in cmd
        assert "-w" in cmd
        assert cmd[-1] == "/alvo"        # alvo por último
        assert "--" not in cmd          # yara não entende '--' (trata como arquivo)

    def test_nao_recursivo(self):
        cmd = backend.build_scan_cmd(["/r/rules.yar"], "/alvo", recursive=False)
        assert "-r" not in cmd

    def test_multiplas_regras_na_ordem(self):
        cmd = backend.build_scan_cmd(["/r/a.yar", "/r/b.yar"], "/alvo")
        ia, ib, it = cmd.index("/r/a.yar"), cmd.index("/r/b.yar"), cmd.index("/alvo")
        assert ia < ib < it

    def test_e_lista_de_strings(self):
        cmd = backend.build_scan_cmd(["/r/a.yar"], "/alvo")
        assert all(isinstance(x, str) for x in cmd)


class TestRulesDiscovery:
    def test_list_rules_vazio_se_nao_existe(self, tmp_path):
        assert backend.list_rules(tmp_path / "nao-existe") == []

    def test_list_rules_acha_yar_e_yara(self, tmp_path):
        (tmp_path / "a.yar").write_text("rule a {condition: true}")
        (tmp_path / "b.yara").write_text("rule b {condition: true}")
        (tmp_path / "leiame.txt").write_text("nao e regra")
        names = [p.name for p in backend.list_rules(tmp_path)]
        assert names == ["a.yar", "b.yara"]

    def test_bundled_rules_existe(self):
        # o starter.yar empacotado deve ser encontrado.
        b = backend.bundled_rules()
        assert any(p.name == "starter.yar" for p in b)

    def test_effective_usa_user_se_houver(self, tmp_path, monkeypatch):
        (tmp_path / "user.yar").write_text("rule u {condition: true}")
        monkeypatch.setattr(backend, "RULES_DIR", tmp_path)
        eff = backend.effective_rules()
        assert [p.name for p in eff] == ["user.yar"]

    def test_effective_cai_no_bundled_sem_user(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "RULES_DIR", tmp_path / "vazio")
        eff = backend.effective_rules()
        assert any(p.name == "starter.yar" for p in eff)


class TestScan:
    def test_scan_parseia_matches(self, monkeypatch):
        monkeypatch.setattr(
            backend.proc, "run",
            lambda cmd, timeout=900: (0, "EICAR_Test_File /tmp/eicar.txt\n", ""),
        )
        r = backend.scan("/tmp", rules=["/r/a.yar"])
        assert r.error == ""
        assert len(r.matches) == 1
        assert r.matches[0].rule == "EICAR_Test_File"
        assert r.rules_count == 1
        assert r.started_at

    def test_scan_rc_erro_sem_stdout(self, monkeypatch):
        monkeypatch.setattr(
            backend.proc, "run",
            lambda cmd, timeout=900: (1, "", "error: could not open file"),
        )
        r = backend.scan("/tmp", rules=["/r/a.yar"])
        assert "could not open" in r.error
        assert r.matches == []

    def test_scan_sem_regras_erro(self, monkeypatch):
        monkeypatch.setattr(backend.proc, "run", lambda *a, **k: (0, "", ""))
        r = backend.scan("/tmp", rules=[])
        assert "regras" in r.error.lower()
        assert r.matches == []


class TestReports:
    def test_save_e_list_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path)
        res = backend.ScanResult(
            target="/tmp",
            started_at="2026-06-01T10:00:00",
            matches=[backend.Match(rule="EICAR_Test_File", path="/tmp/e.txt")],
            rules_count=1,
        )
        p = backend.save_report(res)
        assert p is not None and p.exists()
        recent = backend.list_recent_reports()
        assert len(recent) == 1
        assert recent[0]["target"] == "/tmp"
        assert recent[0]["matches"][0]["rule"] == "EICAR_Test_File"
        assert "_file" in recent[0]

    def test_list_sem_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(backend, "REPORTS_DIR", tmp_path / "nada")
        assert backend.list_recent_reports() == []


class TestWiring:
    def test_registry_liga_yara_na_gui(self):
        from vigia_blue.registry import MODULES
        yara = next(m for m in MODULES if m.id == "yara")
        assert yara.impl == "vigia_blue.modules.yara.page"
        assert yara.status == "pronto"
        # registry continua importável headless (não puxa gi/page)
        assert yara.icon.endswith(".svg")
