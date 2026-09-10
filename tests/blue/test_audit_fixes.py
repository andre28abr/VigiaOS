"""Regressões da auditoria 2026-09 (Blue): regex de regra YARA, heurística de root do IDS."""

from __future__ import annotations

from vigia_blue.modules.ids import backend as ids
from vigia_blue.modules.yara import backend as yara


class TestYaraRuleRegex:
    def test_nao_casa_rule_dentro_de_string(self, tmp_path):
        f = tmp_path / "x.yar"
        f.write_text(
            'rule real_one {\n  meta:\n    description = "this rule detects stuff"\n'
            '    severity = "high"\n  strings:\n    $a = "rule"\n  condition: $a\n}\n'
        )
        assert yara.count_rules([f]) == 1
        meta = yara.rule_meta([f])
        assert list(meta) == ["real_one"]
        assert meta["real_one"]["severity"] == "high"

    def test_modificadores_private_global(self, tmp_path):
        f = tmp_path / "y.yar"
        f.write_text("private rule a { condition: true }\nglobal private rule b { condition: true }\n")
        assert yara.count_rules([f]) == 2
        assert set(yara.rule_meta([f])) == {"a", "b"}


class TestIdsNeedsRoot:
    def test_so_permissao(self):
        assert ids._needs_root("could not open /etc/suricata/suricata.yaml: Permission denied")
        assert ids._needs_root("[Errno 13] EACCES")

    def test_pcap_corrompido_nao_pede_root(self):
        assert not ids._needs_root("could not open pcap file lixo.pcap")
        assert not ids._needs_root("failed to open input file")
        assert not ids._needs_root("")
