"""Testes do backend do Vigia Cracker (john/hashcat). Puro: sem ferramentas, sem GTK."""

from __future__ import annotations


from vigia_red.modules.cracker import backend as b


class TestHashTypes:
    def test_catalogo_tem_auto_e_comuns(self):
        ids = {h.id for h in b.HASH_TYPES}
        assert {"auto", "md5", "ntlm", "sha512crypt"} <= ids

    def test_find_hash_type(self):
        assert b.find_hash_type("ntlm").hashcat_mode == "1000"
        assert b.find_hash_type("inexistente") is None


class TestValidate:
    def test_hashfile_existente(self, tmp_path):
        f = tmp_path / "hashes.txt"
        f.write_text("root:$6$abc$def\n")
        assert b.validate_hashfile(str(f))

    def test_hashfile_inexistente(self):
        assert not b.validate_hashfile("/nao/existe/x")
        assert not b.validate_hashfile("")

    def test_wordlist(self, tmp_path):
        wl = tmp_path / "wl.txt"
        wl.write_text("123456\nsenha\n")
        assert b.validate_wordlist(str(wl))
        assert not b.validate_wordlist("/nao/existe")

    def test_count_hashes(self, tmp_path):
        f = tmp_path / "h.txt"
        f.write_text("a:1\n\nb:2\n  \nc:3\n")
        assert b.count_hashes(str(f)) == 3
        assert b.count_hashes("/nao/existe") == 0


class TestBuildCmd:
    def test_john_estrutura(self):
        cmd = b.build_john_cmd("h.txt", "wl.txt", "sha512crypt", use_rules=True)
        assert cmd[0] == "john"
        assert "--wordlist=wl.txt" in cmd
        assert "--format=sha512crypt" in cmd
        assert "--rules" in cmd
        assert cmd[-1] == "h.txt"
        assert isinstance(cmd, list) and "pkexec" not in cmd

    def test_john_auto_sem_format(self):
        cmd = b.build_john_cmd("h.txt", "wl.txt", "auto")
        assert not any(a.startswith("--format=") for a in cmd)

    def test_john_show(self):
        cmd = b.build_john_show_cmd("h.txt", "ntlm")
        assert cmd[:2] == ["john", "--show"]
        assert "--format=nt" in cmd

    def test_hashcat_estrutura(self):
        cmd = b.build_hashcat_cmd("h.txt", "wl.txt", "md5", use_rules=True)
        assert cmd[0] == "hashcat"
        assert cmd[1:5] == ["-m", "0", "-a", "0"]
        assert "h.txt" in cmd and "wl.txt" in cmd
        assert "-r" in cmd

    def test_hashcat_show(self):
        assert b.build_hashcat_show_cmd("h.txt", "ntlm") == \
            ["hashcat", "-m", "1000", "--show", "h.txt"]


class TestParse:
    def test_john_show(self):
        text = ("root:123456:0:0:root:/root:/bin/bash\n"
                "admin:senha:1:1:admin:/home/admin:/bin/sh\n"
                "2 password hashes cracked, 3 left\n")
        out = b.parse_john_show(text)
        assert [(c.identifier, c.password) for c in out] == [
            ("root", "123456"), ("admin", "senha")]

    def test_john_show_ignora_resumo_e_vazias(self):
        assert b.parse_john_show("\n5 password hashes cracked, 0 left\n") == []

    def test_hashcat_show(self):
        text = "e10adc3949ba59abbe56e057f20f883e:123456\nabc:hunter2\n"
        out = b.parse_hashcat_show(text)
        assert out[0].password == "123456"
        assert out[1].password == "hunter2"

    def test_hashcat_show_senha_com_dois_pontos(self):
        out = b.parse_hashcat_show("hash:a:b:c\n")
        assert out[0].password == "a:b:c"


class TestRunGuards:
    def test_hashfile_invalido(self):
        r = b.run_crack("/nao/existe", "/nao/existe")
        assert not r.ran and "hashes" in r.error.lower()

    def test_engine_ausente(self, tmp_path, monkeypatch):
        f = tmp_path / "h.txt"; f.write_text("root:x\n")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        monkeypatch.setattr(b, "john_available", lambda: False)
        r = b.run_crack(str(f), str(wl), engine="john")
        assert not r.ran and "john" in r.error.lower()

    def test_hashcat_exige_tipo(self, tmp_path, monkeypatch):
        f = tmp_path / "h.txt"; f.write_text("root:x\n")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        monkeypatch.setattr(b, "hashcat_available", lambda: True)
        r = b.run_crack(str(f), str(wl), engine="hashcat", hash_type="auto")
        assert not r.ran and "tipo" in r.error.lower()

    def test_fluxo_sucesso_wireado(self, tmp_path, monkeypatch):
        f = tmp_path / "h.txt"; f.write_text("root:hash1\nadmin:hash2\n")
        wl = tmp_path / "wl.txt"; wl.write_text("123456\n")
        monkeypatch.setattr(b, "john_available", lambda: True)
        monkeypatch.setattr(b, "save_report", lambda r: None)

        def fake_run(cmd, timeout=0):
            if "--show" in cmd:
                return 0, "root:123456:x\n1 password hash cracked, 1 left\n", ""
            return 0, "", ""
        monkeypatch.setattr(b.proc, "run", fake_run)
        r = b.run_crack(str(f), str(wl), engine="john", hash_type="auto")
        assert r.ran and not r.error
        assert r.cracked_count == 1 and r.total_hashes == 2
        assert r.cracked[0].password == "123456"

    def test_formato_desconhecido_vira_erro(self, tmp_path, monkeypatch):
        f = tmp_path / "h.txt"; f.write_text("root:x\n")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        monkeypatch.setattr(b, "john_available", lambda: True)
        monkeypatch.setattr(b, "save_report", lambda r: None)
        monkeypatch.setattr(
            b.proc, "run",
            lambda cmd, timeout=0: (1, "", "Unknown ciphertext format"))
        r = b.run_crack(str(f), str(wl), engine="john")
        assert not r.ran and "ciphertext format" in r.error.lower()


class TestExport:
    def test_texto_com_fracas(self):
        r = b.CrackResult(hashfile="/x/shadow", engine="john", total_hashes=3)
        r.cracked = [b.Cracked("root", "123456")]
        txt = b.result_to_text(r)
        assert "root" in txt and "123456" in txt and "fraca" in txt.lower()

    def test_dict_nao_guarda_senha(self):
        r = b.CrackResult(hashfile="/x", total_hashes=1)
        r.cracked = [b.Cracked("root", "segredo")]
        d = b.result_to_dict(r)
        assert "segredo" not in str(d)
        assert d["weak_identifiers"] == ["root"]


class TestRegistry:
    def test_cracker_pronto_e_wireado(self):
        from vigia_red.registry import MODULES
        m = next(m for m in MODULES if m.id == "cracker")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.cracker.page"
        assert m.requires and m.requires[0].checks == ("john", "hashcat")
