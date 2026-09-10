"""Testes do runner cancelável do Red (vigia_red.runner.ScanProcess).

Puro (não precisa gi). Usa o próprio interpretador Python como "ferramenta"
externa para simular saídas.
"""

from __future__ import annotations

import sys

from vigia_red.runner import ScanProcess


class TestScanProcess:
    def test_captura_stdout_e_returncode(self):
        rc, out, err = ScanProcess().run(
            [sys.executable, "-c", "print('ok')"], timeout=10)
        assert rc == 0
        assert out.strip() == "ok"

    def test_saida_nao_utf8_nao_vira_erro_falso(self):
        # nmap/nuclei podem imprimir bytes fora do UTF-8 (banners, nomes).
        # Antes: UnicodeDecodeError caía no `except Exception` e virava
        # "código 1" sem saída — mascarando um scan bem-sucedido.
        cmd = [sys.executable, "-c",
               "import sys; sys.stdout.buffer.write(b'banner \\xff\\xfe\\n')"]
        rc, out, _ = ScanProcess().run(cmd, timeout=10)
        assert rc == 0
        assert out.startswith("banner ")
        assert "\ufffd" in out

    def test_binario_inexistente_vira_falha(self):
        assert ScanProcess().run(["/nao/existe/xyz"], timeout=5) == (1, "", "")

    def test_cancelado_antes_de_rodar_nao_executa(self):
        sp = ScanProcess()
        sp.cancel()
        assert sp.run([sys.executable, "-c", "print(1)"]) == (1, "", "")
