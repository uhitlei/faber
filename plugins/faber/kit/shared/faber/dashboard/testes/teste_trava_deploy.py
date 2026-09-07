#!/usr/bin/env python3
# =============================================================================
# teste_trava_deploy.py — prova que a trava de deploy FALHA quando deve.
#
# Uma trava que nunca foi vista falhando não é trava, é decoração. Cada
# cenário de vazamento aqui é montado de propósito num dist/ falso.
# =============================================================================
"""Testes de faber/dashboard/trava_deploy.py."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trava_deploy  # noqa: E402

RAIZ_REAL = Path(trava_deploy.__file__).resolve().parents[2]


class BaseTrava(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="teste-trava-"))
        self.dist = self.tmp / "dist"
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text(
            "<!doctype html><html><body><div id=root></div></body></html>", encoding="utf-8")
        (self.dist / "assets" / "index-abc123.js").write_text(
            "const app=()=>'Produto Exemplo';export default app;", encoding="utf-8")
        (self.dist / "assets" / "Dashboard-def456.js").write_text(
            "// tela de dashboard do PRODUTO — não é o dashboard da fábrica\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TesteArtefatoLimpo(BaseTrava):
    def test_build_normal_passa(self):
        self.assertEqual(trava_deploy.verificar_artefato(self.dist), [])

    def test_nome_dashboard_do_produto_nao_e_falso_positivo(self):
        """O produto tem telas de admin; procurar a palavra 'dashboard' geraria
        alarme falso. A trava procura o canário, não a palavra."""
        self.assertEqual(trava_deploy.verificar_artefato(self.dist), [])
        self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.dist)]), 0)


class TesteArtefatoContaminado(BaseTrava):
    def test_canario_no_bundle_falha(self):
        (self.dist / "assets" / "vendor-xyz.js").write_text(
            "/* %s */ const x=1;" % trava_deploy.CANARIO, encoding="utf-8")
        violacoes = trava_deploy.verificar_artefato(self.dist)
        self.assertEqual(len(violacoes), 1)
        self.assertIn("canário", violacoes[0])
        self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.dist)]), 2)

    def test_arquivo_de_faber_copiado_para_o_artefato_falha(self):
        alvo = self.dist / "faber" / "dashboard"
        alvo.mkdir(parents=True)
        shutil.copy(RAIZ_REAL / "faber" / "dashboard" / "leitor.py", alvo / "leitor.py")
        violacoes = trava_deploy.verificar_artefato(self.dist)
        self.assertTrue(any("dentro do artefato" in v for v in violacoes))
        self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.dist)]), 2)

    def test_template_do_dashboard_servido_como_html_falha(self):
        shutil.copy(RAIZ_REAL / "faber" / "dashboard" / "templates" / "base.html",
                    self.dist / "faber-dashboard.html")
        self.assertTrue(trava_deploy.verificar_artefato(self.dist))

    def test_fonte_do_dashboard_no_artefato_falha_seja_qual_for_a_extensao(self):
        """Se o canário fosse procurado só nas extensões de uma lista de TEXTO,
        um dist/assets/leitor.py com o canário dentro passaria batido."""
        for nome in ("leitor.py", "notas.md", "config.yaml", "LEIAME", "app.tsx"):
            (self.dist / "assets" / nome).write_text(
                "canario: %s\n" % trava_deploy.CANARIO, encoding="utf-8")
            violacoes = trava_deploy.verificar_artefato(self.dist)
            self.assertTrue(any("canário" in v and nome in v for v in violacoes), nome)
            self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.dist)]), 2)
            (self.dist / "assets" / nome).unlink()

    def test_referencia_de_caminho_em_fonte_tsx_no_artefato_falha(self):
        (self.dist / "assets" / "x.tsx").write_text(
            "import x from '/faber/dashboard/leitor.py';", encoding="utf-8")
        violacoes = trava_deploy.verificar_artefato(self.dist)
        self.assertTrue(any("referência a faber/dashboard" in v for v in violacoes))

    def test_binario_pulado_e_declarado_e_nao_engolido(self):
        """O que a trava NÃO lê tem que aparecer: limite declarado, jamais inferido."""
        (self.dist / "assets" / "logo.png").write_bytes(trava_deploy.CANARIO.encode())
        ignorados = []
        self.assertEqual(trava_deploy.verificar_artefato(self.dist, ignorados), [])
        self.assertIn("assets/logo.png", ignorados)

    def test_arquivo_acima_do_limite_e_declarado(self):
        grande = self.dist / "assets" / "enorme.js"
        grande.write_bytes(b"x" * (trava_deploy.LIMITE_BYTES + 1))
        ignorados = []
        trava_deploy.verificar_artefato(self.dist, ignorados)
        self.assertIn("assets/enorme.js", ignorados)

    def test_referencia_de_caminho_no_bundle_falha(self):
        (self.dist / "assets" / "chunk.js").write_text(
            "fetch('/faber/dashboard/leitor.py')", encoding="utf-8")
        violacoes = trava_deploy.verificar_artefato(self.dist)
        self.assertTrue(any("referência a faber/dashboard" in v for v in violacoes))


class TesteBancoDeTelemetria(BaseTrava):
    """TASK-123: o banco local não carrega o canário — guarda números,
    `sessionId` e branches. Nenhuma das outras regras o pegaria, e é o pior
    arquivo possível para vazar num site público."""

    def test_banco_de_telemetria_no_artefato_falha(self):
        (self.dist / "assets" / "telemetria.sqlite").write_bytes(b"SQLite format 3\x00")
        violacoes = trava_deploy.verificar_artefato(self.dist)
        self.assertEqual(len(violacoes), 1)
        self.assertIn("banco de telemetria", violacoes[0])
        self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.dist)]), 2)

    def test_wal_do_banco_tambem_falha(self):
        (self.dist / "telemetria.sqlite-wal").write_bytes(b"\x37\x7f\x06\x82")
        self.assertEqual(len(trava_deploy.verificar_artefato(self.dist)), 1)


class TesteFontesDoBuild(BaseTrava):
    def test_fonte_que_importa_o_dashboard_falha(self):
        src = self.tmp / "src"
        src.mkdir()
        (src / "App.tsx").write_text("import x from '../faber/dashboard/app.py';", encoding="utf-8")
        violacoes = trava_deploy.verificar_fontes(self.tmp)
        self.assertEqual(len(violacoes), 1)
        self.assertIn("App.tsx", violacoes[0])

    def test_asset_publico_com_canario_falha(self):
        publico = self.tmp / "public"
        publico.mkdir()
        (publico / "sobre.txt").write_text(trava_deploy.CANARIO, encoding="utf-8")
        self.assertTrue(trava_deploy.verificar_fontes(self.tmp))


class TesteDistAusente(BaseTrava):
    def test_sem_dist_e_nao_executado_nao_e_aprovacao(self):
        """Ferramenta/artefato ausente = 'não executado' explícito (regra da fábrica)."""
        self.assertEqual(trava_deploy.main(["--raiz", str(self.tmp), "--dist", str(self.tmp / "nao-existe")]), 1)


class TesteRepositorioReal(unittest.TestCase):
    def test_fontes_do_produto_nao_referenciam_o_dashboard(self):
        self.assertEqual(trava_deploy.verificar_fontes(RAIZ_REAL), [])

    def test_dashboard_tem_o_canario_plantado(self):
        """Se alguém apagar o canário, a trava vira decoração — isto avisa."""
        base = RAIZ_REAL / "faber" / "dashboard"
        for arquivo in ("app.py", "leitor.py", "static/dashboard.css", "templates/base.html"):
            texto = (base / arquivo).read_text(encoding="utf-8")
            self.assertIn(trava_deploy.CANARIO, texto, arquivo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
