#!/usr/bin/env python3
# =============================================================================
# teste_telemetria.py — testes da leitura de transcripts.
# Cobre os cenários UNITÁRIOS: RN-5/AC-5, RN-6/AC-6, RN-7/AC-7, RN-8/AC-12,
# atribuição por linha, limiar do "ao vivo" (89 s/91 s), o que é "mensagem"
# e agente ausente = sessão principal.
#
# TODAS as fixtures são sintéticas, em tempdir. Nenhum teste lê os transcripts
# reais desta máquina: eles têm conteúdo de sessão, e teste que depende deles
# não passa em outro clone (`--faber-real` à parte).
# =============================================================================
"""Testes de faber/dashboard/telemetria.py."""

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import telemetria  # noqa: E402

REPO = "/Users/fulano/Code/exemplo/produto-git"
SLUG = telemetria.slug_de(REPO)
TASKS = {"TASK-123", "TASK-92", "TASK-77"}
AGORA = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)


def linha(request_id="req-1", branch="feature/TASK-123", saida=100, entrada=10,
          cache_criacao=0, cache_leitura=0, agente="senior-developer",
          modelo="claude-opus-5", em="2026-08-15T11:59:30+00:00", sessao="sess-1",
          com_usage=True, tipo="assistant", conteudo=None):
    """Uma linha de transcript sintética (bytes), no formato real do Claude Code."""
    dados = {
        "type": tipo,
        "requestId": request_id,
        "sessionId": sessao,
        "gitBranch": branch,
        "timestamp": em,
        "message": {"model": modelo, "content": conteudo or []},
    }
    if com_usage:
        dados["message"]["usage"] = {
            "input_tokens": entrada,
            "output_tokens": saida,
            "cache_creation_input_tokens": cache_criacao,
            "cache_read_input_tokens": cache_leitura,
        }
    if agente is not None:
        dados["attributionAgent"] = agente
    return json.dumps(dados).encode("utf-8")


class BaseDisco(unittest.TestCase):
    """Monta um `~/.claude/projects` de brinquedo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="teste-telemetria-"))
        self.projetos = self.tmp / "projects"
        self.projetos.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def pasta(self, nome):
        p = self.projetos / nome
        p.mkdir(parents=True, exist_ok=True)
        return p

    def escrever(self, caminho, linhas, final=b"\n"):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(b"\n".join(linhas) + final if linhas else b"")
        return caminho


class TesteDescoberta(BaseDisco):
    """RN-5/AC-5 e RN-7/AC-7: o que entra e, principalmente, o que NÃO entra."""

    def test_sessao_e_subagente_entram(self):  # AC-5 (positivo)
        self.escrever(self.pasta(SLUG) / "sessao.jsonl", [linha()])
        self.escrever(self.pasta(SLUG) / "sessao" / "subagents" / "agent-a1.jsonl", [linha()])
        achados = telemetria.transcripts(REPO, self.projetos)
        origens = sorted(o for _c, o in achados)
        self.assertEqual(origens, ["sessao", "subagente"])

    def test_sessao_sem_pasta_subagents_nao_quebra(self):  # AC-5 (negativo)
        self.escrever(self.pasta(SLUG) / "sessao.jsonl", [linha()])
        self.assertEqual(len(telemetria.transcripts(REPO, self.projetos)), 1)

    def test_worktree_entra(self):  # AC-6 (positivo)
        pasta = SLUG + "--claude-worktrees-TASK-123"
        self.escrever(self.pasta(pasta) / "sessao.jsonl", [linha()])
        achados = telemetria.transcripts(REPO, self.projetos)
        self.assertEqual([c.parent.name for c, _o in achados], [pasta])

    def test_repositorio_vizinho_fica_de_fora(self):  # AC-7
        for vizinho in (SLUG + "-backup", SLUG + "-2", SLUG + "-old"):
            self.escrever(self.pasta(vizinho) / "sessao.jsonl", [linha()])
        self.assertEqual(telemetria.transcripts(REPO, self.projetos), [])

    def test_nome_que_estende_o_slug_sem_ser_worktree_fica_de_fora(self):  # AC-7 (borda)
        self.escrever(self.pasta(SLUG + "x") / "sessao.jsonl", [linha()])
        self.escrever(self.pasta(SLUG + "--claude-worktrees") / "s.jsonl", [linha()])
        self.assertEqual(telemetria.transcripts(REPO, self.projetos), [])

    def test_outro_repositorio_qualquer_fica_de_fora(self):
        self.escrever(self.pasta("-Users-fulano-Code-outro-projeto") / "s.jsonl", [linha()])
        self.assertEqual(telemetria.transcripts(REPO, self.projetos), [])

    def test_slug_deriva_do_caminho_de_lancamento(self):
        self.assertEqual(telemetria.slug_de("/Users/fulano/Code/exemplo/produto-git"),
                         "-Users-fulano-Code-exemplo-produto-git")
        # o ponto de `.claude` também vira traço — daí o `--` da worktree
        self.assertEqual(telemetria.slug_de(REPO + "/.claude/worktrees/TASK-123"),
                         SLUG + "--claude-worktrees-TASK-123")

    def test_raiz_de_projetos_inexistente_e_ausencia_nao_falha(self):
        self.assertEqual(telemetria.transcripts(REPO, self.tmp / "nao-existe"), [])


class TesteLeituraIncremental(BaseDisco):
    """RN-8/AC-12: a linha parcial não pode virar evento nem contaminar nada."""

    def test_linha_final_sem_quebra_nao_e_lida(self):  # AC-12 (positivo)
        arq = self.escrever(self.tmp / "t.jsonl", [linha(request_id="r1")], final=b"\n")
        with arq.open("ab") as fh:
            fh.write(b'{"type":"assistant","requestId":"r2","mess')
        linhas, deslocamento = telemetria.ler_incremental(arq, 0)
        self.assertEqual(len(linhas), 1)
        self.assertNotIn(b"r2", b"".join(linhas))
        # o deslocamento parou no \n: a parcial será relida inteira depois
        self.assertEqual(deslocamento, arq.stat().st_size - len('{"type":"assistant","requestId":"r2","mess'))

    def test_linha_parcial_que_continua_incompleta_nao_e_reprocessada(self):  # AC-12 (borda)
        arq = self.escrever(self.tmp / "t.jsonl", [linha(request_id="r1")])
        with arq.open("ab") as fh:
            fh.write(b'{"parcial":')
        _l1, d1 = telemetria.ler_incremental(arq, 0)
        linhas2, d2 = telemetria.ler_incremental(arq, d1)
        self.assertEqual(linhas2, [])
        self.assertEqual(d2, d1)

    def test_parcial_completada_depois_e_lida_inteira(self):
        arq = self.escrever(self.tmp / "t.jsonl", [linha(request_id="r1")])
        with arq.open("ab") as fh:
            fh.write(linha(request_id="r2")[:20])
        _l1, d1 = telemetria.ler_incremental(arq, 0)
        with arq.open("ab") as fh:
            fh.write(linha(request_id="r2")[20:] + b"\n")
        linhas2, _d2 = telemetria.ler_incremental(arq, d1)
        self.assertEqual(len(linhas2), 1)
        eventos = telemetria.eventos_de(linhas2, TASKS)
        self.assertEqual([e.request_id for e in eventos], ["r2"])

    def test_incremental_so_devolve_o_que_chegou_depois(self):
        arq = self.escrever(self.tmp / "t.jsonl", [linha(request_id="r1")])
        _l1, d1 = telemetria.ler_incremental(arq, 0)
        with arq.open("ab") as fh:
            fh.write(linha(request_id="r2") + b"\n")
        linhas2, _d2 = telemetria.ler_incremental(arq, d1)
        self.assertEqual([e.request_id for e in telemetria.eventos_de(linhas2, TASKS)], ["r2"])

    def test_arquivo_menor_que_o_deslocamento_e_relido_do_zero(self):
        """Rotação/recriação: casar offset velho com conteúdo novo daria lixo."""
        arq = self.escrever(self.tmp / "t.jsonl", [linha(request_id="r%d" % i) for i in range(5)])
        _l, grande = telemetria.ler_incremental(arq, 0)
        self.escrever(self.tmp / "t.jsonl", [linha(request_id="novo")])
        linhas, deslocamento = telemetria.ler_incremental(arq, grande)
        self.assertEqual([e.request_id for e in telemetria.eventos_de(linhas, TASKS)], ["novo"])
        self.assertEqual(deslocamento, arq.stat().st_size)

    def test_arquivo_ausente_nao_levanta(self):
        linhas, deslocamento = telemetria.ler_incremental(self.tmp / "nao-existe.jsonl", 7)
        self.assertEqual((linhas, deslocamento), ([], 7))


class TesteAtribuicao(unittest.TestCase):
    """A chave é a branch DA LINHA, e demanda inexistente não é inventada."""

    def test_branch_de_feature(self):  # AC-6 (negativo — fora de worktree)
        self.assertEqual(telemetria.demanda_da_branch("feature/TASK-123", TASKS), "TASK-123")

    def test_branch_de_docs_conta_para_a_demanda(self):
        self.assertEqual(telemetria.demanda_da_branch("docs/TASK-92-specs", TASKS), "TASK-92")

    def test_branch_sem_demanda_nao_e_rateada(self):
        for branch in ("develop", "main", "feature/faber-fase-3", "release/promote-develop"):
            self.assertIsNone(telemetria.demanda_da_branch(branch, TASKS))

    def test_demanda_que_nao_existe_na_projecao_nao_e_inventada(self):
        self.assertIsNone(telemetria.demanda_da_branch("feature/TASK-99999", TASKS))

    def test_branch_ausente_ou_invalida(self):
        for branch in (None, "", 42, []):
            self.assertIsNone(telemetria.demanda_da_branch(branch, TASKS))

    def test_um_arquivo_com_varias_branches_atribui_cada_linha_a_sua_demanda(self):
        """O achado que motivou a regra: muitos transcripts são multi-branch."""
        linhas = [
            linha(request_id="r1", branch="feature/TASK-123"),
            linha(request_id="r2", branch="feature/TASK-92"),
            linha(request_id="r3", branch="develop"),
        ]
        eventos = telemetria.eventos_de(linhas, TASKS)
        self.assertEqual([e.demanda for e in eventos], ["TASK-123", "TASK-92", None])


class TesteExtracao(unittest.TestCase):
    """RN-2: sai a lista branca, e só ela. Mais AC-13 (modelo) e agente ausente."""

    def test_linha_sem_usage_nao_e_telemetria(self):
        self.assertIsNone(telemetria.evento_da_linha(linha(com_usage=False), TASKS))

    def test_linha_sem_request_id_nao_e_telemetria(self):
        bruto = json.dumps({"type": "assistant", "message": {"usage": {"output_tokens": 1}}}).encode()
        self.assertIsNone(telemetria.evento_da_linha(bruto, TASKS))

    def test_json_quebrado_nao_levanta(self):
        self.assertIsNone(telemetria.evento_da_linha(b'{"type": "assist', TASKS))
        self.assertIsNone(telemetria.evento_da_linha(b"[1,2,3]", TASKS))

    def test_campos_de_usage_extraidos(self):
        evento = telemetria.evento_da_linha(
            linha(entrada=7, saida=11, cache_criacao=13, cache_leitura=17), TASKS)
        self.assertEqual((evento.entrada, evento.saida, evento.cache_criacao, evento.cache_leitura),
                         (7, 11, 13, 17))

    def test_evento_nao_tem_campo_de_conteudo(self):
        """A trava estrutural da RN-2: não há onde guardar conteúdo."""
        campos = set(telemetria.Evento._fields)
        self.assertEqual(campos & {"content", "conteudo", "texto", "mensagem", "thinking"}, set())

    def test_conteudo_nao_aparece_no_evento(self):
        isca = "ISCA_DE_CONTEUDO_NAO_PODE_VAZAR"
        bruto = linha(conteudo=[{"type": "text", "text": isca}])
        evento = telemetria.evento_da_linha(bruto, TASKS)
        self.assertNotIn(isca, repr(evento))

    def test_agente_ausente_vira_sessao_principal(self):  # AC-10 (borda)
        evento = telemetria.evento_da_linha(linha(agente=None), TASKS)
        self.assertEqual(evento.agente, "cto")

    def test_modelo_ausente_fica_none_para_virar_sem_dados(self):  # AC-13
        self.assertIsNone(telemetria.evento_da_linha(linha(modelo=None), TASKS).modelo)

    def test_modelo_reconhecido_e_preservado_como_veio(self):  # AC-13 (negativo)
        for modelo in ("claude-opus-5", "<synthetic>"):
            self.assertEqual(telemetria.evento_da_linha(linha(modelo=modelo), TASKS).modelo, modelo)

    def test_usage_com_lixo_vira_zero_nunca_excecao(self):
        bruto = json.dumps({
            "type": "assistant", "requestId": "r1", "gitBranch": "feature/TASK-123",
            "message": {"usage": {"output_tokens": "muito", "input_tokens": -5}},
        }).encode()
        evento = telemetria.evento_da_linha(bruto, TASKS)
        self.assertEqual((evento.entrada, evento.saida), (0, 0))


class TesteMensagemExibida(unittest.TestCase):
    """O que é uma "mensagem" no card — confirmado pelo Owner no G1."""

    def test_bloco_text_vira_mensagem_truncada(self):
        bruto = linha(conteudo=[{"type": "text", "text": "a" * 500}])
        mensagem = telemetria.mensagem_da_linha(bruto)
        self.assertEqual(mensagem.tipo, "text")
        self.assertLessEqual(len(mensagem.texto), telemetria.LIMITE_TEXTO + 1)
        self.assertTrue(mensagem.texto.endswith("…"))

    def test_texto_curto_nao_e_truncado(self):
        mensagem = telemetria.mensagem_da_linha(linha(conteudo=[{"type": "text", "text": "pronto"}]))
        self.assertEqual(mensagem.texto, "pronto")

    def test_tool_use_vira_resumo_de_uma_linha(self):
        bruto = linha(conteudo=[{"type": "tool_use", "name": "Bash",
                                 "input": {"command": "npm run build"}}])
        self.assertEqual(telemetria.mensagem_da_linha(bruto).texto, "Bash: npm run build")

    def test_tool_use_usa_a_chave_que_existir(self):
        bruto = linha(conteudo=[{"type": "tool_use", "name": "Read",
                                 "input": {"file_path": "/tmp/x.py"}}])
        self.assertEqual(telemetria.mensagem_da_linha(bruto).texto, "Read: /tmp/x.py")

    def test_tool_use_sem_input_conhecido_mostra_so_o_nome(self):
        bruto = linha(conteudo=[{"type": "tool_use", "name": "TodoWrite", "input": {"todos": []}}])
        self.assertEqual(telemetria.mensagem_da_linha(bruto).texto, "TodoWrite")

    def test_thinking_nunca_vira_mensagem(self):
        bruto = linha(conteudo=[{"type": "thinking", "thinking": "raciocínio secreto"}])
        self.assertIsNone(telemetria.mensagem_da_linha(bruto))

    def test_thinking_antes_de_texto_nao_impede_o_texto(self):
        bruto = linha(conteudo=[{"type": "thinking", "thinking": "secreto"},
                                {"type": "text", "text": "visível"}])
        mensagem = telemetria.mensagem_da_linha(bruto)
        self.assertEqual(mensagem.texto, "visível")
        self.assertNotIn("secreto", mensagem.texto)

    def test_linha_de_usuario_nao_vira_mensagem(self):
        bruto = linha(tipo="user", conteudo=[{"type": "text", "text": "oi"}])
        self.assertIsNone(telemetria.mensagem_da_linha(bruto))

    def test_quebras_de_linha_viram_espaco(self):
        bruto = linha(conteudo=[{"type": "text", "text": "linha 1\n\nlinha 2"}])
        self.assertEqual(telemetria.mensagem_da_linha(bruto).texto, "linha 1 linha 2")

    def test_agente_da_mensagem_cai_para_sessao_principal(self):
        bruto = linha(agente=None, conteudo=[{"type": "text", "text": "oi"}])
        self.assertEqual(telemetria.mensagem_da_linha(bruto).agente, "cto")


class TesteMensagensDoArquivo(BaseDisco):
    """AC-1: últimas 4–5, o que houver se for menos, e nada de outra demanda."""

    def test_ultimas_cinco_de_dez(self):  # AC-1 (positivo)
        linhas = [linha(request_id="r%d" % i, conteudo=[{"type": "text", "text": "msg %d" % i}])
                  for i in range(10)]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        mensagens = telemetria.mensagens_do_arquivo(arq, "TASK-123", TASKS)
        self.assertEqual([m.texto for m in mensagens], ["msg 5", "msg 6", "msg 7", "msg 8", "msg 9"])

    def test_menos_de_quatro_mostra_o_que_existe(self):  # AC-1 (borda)
        linhas = [linha(request_id="r%d" % i, conteudo=[{"type": "text", "text": "msg %d" % i}])
                  for i in range(2)]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        mensagens = telemetria.mensagens_do_arquivo(arq, "TASK-123", TASKS)
        self.assertEqual([m.texto for m in mensagens], ["msg 0", "msg 1"])

    def test_mensagem_de_outra_demanda_nao_entra_no_card(self):
        linhas = [
            linha(request_id="r1", branch="feature/TASK-92",
                  conteudo=[{"type": "text", "text": "da 92"}]),
            linha(request_id="r2", branch="develop", conteudo=[{"type": "text", "text": "do develop"}]),
            linha(request_id="r3", branch="feature/TASK-123",
                  conteudo=[{"type": "text", "text": "da 110"}]),
        ]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        mensagens = telemetria.mensagens_do_arquivo(arq, "TASK-123", TASKS)
        self.assertEqual([m.texto for m in mensagens], ["da 110"])

    def test_transcript_removido_devolve_vazio_sem_erro(self):  # AC-11 (borda)
        self.assertEqual(telemetria.mensagens_do_arquivo(self.tmp / "sumiu.jsonl",
                                                         "TASK-123", TASKS), [])

    def test_linha_parcial_no_fim_nao_vira_mensagem(self):
        linhas = [linha(request_id="r1", conteudo=[{"type": "text", "text": "completa"}])]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        with arq.open("ab") as fh:
            fh.write(b'{"type":"assistant","message":{"content":[{"type":"text","text":"parc')
        mensagens = telemetria.mensagens_do_arquivo(arq, "TASK-123", TASKS)
        self.assertEqual([m.texto for m in mensagens], ["completa"])

    def test_historico_traz_tudo_da_demanda(self):  # AC-2 (positivo)
        linhas = [linha(request_id="r%d" % i, conteudo=[{"type": "text", "text": "msg %d" % i}])
                  for i in range(30)]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        historico = telemetria.historico_do_arquivo(arq, "TASK-123", TASKS)
        self.assertEqual(len(historico), 30)
        self.assertEqual(historico[0].texto, "msg 0")

    def test_janela_pequena_ainda_acha_as_ultimas(self):
        """Tail de arquivo grande: a primeira linha da janela é descartada por
        estar cortada, e as últimas continuam corretas."""
        linhas = [linha(request_id="r%d" % i, conteudo=[{"type": "text", "text": "msg %d" % i}])
                  for i in range(40)]
        arq = self.escrever(self.tmp / "t.jsonl", linhas)
        mensagens = telemetria.mensagens_do_arquivo(arq, "TASK-123", TASKS, janela=900)
        self.assertEqual([m.texto for m in mensagens][-1:], ["msg 39"])


class TesteLimiarAoVivo(unittest.TestCase):
    """90 s, relógio injetado — nunca `sleep`, nunca `mtime`."""

    def em(self, segundos_atras):
        return (AGORA - timedelta(seconds=segundos_atras)).isoformat()

    def test_89_segundos_esta_ao_vivo(self):  # AC-9/AC-10 (borda)
        self.assertTrue(telemetria.esta_ao_vivo(self.em(89), agora=AGORA))

    def test_91_segundos_nao_esta_ao_vivo(self):  # AC-9/AC-10 (borda)
        self.assertFalse(telemetria.esta_ao_vivo(self.em(91), agora=AGORA))

    def test_limiar_e_noventa_segundos(self):
        self.assertEqual(telemetria.LIMIAR_LIVE_S, 90)

    def test_sem_timestamp_nao_esta_ao_vivo(self):  # AC-9 (negativo)
        for valor in (None, "", "ontem", 42):
            self.assertFalse(telemetria.esta_ao_vivo(valor, agora=AGORA))

    def test_idade_em_segundos_e_dado_cru(self):
        self.assertEqual(telemetria.idade_em_segundos(self.em(96), agora=AGORA), 96)
        self.assertIsNone(telemetria.idade_em_segundos(None, agora=AGORA))

    def test_timestamp_sem_fuso_e_tratado_como_utc(self):
        self.assertTrue(telemetria.esta_ao_vivo("2026-08-15T11:59:30", agora=AGORA))


if __name__ == "__main__":
    unittest.main()
