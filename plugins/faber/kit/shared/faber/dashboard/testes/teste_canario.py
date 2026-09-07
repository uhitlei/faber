#!/usr/bin/env python3
# =============================================================================
# teste_canario.py — a trava de privacidade da persistência.
# RN-2 / AC-3 (BLOQUEANTE) + AC-14 (o tailer não escreve na fonte que lê).
#
# Por que este arquivo existe, e por que ele é assim (três fatos medidos no
# SQLite):
#
#   1. O SQLite grava TEXT em CLARO — `grep` de bytes acha a isca. Provado
#      aqui pelo CONTROLE POSITIVO, que roda ANTES da varredura real: sem ele,
#      um erro de encoding no detector devolveria "zero ocorrências" sem ter
#      testado coisa alguma. Zero que não sabe achar nada não é zero.
#   2. Com WAL e sem checkpoint, a isca vive SÓ no arquivo `-wal` (medido: 0
#      ocorrências no `.sqlite`, 1 no `-wal`). Varrer só o `.sqlite` daria
#      FALSO VERDE — daí a varredura em dobro (conexão aberta e após close).
#   3. `DELETE` + checkpoint NÃO apaga os bytes (páginas livres guardam o
#      conteúdo antigo). Logo "gravar e limpar depois" é inaceitável: a única
#      garantia possível é NUNCA GRAVAR — que é o que `telemetria.Evento`
#      torna estrutural (não tem campo de conteúdo) e a lista branca de
#      `banco.py` torna auditável.
#
# Falha (b) = isca encontrada. Falha (c) = pipeline não processou a
# fixture: o resultado é INCONCLUSIVO, nunca "passou" — por isso as asserções
# de contagem/soma vêm antes das de ausência.
# =============================================================================
"""Canário de privacidade da persistência (AC-3) e travas de escrita (AC-14)."""

import ast
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))

import banco  # noqa: E402
import telemetria  # noqa: E402
from teste_telemetria import TASKS, REPO, SLUG  # noqa: E402

SUFIXOS = ("", "-wal", "-shm", "-journal")


def varrer(caminho_banco, iscas):
    """Detector: conta ocorrências de cada isca nos BYTES do banco e auxiliares.

    Dump binário do arquivo inteiro, nunca `SELECT` coluna a coluna — `SELECT`
    cobriria só o schema conhecido, e o vazamento que interessa é justamente o
    que escapa dele (página livre, índice, nome de coluna, journal).
    """
    achados = {}
    for sufixo in SUFIXOS:
        arquivo = Path(str(caminho_banco) + sufixo)
        if not arquivo.exists():
            continue
        dados = arquivo.read_bytes()
        for nome, isca in iscas.items():
            n = dados.count(isca.encode("utf-8"))
            if n:
                achados["%s@%s" % (nome, arquivo.name)] = n
    return achados


def linha_com_isca(request_id, iscas, onde, saida=100):
    """Linha de transcript VÁLIDA (usage/requestId/gitBranch/timestamp/sessionId)
    carregando a isca no lugar `onde`. Válida de propósito: linha pulada não
    prova nada."""
    conteudo = [{"type": "text", "text": "resposta"}]
    dados = {
        "type": "assistant",
        "requestId": request_id,
        "sessionId": "sessao-canario",
        "gitBranch": "feature/TASK-123",
        "timestamp": "2026-08-15T12:00:00+00:00",
        "attributionAgent": "senior-developer",
        "message": {
            "model": "claude-opus-5",
            "content": conteudo,
            "usage": {"input_tokens": 10, "output_tokens": saida,
                      "cache_creation_input_tokens": 5, "cache_read_input_tokens": 7},
        },
    }
    if onde == "text":
        conteudo[0]["text"] = "resposta com %s no meio" % iscas["text"]
    elif onde == "thinking":
        conteudo.insert(0, {"type": "thinking", "thinking": iscas["thinking"]})
    elif onde == "tool_use":
        conteudo.append({"type": "tool_use", "name": "Bash",
                         "input": {"command": "echo %s" % iscas["tool_use"]}})
    elif onde == "toolUseResult":
        dados["toolUseResult"] = {"stdout": iscas["toolUseResult"], "stderr": ""}
    return json.dumps(dados).encode("utf-8")


class TesteCanario(unittest.TestCase):
    """AC-3 — bloqueante. Nenhuma entrega é aceita sem este teste verde."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="canario-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Nonce por RODADA: isca fixa mascararia falso negativo com resíduo de
        # uma execução anterior.
        nonce = uuid.uuid4().hex
        self.iscas = {onde: "CANARIO_QA_%s_%s" % (onde.upper(), nonce)
                      for onde in ("text", "thinking", "tool_use", "toolUseResult")}
        self.projetos = self.tmp / "projects"
        alvo = self.projetos / SLUG
        alvo.mkdir(parents=True)
        (alvo / "sessao.jsonl").write_bytes(b"\n".join(
            linha_com_isca("req-%d" % i, self.iscas, onde, saida=100)
            for i, onde in enumerate(self.iscas)) + b"\n")
        self.banco = self.tmp / "telemetria.sqlite"

    def test_controle_positivo_o_detector_acha_a_isca(self):
        """Pré-requisito: detector que não acha nada passa vazio."""
        scratch = self.tmp / "scratch.sqlite"
        con = sqlite3.connect(str(scratch))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE t (v TEXT)")
        for isca in self.iscas.values():
            con.execute("INSERT INTO t (v) VALUES (?)", (isca,))
        con.commit()
        aberto = varrer(scratch, self.iscas)
        con.close()
        fechado = varrer(scratch, self.iscas)
        self.assertTrue(aberto, "detector não achou a isca com a conexão ABERTA (WAL)")
        self.assertTrue(fechado, "detector não achou a isca após close()")
        self.assertEqual(len(self.iscas), 4)

    def test_isca_nao_aparece_em_nenhum_byte_do_banco(self):  # AC-3 — bloqueante
        con = banco.abrir(self.banco)
        resultado = banco.sincronizar(con, REPO, TASKS, self.projetos)

        # (c) prova independente de que a fixture FOI processada. Sem isto,
        # "zero ocorrências" é inconclusivo, não "passou".
        self.assertEqual(resultado["arquivos"], 1)
        self.assertEqual(resultado["eventos"], 4, "as 4 linhas com isca não foram processadas")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM requisicao").fetchone()[0], 4)
        self.assertEqual(con.execute("SELECT SUM(saida) FROM requisicao").fetchone()[0], 400)

        # (1ª varredura) conexão ABERTA: é aqui que o WAL está populado
        aberto = varrer(self.banco, self.iscas)
        con.close()
        # (2ª varredura) após close(): arquivo principal + resíduo de WAL/SHM
        fechado = varrer(self.banco, self.iscas)

        self.assertEqual(aberto, {}, "isca encontrada com a conexão aberta: %s" % aberto)
        self.assertEqual(fechado, {}, "isca encontrada após close(): %s" % fechado)

    def test_conteudo_exibido_ao_vivo_continua_fora_do_banco(self):
        """RN-1 × RN-2: o mesmo conteúdo que a tela mostra não pode ser retido.

        Prova as duas metades juntas — se a exibição parasse de funcionar, o
        canário passaria por vacuidade.
        """
        con = banco.abrir(self.banco)
        banco.sincronizar(con, REPO, TASKS, self.projetos)
        caminho = banco.transcripts_da_demanda(con, "TASK-123")[0]
        mensagens = telemetria.mensagens_do_arquivo(caminho, "TASK-123", TASKS)
        exibido = " ".join(m.texto for m in mensagens)
        self.assertIn(self.iscas["text"], exibido, "a exibição ao vivo (RN-1) parou de funcionar")
        self.assertNotIn(self.iscas["thinking"], exibido, "thinking nunca é exibido")
        con.close()
        self.assertEqual(varrer(self.banco, self.iscas), {})

    def test_nenhuma_isca_no_dump_textual_de_todas_as_tabelas(self):
        """Segunda opinião do mesmo fato, por um caminho independente do grep
        de bytes: `iterdump()` percorre schema + dados de todas as tabelas."""
        con = banco.abrir(self.banco)
        banco.sincronizar(con, REPO, TASKS, self.projetos)
        despejo = "\n".join(con.iterdump())
        con.close()
        for onde, isca in self.iscas.items():
            self.assertNotIn(isca, despejo, "isca de %s apareceu no dump SQL" % onde)


class TesteTravasDeEscrita(unittest.TestCase):
    """AC-14: o tailer lê a fonte; não escreve nela, nem em artefato da fábrica."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trava-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.projetos = self.tmp / "projects"
        alvo = self.projetos / SLUG
        (alvo / "sessao" / "subagents").mkdir(parents=True)
        linha = linha_com_isca("req-1", {"text": "x"}, "text")
        (alvo / "sessao.jsonl").write_bytes(linha + b"\n")
        (alvo / "sessao" / "subagents" / "agent-a1.jsonl").write_bytes(linha + b"\n")

    def impressao(self):
        """Impressão digital (sha256 + tamanho + mtime_ns), a mesma do teste do Kanban."""
        itens = []
        for p in sorted(self.projetos.rglob("*")):
            if p.is_file():
                st = p.stat()
                itens.append((str(p), st.st_size, st.st_mtime_ns,
                              hashlib.sha256(p.read_bytes()).hexdigest()))
            else:
                itens.append((str(p), None, None, None))
        return itens

    def test_varredura_nao_escreve_nos_transcripts(self):  # AC-14
        antes = self.impressao()
        con = banco.abrir(self.tmp / "t.sqlite")
        banco.sincronizar(con, REPO, TASKS, self.projetos)
        banco.sincronizar(con, REPO, TASKS, self.projetos)
        con.close()
        self.assertEqual(antes, self.impressao())

    def test_nenhum_arquivo_novo_na_pasta_de_projetos(self):
        antes = {str(p) for p in self.projetos.rglob("*")}
        con = banco.abrir(self.tmp / "t.sqlite")
        banco.sincronizar(con, REPO, TASKS, self.projetos)
        con.close()
        self.assertEqual({str(p) for p in self.projetos.rglob("*")}, antes)


class TesteTravasEstaticas(unittest.TestCase):
    """A lista branca só é auditável se `sqlite3` tiver um dono só.

    A trava usa **AST**, não regex. O regex antigo casava
    só `^\\s*import sqlite3`: `from sqlite3 import connect`, `import sqlite3 as
    db`, um import indentado dentro de uma função ou `__import__("sqlite3")`
    passavam limpos. Não havia violação — era a trava do futuro que estava
    frouxa, e trava frouxa costuma ser descoberta depois do dano.
    """

    def modulos(self):
        return sorted(p for p in AQUI.parent.glob("*.py"))

    def importa(self, caminho, alvo):
        """Todo jeito de trazer um módulo para dentro do arquivo."""
        arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                if any(a.name == alvo or a.name.startswith(alvo + ".") for a in no.names):
                    return True
            elif isinstance(no, ast.ImportFrom):
                if no.module == alvo or (no.module or "").startswith(alvo + "."):
                    return True
            # import dinâmico: __import__("sqlite3") / importlib.import_module("sqlite3")
            elif isinstance(no, ast.Call):
                nome = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
                if nome in ("__import__", "import_module"):
                    for arg in no.args:
                        if isinstance(arg, ast.Constant) and arg.value == alvo:
                            return True
        return False

    def test_somente_banco_importa_sqlite3(self):
        importam = [p.name for p in self.modulos() if self.importa(p, "sqlite3")]
        self.assertEqual(importam, ["banco.py"],
                         "sqlite3 fora de banco.py fura a lista branca da RN-2")

    def test_telemetria_nao_conhece_persistencia(self):
        alvo = AQUI.parent / "telemetria.py"
        self.assertFalse(self.importa(alvo, "sqlite3"))
        self.assertFalse(self.importa(alvo, "banco"))

    def test_a_propria_trava_pega_as_formas_disfarcadas(self):
        """Sem este teste, a trava acima poderia estar quebrada e ninguém saber:
        ela só afirma ausência, e ausência passa vazia."""
        disfarces = (
            "import sqlite3",
            "import sqlite3 as db",
            "from sqlite3 import connect",
            "from sqlite3.dbapi2 import connect",
            "def f():\n    import sqlite3\n",
            'importlib.import_module("sqlite3")',
            '__import__("sqlite3")',
        )
        alvo = Path(tempfile.mkdtemp(prefix="trava-import-")) / "falso.py"
        self.addCleanup(shutil.rmtree, alvo.parent, ignore_errors=True)
        for fonte in disfarces:
            alvo.write_text(fonte, encoding="utf-8")
            self.assertTrue(self.importa(alvo, "sqlite3"), "trava não pegou: %r" % fonte)
        alvo.write_text("import json\nfrom pathlib import Path\n", encoding="utf-8")
        self.assertFalse(self.importa(alvo, "sqlite3"))

    def test_lista_branca_nao_tem_campo_de_conteudo(self):
        proibidos = {"content", "conteudo", "texto", "mensagem", "thinking", "text"}
        self.assertEqual(banco.CAMPOS_PERSISTIVEIS & proibidos, set())

    def test_evento_e_o_que_a_lista_branca_permite(self):
        """Todo campo do Evento (que vai para o banco) está na lista branca."""
        campos = set(telemetria.Evento._fields) - {"em"}  # `em` é gravado como `ultimo_em`
        self.assertEqual(campos - banco.CAMPOS_PERSISTIVEIS, set())

    def test_modulos_novos_tem_a_canario_da_trava_de_deploy(self):
        for nome in ("telemetria.py", "banco.py"):
            fonte = (AQUI.parent / nome).read_text(encoding="utf-8")
            self.assertIn("CANÁRIO-TRAVA-DEPLOY", fonte, "%s sem a marca da trava" % nome)


if __name__ == "__main__":
    unittest.main()
