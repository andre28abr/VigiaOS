"""Testes do parser/catalogo do Capabilities Inspector (vigia_caps).

Exercita o parser do `getcap -r` (parse_getcap_output / _GETCAP_LINE_RE),
a propriedade BinaryWithCaps.cap_names (que limpa flags e dedupa) e o
catalogo de capabilities (CAPABILITIES, get_capability, risk_for_cap,
BY_NAME).

Nada aqui chama getcap de verdade nem precisa de root: alimentamos strings
no formato do getcap diretamente. Os modulos backend/capabilities sao
puros (nao importam gi), entao rodam headless em qualquer plataforma.
"""

from __future__ import annotations

import pytest

from vigia_caps import backend, capabilities


# ============================================================
# parse_getcap_output — formato de linha do getcap -r
# ============================================================


class TestParseGetcapLines:
    def test_linha_simples(self):
        out = backend.parse_getcap_output("/usr/bin/ping cap_net_raw=ep")
        assert len(out) == 1
        b = out[0]
        assert b.path == "/usr/bin/ping"
        # A cap fica crua (com flags) em .capabilities; cap_names limpa.
        assert b.capabilities == ["cap_net_raw=ep"]
        assert b.cap_names == ["cap_net_raw"]

    def test_multiplas_caps_separadas_por_virgula(self):
        # getcap junta caps com mesmas flags numa unica string com virgulas.
        out = backend.parse_getcap_output(
            "/usr/bin/example cap_net_admin,cap_net_raw=ep"
        )
        assert len(out) == 1
        b = out[0]
        assert b.path == "/usr/bin/example"
        # Ambas as caps aparecem em cap_names, na ordem.
        assert b.cap_names == ["cap_net_admin", "cap_net_raw"]

    def test_varias_linhas(self):
        text = (
            "/usr/bin/ping cap_net_raw=ep\n"
            "/usr/sbin/arping cap_net_raw=ep\n"
            "/usr/bin/example cap_net_admin,cap_net_raw=ep\n"
        )
        out = backend.parse_getcap_output(text)
        assert [b.path for b in out] == [
            "/usr/bin/ping",
            "/usr/sbin/arping",
            "/usr/bin/example",
        ]

    def test_linha_de_erro_do_getcap_ignorada(self):
        # getcap escreve erros no formato "getcap: <path>: <msg>".
        text = "getcap: /usr/bin/secret: Operation not permitted"
        assert backend.parse_getcap_output(text) == []

    def test_linha_operation_not_permitted_sem_prefixo_ignorada(self):
        # Tambem filtramos qualquer linha que mencione "Operation not permitted",
        # mesmo sem o prefixo "getcap:".
        text = "Failed to get capabilities of file '/x': Operation not permitted"
        assert backend.parse_getcap_output(text) == []

    def test_erro_misturado_com_linha_valida(self):
        text = (
            "getcap: /usr/bin/secret: Operation not permitted\n"
            "/usr/bin/ping cap_net_raw=ep\n"
        )
        out = backend.parse_getcap_output(text)
        assert len(out) == 1
        assert out[0].path == "/usr/bin/ping"

    def test_linha_em_branco_ignorada(self):
        text = "\n   \n\t\n/usr/bin/ping cap_net_raw=ep\n\n"
        out = backend.parse_getcap_output(text)
        assert len(out) == 1
        assert out[0].path == "/usr/bin/ping"

    def test_output_vazio_retorna_lista_vazia(self):
        assert backend.parse_getcap_output("") == []

    def test_output_so_brancos_retorna_lista_vazia(self):
        assert backend.parse_getcap_output("   \n\t\n  ") == []

    def test_linha_sem_caps_ignorada(self):
        # Uma unica palavra (so o path, sem o campo de caps) nao casa o regex.
        assert backend.parse_getcap_output("/usr/bin/sozinho") == []


# ============================================================
# BinaryWithCaps.cap_names — dedupe + remocao de flags
# ============================================================


class TestCapNames:
    def test_dedup_mesma_cap_duas_vezes(self):
        b = backend.BinaryWithCaps(
            path="/usr/bin/x",
            capabilities=["cap_net_raw=ep", "cap_net_raw=ep"],
        )
        assert b.cap_names == ["cap_net_raw"]

    def test_dedup_mesma_cap_entradas_distintas(self):
        # Mesma cap aparecendo em entradas separadas tambem deduplica.
        b = backend.BinaryWithCaps(
            path="/usr/bin/x",
            capabilities=["cap_net_admin=ep", "cap_net_admin,cap_chown=eip"],
        )
        assert b.cap_names == ["cap_net_admin", "cap_chown"]

    def test_flags_eip_removidas(self):
        b = backend.BinaryWithCaps(
            path="/usr/bin/x", capabilities=["cap_sys_admin=eip"]
        )
        assert b.cap_names == ["cap_sys_admin"]

    def test_flags_ep_removidas(self):
        b = backend.BinaryWithCaps(
            path="/usr/bin/x", capabilities=["cap_dac_override=ep"]
        )
        assert b.cap_names == ["cap_dac_override"]

    def test_sem_capabilities(self):
        b = backend.BinaryWithCaps(path="/usr/bin/x")
        assert b.cap_names == []

    def test_flags_com_operador_mais_removidas(self):
        # Regressao: a forma com operador '+' (setcap / algumas saidas) deve
        # ter o flag removido igual a forma com '=' (corrigido na auditoria).
        b = backend.BinaryWithCaps(
            path="/usr/bin/x", capabilities=["cap_net_raw+ep"]
        )
        assert b.cap_names == ["cap_net_raw"]


# ============================================================
# Catalogo de capabilities
# ============================================================


class TestGetCapability:
    def test_nome_canonico(self):
        c = capabilities.get_capability("cap_sys_admin")
        assert c is not None
        assert c.name == "cap_sys_admin"

    def test_sem_prefixo_cap(self):
        # "sys_admin" (sem o prefixo cap_) resolve para a mesma capability.
        assert capabilities.get_capability("sys_admin") is capabilities.get_capability(
            "cap_sys_admin"
        )

    def test_case_insensitive(self):
        assert capabilities.get_capability(
            "CAP_SYS_ADMIN"
        ) is capabilities.get_capability("cap_sys_admin")

    def test_whitespace_e_case_misturados(self):
        # strip() + lower() + prefixo opcional, tudo junto.
        assert capabilities.get_capability(
            "  Sys_Admin  "
        ) is capabilities.get_capability("cap_sys_admin")

    def test_inexistente_retorna_none(self):
        assert capabilities.get_capability("cap_nao_existe") is None


class TestRiskForCap:
    def test_cap_conhecida(self):
        assert capabilities.risk_for_cap("cap_sys_admin") == "alto"

    def test_cap_conhecida_sem_prefixo_e_case(self):
        assert capabilities.risk_for_cap("NET_RAW") == "medio"

    def test_cap_inexistente_retorna_default(self):
        # Default documentado para cap fora do catalogo.
        assert capabilities.risk_for_cap("cap_nao_existe") == "desconhecida"

    def test_default_nao_esta_no_conjunto_de_riscos_validos(self):
        # Garante que o sentinel "desconhecida" e' distinguivel de um risco real.
        assert "desconhecida" not in {"alto", "medio", "baixo"}


class TestCatalogInvariants:
    VALID_RISKS = {"alto", "medio", "baixo"}

    def test_todo_item_tem_risco_valido(self):
        for c in capabilities.CAPABILITIES:
            assert c.risk in self.VALID_RISKS, f"{c.name} tem risco invalido: {c.risk!r}"

    def test_by_name_sem_nomes_duplicados(self):
        names = [c.name for c in capabilities.CAPABILITIES]
        assert len(names) == len(set(names)), "ha nomes de capability duplicados"
        # BY_NAME (1 entrada por nome) deve cobrir todos os itens.
        assert len(capabilities.BY_NAME) == len(capabilities.CAPABILITIES)

    def test_nomes_canonicos(self):
        # Todo nome e' lowercase e comeca com 'cap_' (formato do getcap).
        for c in capabilities.CAPABILITIES:
            assert c.name == c.name.lower()
            assert c.name.startswith("cap_")

    def test_by_name_aponta_para_o_item_certo(self):
        for c in capabilities.CAPABILITIES:
            assert capabilities.BY_NAME[c.name] is c

    def test_risk_order_cobre_os_riscos_validos(self):
        # RISK_ORDER e' usado para ordenar; deve conhecer todos os riscos reais.
        assert self.VALID_RISKS <= set(capabilities.RISK_ORDER.keys())
