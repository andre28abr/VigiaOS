"""Testes do backend do Vigia Wireless (aircrack-ng). Puro: sem ferramenta, sem GTK."""

from __future__ import annotations

import pytest

from vigia_red.modules.wireless import backend as b


class TestValidate:
    @pytest.mark.parametrize("bssid", ["AA:BB:CC:DD:EE:FF", "00:11:22:33:44:55"])
    def test_bssid_valido(self, bssid):
        assert b.validate_bssid(bssid)

    @pytest.mark.parametrize("bssid", ["", "AA:BB:CC:DD:EE", "ZZ:BB:CC:DD:EE:FF",
                                       "AABBCCDDEEFF"])
    def test_bssid_invalido(self, bssid):
        assert not b.validate_bssid(bssid)

    def test_interface(self):
        assert b.validate_interface("wlan0")
        assert b.validate_interface("wlp3s0mon")
        assert not b.validate_interface("wlan 0")
        assert not b.validate_interface("a" * 16)

    def test_channel(self):
        assert b.validate_channel("6")
        assert b.validate_channel("149")
        assert not b.validate_channel("0")
        assert not b.validate_channel("999")
        assert not b.validate_channel("x")

    def test_capture(self, tmp_path):
        cap = tmp_path / "meu.cap"; cap.write_bytes(b"\x00")
        assert b.validate_capture(str(cap))
        txt = tmp_path / "x.txt"; txt.write_text("x")
        assert not b.validate_capture(str(txt))
        assert not b.validate_capture("/nao/existe.cap")


class TestBuildCmd:
    def test_airodump(self):
        cmd = b.build_airodump_cmd("wlan0mon", "AA:BB:CC:DD:EE:FF", "6", "/tmp/cap")
        assert cmd[0] == "airodump-ng"
        assert "--bssid" in cmd and "AA:BB:CC:DD:EE:FF" in cmd
        assert "--channel" in cmd and "6" in cmd
        assert cmd[-1] == "wlan0mon"

    def test_deauth(self):
        cmd = b.build_aireplay_deauth_cmd("wlan0mon", "AA:BB:CC:DD:EE:FF", "5")
        assert cmd[:2] == ["aireplay-ng", "--deauth"]
        assert "5" in cmd and "-a" in cmd

    def test_aircrack_com_bssid(self):
        cmd = b.build_aircrack_cmd("/tmp/x.cap", "/tmp/wl.txt", "AA:BB:CC:DD:EE:FF")
        assert cmd[0] == "aircrack-ng"
        assert "-w" in cmd and "/tmp/wl.txt" in cmd
        assert "-b" in cmd and "AA:BB:CC:DD:EE:FF" in cmd
        assert cmd[-1] == "/tmp/x.cap"

    def test_aircrack_sem_bssid(self):
        cmd = b.build_aircrack_cmd("/tmp/x.cap", "/tmp/wl.txt")
        assert "-b" not in cmd


class TestParse:
    def test_key_found(self):
        found, pw = b.parse_aircrack_output(
            "Aircrack-ng 1.7\n\n  KEY FOUND! [ minhasenha123 ]\n\nMaster Key ...")
        assert found and pw == "minhasenha123"

    def test_nao_achou(self):
        found, pw = b.parse_aircrack_output(
            "Passphrase not in dictionary\n")
        assert not found and pw == ""

    def test_handshake_presente_ou_nao(self):
        assert not b.capture_has_handshake("No valid WPA handshakes found")
        assert b.capture_has_handshake("Reading packets... KEY FOUND! [ x ]")


class TestRunGuards:
    def test_captura_invalida(self, tmp_path):
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        r = b.run_audit("/nao/existe.cap", str(wl))
        assert not r.ran and "captura" in r.error.lower()

    def test_bssid_invalido(self, tmp_path):
        cap = tmp_path / "x.cap"; cap.write_bytes(b"\x00")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        r = b.run_audit(str(cap), str(wl), bssid="xx")
        assert not r.ran and "bssid" in r.error.lower()

    def test_ferramenta_ausente(self, tmp_path, monkeypatch):
        cap = tmp_path / "x.cap"; cap.write_bytes(b"\x00")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        monkeypatch.setattr(b, "aircrack_available", lambda: False)
        r = b.run_audit(str(cap), str(wl))
        assert not r.ran and "aircrack" in r.error.lower()

    def test_fluxo_sucesso_wireado(self, tmp_path, monkeypatch):
        cap = tmp_path / "x.cap"; cap.write_bytes(b"\x00")
        wl = tmp_path / "wl.txt"; wl.write_text("minhasenha123\n")
        monkeypatch.setattr(b, "aircrack_available", lambda: True)
        monkeypatch.setattr(b, "save_report", lambda r: None)
        monkeypatch.setattr(
            b.proc, "run",
            lambda cmd, timeout=0: (0, "KEY FOUND! [ minhasenha123 ]", ""))
        r = b.run_audit(str(cap), str(wl))
        assert r.ran and r.found and r.password == "minhasenha123"

    def test_sem_handshake_vira_erro(self, tmp_path, monkeypatch):
        cap = tmp_path / "x.cap"; cap.write_bytes(b"\x00")
        wl = tmp_path / "wl.txt"; wl.write_text("x\n")
        monkeypatch.setattr(b, "aircrack_available", lambda: True)
        monkeypatch.setattr(b, "save_report", lambda r: None)
        monkeypatch.setattr(
            b.proc, "run",
            lambda cmd, timeout=0: (1, "No valid WPA handshakes found", ""))
        r = b.run_audit(str(cap), str(wl))
        assert not r.ran and "handshake" in r.error.lower()


class TestExport:
    def test_texto_fraca(self):
        r = b.AuditResult(capture="/x/meu.cap", found=True, password="123")
        txt = b.result_to_text(r)
        assert "FRACA" in txt and "123" in txt

    def test_dict_nao_guarda_senha(self):
        r = b.AuditResult(capture="/x", found=True, password="segredo")
        assert "segredo" not in str(b.result_to_dict(r))


class TestRegistry:
    def test_wireless_pronto(self):
        from vigia_red.registry import MODULES
        m = next(m for m in MODULES if m.id == "wireless")
        assert m.status == "pronto"
        assert m.impl == "vigia_red.modules.wireless.page"
