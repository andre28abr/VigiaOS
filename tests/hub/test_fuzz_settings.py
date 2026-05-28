"""Fuzz tests pro parser de settings do Vigia Hub (Etapa E — hardening)."""

from __future__ import annotations

from vigia_hub import settings

FUZZ_JSON = [
    "", "   ", "lixo {{{", "{", "null", "42", "3.14", '"str"', "true",
    "[]", "[1, 2, 3]", '[{"x": 1}]', "{}", '{"chave": "errada"}',
    '{"auto_lock_minutes": "abc"}',          # numerico como string
    '{"auto_lock_minutes": 9999}',           # fora do range (clamp)
    '{"theme": "roxo"}',                     # tema invalido
    '{"autostart": "sim", "show_tray": 1}',  # tipos esquisitos (bool coerce)
]


class TestLoadSettingsFuzz:
    def test_never_crashes(self, tmp_path, monkeypatch):
        p = tmp_path / "settings.json"
        monkeypatch.setattr(settings, "STATE_PATH", p)
        for payload in FUZZ_JSON:
            p.write_text(payload, encoding="utf-8")
            s = settings.load_settings()
            assert isinstance(s, settings.Settings), f"payload quebrou: {payload!r}"
            # auto_lock sempre clampado em [0, 120]
            assert 0 <= s.auto_lock_minutes <= 120
            # theme sempre normalizado
            assert s.theme in ("system", "light", "dark")

    def test_missing_file_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "STATE_PATH", tmp_path / "naoexiste.json")
        s = settings.load_settings()
        assert isinstance(s, settings.Settings)

    def test_valid_settings_parsed(self, tmp_path, monkeypatch):
        p = tmp_path / "settings.json"
        monkeypatch.setattr(settings, "STATE_PATH", p)
        p.write_text(
            '{"autostart": true, "auto_lock_minutes": 15, "password_lock": true}',
            encoding="utf-8",
        )
        s = settings.load_settings()
        assert s.autostart is True
        assert s.auto_lock_minutes == 15
        assert s.password_lock is True
