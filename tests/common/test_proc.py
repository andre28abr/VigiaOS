"""Testes do wrapper de subprocesso vigia_common.proc.run.

Puro (não precisa gi). Usa comandos POSIX triviais (true/false/echo) que
existem em qualquer Linux/macOS, e monkeypatch para os caminhos de exceção.
"""

from __future__ import annotations

import subprocess

from vigia_common import proc


class TestRun:
    def test_sucesso_captura_stdout(self):
        rc, out, err = proc.run(["printf", "ola"])
        assert rc == 0
        assert out == "ola"
        assert err == ""

    def test_returncode_de_falha_preservado(self):
        rc, out, err = proc.run(["false"])
        assert rc != 0

    def test_stderr_capturado(self):
        # `ls` de um path inexistente escreve no stderr e sai != 0.
        rc, out, err = proc.run(["ls", "/caminho/que/nao/existe/vigia"])
        assert rc != 0
        assert err != ""

    def test_binario_inexistente_vira_tupla_de_falha(self):
        # FileNotFoundError -> (1, "", ""), nunca levanta.
        assert proc.run(["binario-vigia-que-nao-existe-zzz"]) == (1, "", "")

    def test_timeout_vira_tupla_de_falha(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        monkeypatch.setattr(subprocess, "run", boom)
        assert proc.run(["qualquer"], timeout=1) == (1, "", "")

    def test_oserror_generico_vira_tupla_de_falha(self, monkeypatch):
        # PermissionError/ENOMEM etc. (OSError != FileNotFound) tambem sao
        # engolidos -> contrato "nunca levanta".
        def boom(*a, **k):
            raise PermissionError("sem permissao")

        monkeypatch.setattr(subprocess, "run", boom)
        assert proc.run(["x"]) == (1, "", "")

    def test_timeout_repassado_ao_subprocess(self, monkeypatch):
        captured = {}

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake(*a, **k):
            captured["timeout"] = k.get("timeout")
            return _R()

        monkeypatch.setattr(subprocess, "run", fake)
        proc.run(["x"], timeout=7)
        assert captured["timeout"] == 7

    def test_cmd_e_lista_nunca_shell(self, monkeypatch):
        # Convenção de segurança: nunca shell=True.
        captured = {}

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake(cmd, *a, **k):
            captured["cmd"] = cmd
            captured["shell"] = k.get("shell", False)
            return _R()

        monkeypatch.setattr(subprocess, "run", fake)
        proc.run(["echo", "hi"])
        assert captured["cmd"] == ["echo", "hi"]
        assert captured["shell"] is False

    def test_saida_nao_utf8_nao_levanta(self):
        # Ferramenta externa imprime um nome de arquivo Latin-1 (vindo de
        # Windows, p.ex.). Antes: UnicodeDecodeError (ValueError) escapava
        # do wrapper e matava a thread de trabalho da GUI.
        import sys
        cmd = [sys.executable, "-c",
               "import sys; sys.stdout.buffer.write(b'caf\\xe9.pdf\\n')"]
        rc, out, err = proc.run(cmd, timeout=10)
        assert rc == 0
        assert out.startswith("caf")
        assert "\ufffd" in out  # byte inválido vira U+FFFD, não exceção

    def test_valueerror_vira_tupla_de_falha(self, monkeypatch):
        def boom(*a, **k):
            raise ValueError("argumento inválido")

        monkeypatch.setattr(subprocess, "run", boom)
        assert proc.run(["x"]) == (1, "", "")


class TestTerminate:
    def test_encerra_processo_comum(self):
        import sys
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        assert proc.terminate(p, grace=5) is True
        assert p.returncode is not None  # já fez wait()

    def test_none_nao_levanta(self):
        assert proc.terminate(None) is False

    def test_eperm_pede_pkexec_kill(self, monkeypatch):
        # Filho de pkexec roda como root: SIGTERM direto dá EPERM. O helper
        # então pede `pkexec kill` (e devolve o resultado dele).
        class Root:
            pid = 4242

            def terminate(self):
                raise PermissionError("Operation not permitted")

        chamado = {}

        def fake_kill(pid):
            chamado["pid"] = pid
            return True

        monkeypatch.setattr(proc, "_kill_elevated", fake_kill)
        assert proc.terminate(Root()) is True
        assert chamado["pid"] == 4242

    def test_kill_elevated_usa_pkexec_kill(self, monkeypatch):
        seen = {}

        def fake_run(cmd, **kw):
            seen["cmd"] = cmd

            class R:
                returncode = 0
            return R()

        monkeypatch.setattr(subprocess, "run", fake_run)
        assert proc._kill_elevated(99) is True
        assert seen["cmd"] == ["pkexec", "kill", "-TERM", "99"]

