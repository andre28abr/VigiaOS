"""Testes do modelo puro de notificações do sininho (vigia_common.notices).

Sem GTK — só dado. Roda no macOS/CI sem PyGObject.
"""

from __future__ import annotations

from vigia_common.notices import Notification, module_dep_notifications


class TestNotification:
    def test_defaults(self):
        n = Notification("título")
        assert n.title == "título"
        assert n.subtitle == ""
        assert n.icon  # tem um ícone default


class TestModuleDepNotifications:
    def test_vazio_quando_nada_faltando(self):
        assert module_dep_notifications([]) == []
        assert module_dep_notifications([("Vigia X", [])]) == []

    def test_uma_por_modulo_com_dep_faltando(self):
        notes = module_dep_notifications([
            ("Vigia Timeline", ["plaso"]),
            ("Vigia IDS", ["Suricata", "tcpdump"]),
        ])
        assert len(notes) == 2
        assert notes[0].title.startswith("Vigia Timeline")
        assert "plaso" in notes[0].subtitle
        assert "Suricata" in notes[1].subtitle and "tcpdump" in notes[1].subtitle

    def test_filtra_labels_vazios(self):
        notes = module_dep_notifications([("M", ["", None, "x"])])
        assert len(notes) == 1
        assert notes[0].subtitle == "Instale: x"

    def test_icone_de_aviso(self):
        notes = module_dep_notifications([("M", ["x"])])
        assert notes[0].icon == "dialog-warning-symbolic"
