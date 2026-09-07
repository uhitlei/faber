#!/usr/bin/env python3
# =============================================================================
# teste_banco.py — testes da persistência da telemetria.
# Cobre AC-4 (MAX por requestId), AC-5 (subagente soma), AC-6 (worktree),
# AC-7 (repo vizinho), AC-15 (desconto de arquivo removido e reaparecido),
# AC-12 (parcial não contamina o agregado) e a lista branca da RN-2.
#
# O teste que mais importa aqui é o da RN-9/AC-15: "duas leituras do mesmo
# estado produzem o mesmo número". Um acumulador mede 100 → 200 quando essa
# propriedade quebra, e a única razão de ela valer agora é o agregado ser
# derivado por SUM em vez de acumulado.
# =============================================================================
"""Testes de faber/dashboard/banco.py."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import banco  # noqa: E402
import telemetria  # noqa: E402
from teste_telemetria import TASKS, REPO, SLUG, linha  # noqa: E402


class BaseBanco(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="teste-banco-"))
        self.projetos = self.tmp / "projects"
        self.projetos.mkdir()
        self.con = banco.abrir(self.tmp / "dados" / "telemetria.sqlite")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.addCleanup(self.con.close)

    def transcript(self, nome, linhas, pasta=SLUG, final=b"\n"):
        caminho = self.projetos / pasta / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(b"\n".join(linhas) + final if linhas else b"")
        return caminho

    def sincronizar(self):
        return banco.sincronizar(self.con, REPO, TASKS, self.projetos)

    def saida(self, demanda="TASK-123"):
        return banco.tokens_por_demanda(self.con).get(demanda, {}).get("saida", 0)


class TesteEsquema(BaseBanco):
    """RN-2: a lista branca é o esquema, e o esquema é a lista branca."""

    def test_colunas_do_banco_estao_todas_na_lista_branca(self):
        fora = banco.colunas(self.con) - banco.CAMPOS_PERSISTIVEIS
        self.assertEqual(fora, set(), "coluna fora da lista branca da RN-2: %s" % fora)

    def test_tabela_nova_entra_na_conferencia_por_construcao(self):
        """A lista de tabelas vem do `sqlite_master`, não de um literal: uma
        tabela criada amanhã é conferida sem ninguém lembrar de nada."""
        self.assertEqual(sorted(banco.tabelas(self.con)), ["arquivo", "requisicao"])
        self.con.execute("CREATE TABLE cache_de_saida (texto TEXT)")
        self.assertIn("cache_de_saida", banco.tabelas(self.con))
        self.assertIn("texto", banco.colunas(self.con))
        self.assertIn("texto", banco.colunas(self.con) - banco.CAMPOS_PERSISTIVEIS)

    def test_nenhuma_coluna_de_conteudo(self):
        suspeitas = {"content", "conteudo", "texto", "mensagem", "thinking", "output_texto"}
        self.assertEqual(banco.colunas(self.con) & suspeitas, set())

    def test_versao_do_esquema_gravada(self):
        self.assertEqual(self.con.execute("PRAGMA user_version").fetchone()[0],
                         banco.VERSAO_ESQUEMA)

    def test_versao_diferente_apaga_e_reconstroi(self):
        caminho = self.tmp / "outro.sqlite"
        con = banco.abrir(caminho)
        con.execute("INSERT INTO requisicao (caminho, request_id, provedor) VALUES ('x','r','p')")
        con.execute("PRAGMA user_version=99")
        con.commit()
        con.close()
        con = banco.abrir(caminho)
        self.addCleanup(con.close)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM requisicao").fetchone()[0], 0)
        self.assertEqual(con.execute("PRAGMA user_version").fetchone()[0], banco.VERSAO_ESQUEMA)

    def test_banco_corrompido_levanta_erro_de_telemetria(self):
        caminho = self.tmp / "corrompido.sqlite"
        caminho.write_bytes(b"isto nao e um banco sqlite" * 500)
        with self.assertRaises(banco.ErroTelemetria):
            con = banco.abrir(caminho)
            banco.sincronizar(con, REPO, TASKS, self.projetos)


class TesteDedup(BaseBanco):
    """AC-4: MAX dentro do requestId; soma normal ENTRE requestIds diferentes."""

    def test_mesmo_request_id_repetido_usa_max_nunca_soma(self):  # AC-4 (positivo)
        self.transcript("s.jsonl", [
            linha(request_id="r1", saida=100, entrada=10),
            linha(request_id="r1", saida=100, entrada=10),
            linha(request_id="r1", saida=100, entrada=10),
        ])
        self.sincronizar()
        self.assertEqual(self.saida(), 100)  # e não 300

    def test_valor_que_cresce_dentro_do_request_id_vence_pelo_maior(self):
        self.transcript("s.jsonl", [
            linha(request_id="r1", saida=40),
            linha(request_id="r1", saida=180),
            linha(request_id="r1", saida=180),
        ])
        self.sincronizar()
        self.assertEqual(self.saida(), 180)

    def test_request_ids_diferentes_somam(self):  # AC-4 (borda)
        self.transcript("s.jsonl", [linha(request_id="r1", saida=100),
                                    linha(request_id="r2", saida=50)])
        self.sincronizar()
        self.assertEqual(self.saida(), 150)

    def test_max_e_por_campo(self):
        self.transcript("s.jsonl", [
            linha(request_id="r1", saida=10, entrada=99, cache_criacao=5, cache_leitura=1),
            linha(request_id="r1", saida=80, entrada=1, cache_criacao=50, cache_leitura=900),
        ])
        self.sincronizar()
        t = banco.tokens_por_demanda(self.con)["TASK-123"]
        self.assertEqual((t["saida"], t["entrada"], t["cache_criacao"], t["cache_leitura"]),
                         (80, 99, 50, 900))

    def test_quatro_campos_ficam_separados_sem_total_unico(self):  # RN-10
        self.transcript("s.jsonl", [linha(request_id="r1", saida=1, entrada=2,
                                          cache_criacao=3, cache_leitura=4)])
        self.sincronizar()
        t = banco.tokens_por_demanda(self.con)["TASK-123"]
        self.assertNotIn("total", t)


class TesteCoberturaEAtribuicao(BaseBanco):
    """AC-5, AC-6, AC-7 no caminho completo (disco → banco)."""

    def test_subagente_soma_com_a_sessao_principal(self):  # AC-5 (positivo)
        self.transcript("s.jsonl", [linha(request_id="r1", saida=100)])
        self.transcript("s/subagents/agent-a1.jsonl", [linha(request_id="r2", saida=250)])
        self.sincronizar()
        self.assertEqual(self.saida(), 350)

    def test_worktree_atribui_a_demanda_certa(self):  # AC-6 (positivo)
        self.transcript("s.jsonl", [linha(request_id="r1", saida=70)],
                        pasta=SLUG + "--claude-worktrees-TASK-123")
        self.sincronizar()
        self.assertEqual(self.saida(), 70)

    def test_repositorio_vizinho_nao_soma(self):  # AC-7
        self.transcript("s.jsonl", [linha(request_id="r1", saida=100)])
        for vizinho in (SLUG + "-backup", SLUG + "-2", SLUG + "-old", SLUG + "x"):
            self.transcript("s.jsonl", [linha(request_id="v1", saida=7877)], pasta=vizinho)
        self.sincronizar()
        self.assertEqual(self.saida(), 100)

    def test_arquivo_multibranch_divide_o_consumo_entre_as_demandas(self):
        self.transcript("s.jsonl", [
            linha(request_id="r1", branch="feature/TASK-123", saida=100),
            linha(request_id="r2", branch="feature/TASK-92", saida=30),
            linha(request_id="r3", branch="develop", saida=999),
        ])
        self.sincronizar()
        tokens = banco.tokens_por_demanda(self.con)
        self.assertEqual(tokens["TASK-123"]["saida"], 100)
        self.assertEqual(tokens["TASK-92"]["saida"], 30)
        self.assertNotIn(None, tokens)
        self.assertEqual(banco.fora_de_demanda(self.con)["saida"], 999)  # KPI, não rateio

    def test_agentes_e_modelo_da_demanda(self):  # AC-10 / AC-13
        self.transcript("s.jsonl", [
            linha(request_id="r1", agente="qa", em="2026-08-15T11:00:00+00:00"),
            linha(request_id="r2", agente="senior-developer", em="2026-08-15T11:59:00+00:00"),
        ])
        self.sincronizar()
        self.assertEqual([a for a, _e in banco.agentes_da_demanda(self.con, "TASK-123")],
                         ["senior-developer", "qa"])
        self.assertEqual(banco.modelo_da_demanda(self.con, "TASK-123"), "claude-opus-5")

    def test_modelo_ausente_fica_sem_dados(self):  # AC-13 (positivo)
        self.transcript("s.jsonl", [linha(request_id="r1", modelo=None)])
        self.sincronizar()
        self.assertIsNone(banco.modelo_da_demanda(self.con, "TASK-123"))


class TesteRetencaoEIdempotencia(BaseBanco):
    """RN-9/AC-15 sob a decisão do Owner: RETÉM em vez de descontar.

    A garantia que importa não mudou de dono: ela nunca veio do desconto, e sim
    de NÃO HAVER ACUMULADOR. O total é `SUM` sobre linhas com `UPSERT MAX`, que
    é idempotente — é a recontagem sobre acumulador que produz o 100 → 200,
    não a retenção.
    """

    def test_duas_leituras_do_mesmo_estado_dao_o_mesmo_numero(self):  # AC-15
        self.transcript("s.jsonl", [linha(request_id="r1", saida=100)])
        self.sincronizar()
        primeiro = self.saida()
        self.sincronizar()
        self.assertEqual(self.saida(), primeiro)

    def test_arquivo_removido_e_marcado_e_o_total_nao_desconta(self):  # AC-15
        self.transcript("a.jsonl", [linha(request_id="r1", saida=100)])
        alvo = self.transcript("b.jsonl", [linha(request_id="r2", saida=60)])
        self.sincronizar()
        self.assertEqual(self.saida(), 160)

        alvo.unlink()
        resultado = self.sincronizar()
        self.assertEqual(resultado["removidos"], 1)
        # o total NÃO encolhe: tokens são registro durável do que foi medido
        self.assertEqual(self.saida(), 160)
        # e o arquivo fica marcado, para o conteúdo dele virar "sem dados"
        self.assertEqual(banco.removidos(self.con), {str(alvo)})

    def test_marcacao_nao_se_repete_a_cada_varredura(self):
        alvo = self.transcript("b.jsonl", [linha(request_id="r2", saida=60)])
        self.sincronizar()
        alvo.unlink()
        self.assertEqual(self.sincronizar()["removidos"], 1)
        self.assertEqual(self.sincronizar()["removidos"], 0)  # já estava marcado
        self.assertEqual(self.saida(), 60)

    def test_arquivo_que_some_e_volta_converge_para_as_mesmas_linhas(self):  # AC-15 (borda)
        self.transcript("a.jsonl", [linha(request_id="r1", saida=100)])
        alvo = self.transcript("b.jsonl", [linha(request_id="r2", saida=60)])
        self.sincronizar()
        antes = self.saida()
        requisicoes = self.con.execute("SELECT COUNT(*) FROM requisicao").fetchone()[0]

        guardado = alvo.read_bytes()
        alvo.unlink()
        self.sincronizar()
        self.assertEqual(self.saida(), antes)  # retido enquanto ausente

        alvo.write_bytes(guardado)
        resultado = self.sincronizar()
        self.assertEqual(resultado["voltaram"], 1)
        self.assertEqual(banco.removidos(self.con), set())  # marcação limpa
        # reprocessou do offset 0 e NÃO duplicou: MAX é idempotente
        self.assertEqual(self.saida(), antes)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM requisicao").fetchone()[0],
                         requisicoes)

    def test_linha_orfa_e_reatribuida_quando_a_demanda_passa_a_existir(self):
        """A demanda ainda não estava na projeção quando a linha foi lida —
        `state.yaml` ilegível no instante da leitura é modo de falha conhecido
        da fábrica. Sem reparo, o consumo ficava para sempre em "fora de
        demanda" e o card subcontava tokens em silêncio."""
        self.transcript("s.jsonl", [linha(request_id="r1", branch="feature/TASK-777",
                                          saida=100)])
        banco.sincronizar(self.con, REPO, TASKS, self.projetos)  # 777 desconhecida
        self.assertEqual(self.saida("TASK-777"), 0)
        self.assertEqual(banco.fora_de_demanda(self.con)["saida"], 100)

        # a demanda passa a existir; a varredura seguinte não relê o arquivo
        # (offset já avançou), mas repara as órfãs
        resultado = banco.sincronizar(self.con, REPO, TASKS | {"TASK-777"}, self.projetos)
        self.assertEqual(resultado["eventos"], 0, "não deveria ter relido o arquivo")
        self.assertEqual(resultado["reatribuidas"], 1)
        self.assertEqual(self.saida("TASK-777"), 100)
        self.assertEqual(banco.fora_de_demanda(self.con)["saida"], 0)

    def test_incremental_e_reconstrucao_do_zero_convergem(self):  # AC-15
        """O `rm -rf dados/` que o README chama de inócuo tem que ser inócuo
        mesmo: o número do incremental e o da reconstrução do zero têm de
        bater, inclusive quando a projeção mudou no meio do caminho."""
        self.transcript("a.jsonl", [linha(request_id="r1", branch="feature/TASK-777", saida=100)])
        banco.sincronizar(self.con, REPO, TASKS, self.projetos)  # 777 ainda desconhecida
        self.transcript("b.jsonl", [linha(request_id="r2", branch="feature/TASK-777", saida=60)])
        banco.sincronizar(self.con, REPO, TASKS | {"TASK-777"}, self.projetos)
        incremental = banco.tokens_por_demanda(self.con)

        do_zero = banco.abrir(self.tmp / "dados" / "outro.sqlite")
        self.addCleanup(do_zero.close)
        banco.sincronizar(do_zero, REPO, TASKS | {"TASK-777"}, self.projetos)
        self.assertEqual(incremental, banco.tokens_por_demanda(do_zero))
        self.assertEqual(incremental["TASK-777"]["saida"], 160)

    def test_branch_sem_demanda_continua_orfa(self):
        """O reparo não pode virar atribuição criativa: `develop` segue sem
        dono, que é o que o KPI 'fora de demanda' existe para mostrar."""
        self.transcript("s.jsonl", [linha(request_id="r1", branch="develop", saida=999)])
        self.sincronizar()
        self.assertEqual(self.sincronizar()["reatribuidas"], 0)
        self.assertEqual(banco.fora_de_demanda(self.con)["saida"], 999)

    def test_reprocessar_do_zero_nao_infla(self):
        """A listagem que falha por um tick — o modo de falha que mediu 100 → 200."""
        alvo = self.transcript("s.jsonl", [linha(request_id="r%d" % i, saida=10) for i in range(10)])
        self.sincronizar()
        antes = self.saida()
        guardado = alvo.read_bytes()
        alvo.unlink()
        self.sincronizar()
        alvo.write_bytes(guardado)
        self.sincronizar()
        self.assertEqual(self.saida(), antes)
        self.assertEqual(antes, 100)  # e não 200

    def test_linha_parcial_nao_contamina_o_agregado(self):  # AC-12 (borda)
        alvo = self.transcript("s.jsonl", [linha(request_id="r1", saida=100)])
        self.sincronizar()
        with alvo.open("ab") as fh:
            fh.write(json.dumps({"requestId": "r2", "gitBranch": "feature/TASK-123",
                                 "message": {"usage": {"output_tokens": 500}}})[:40].encode())
        self.sincronizar()
        self.assertEqual(self.saida(), 100)
        with alvo.open("ab") as fh:  # a linha se completa depois
            fh.write(json.dumps({"requestId": "r2", "gitBranch": "feature/TASK-123",
                                 "message": {"usage": {"output_tokens": 500}}})[40:].encode() + b"\n")
        self.sincronizar()
        self.assertEqual(self.saida(), 600)

    def test_append_incremental_soma_so_o_que_chegou(self):
        alvo = self.transcript("s.jsonl", [linha(request_id="r1", saida=100)])
        self.sincronizar()
        with alvo.open("ab") as fh:
            fh.write(linha(request_id="r2", saida=50) + b"\n")
        resultado = self.sincronizar()
        self.assertEqual(resultado["eventos"], 1)  # releu só a linha nova
        self.assertEqual(self.saida(), 150)

    def test_arquivo_recriado_com_outro_inode_relê_do_zero_e_soma_o_novo(self):
        """Rotação: mesmo nome, arquivo outro. Com retenção, as requisições antigas
        são retidas (foram medidas de verdade) e as novas se somam — o que não
        pode acontecer é o offset velho casar com conteúdo novo e produzir
        lixo."""
        alvo = self.transcript("s.jsonl", [linha(request_id="r1", saida=100),
                                           linha(request_id="r2", saida=100)])
        self.sincronizar()
        self.assertEqual(self.saida(), 200)
        alvo.unlink()
        self.transcript("s.jsonl", [linha(request_id="r9", saida=5)])
        self.sincronizar()
        self.assertEqual(self.saida(), 205)
        # e o `r9` foi lido de fato, não pulado por offset herdado
        self.assertEqual(
            self.con.execute("SELECT saida FROM requisicao WHERE request_id='r9'").fetchone()[0], 5)

    def test_transcripts_da_demanda_sao_ponteiros_para_reler(self):  # AC-11
        a = self.transcript("a.jsonl", [linha(request_id="r1", em="2026-08-15T10:00:00+00:00")])
        b = self.transcript("b.jsonl", [linha(request_id="r2", em="2026-08-15T11:00:00+00:00")])
        self.sincronizar()
        self.assertEqual(banco.transcripts_da_demanda(self.con, "TASK-123"), [str(b), str(a)])


class TestePersistencia(BaseBanco):
    """AC-11: processo novo, sem sessão viva — os tokens continuam lá."""

    def test_tokens_sobrevivem_a_reabertura_do_banco(self):
        self.transcript("s.jsonl", [linha(request_id="r1", saida=123)])
        self.sincronizar()
        self.con.close()
        con = banco.abrir(self.tmp / "dados" / "telemetria.sqlite")
        self.addCleanup(con.close)
        self.assertEqual(banco.tokens_por_demanda(con)["TASK-123"]["saida"], 123)

    def test_tokens_continuam_mesmo_com_o_transcript_apagado(self):  # AC-11 (borda)
        alvo = self.transcript("s.jsonl", [linha(request_id="r1", saida=123)])
        self.sincronizar()
        self.con.close()
        alvo.unlink()
        con = banco.abrir(self.tmp / "dados" / "telemetria.sqlite")
        self.addCleanup(con.close)
        # sem varrer de novo, o dado persistido continua disponível
        self.assertEqual(banco.tokens_por_demanda(con)["TASK-123"]["saida"], 123)
        # e o ponteiro para reler o conteúdo aponta para um arquivo que sumiu:
        # a releitura devolve vazio ("sem dados"), sem erro
        caminho = banco.transcripts_da_demanda(con, "TASK-123")[0]
        self.assertEqual(telemetria.mensagens_do_arquivo(caminho, "TASK-123", TASKS), [])

    def test_banco_vazio_nao_quebra_nenhuma_consulta(self):
        self.assertEqual(banco.tokens_por_demanda(self.con), {})
        self.assertEqual(banco.fora_de_demanda(self.con), {"saida": 0, "requisicoes": 0})
        self.assertEqual(banco.agentes_da_demanda(self.con, "TASK-123"), [])
        self.assertIsNone(banco.modelo_da_demanda(self.con, "TASK-123"))
        self.assertEqual(banco.transcripts_da_demanda(self.con, "TASK-123"), [])


if __name__ == "__main__":
    unittest.main()
