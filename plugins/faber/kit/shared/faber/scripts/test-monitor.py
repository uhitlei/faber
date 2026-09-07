#!/usr/bin/env python3
# =============================================================================
# test-monitor.py — testes do monitor.py (unittest da stdlib, zero dependência
# nova além do PyYAML que o próprio monitor já usa). Demanda: TASK-91,
# AC-2/AC-4/AC-5/AC-6 (decisions.md D-2: unittest, não pytest).
#
# Todas as fixtures são state.yaml SINTÉTICOS em diretório temporário
# (tempfile.mkdtemp) — nenhum teste depende das demandas reais do repo.
#
# Uso: python3 faber/scripts/test-monitor.py [-v]
# Exit: 0 = todos os testes passaram · 1 = falha
# =============================================================================
"""Testes do faber/scripts/monitor.py."""

import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # não deixa __pycache__ no repo

_AQUI = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("monitor", _AQUI / "monitor.py")
monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monitor)


# ── Helpers de fixture ───────────────────────────────────────────────────────

GATES_TODOS_PENDENTES = {g: {"name": g.lower(), "status": "pending"} for g in monitor.GATES_ORDEM}


def state_yaml(demanda, estado, gates=None, titulo="fixture", tipo="feature", extra=None):
    """Monta o texto de um state.yaml sintético (só o necessário)."""
    dados = {
        "task": demanda,
        "issue": monitor.numero_tarefa(demanda) or 0,
        "title": titulo,
        "type": tipo,
        "state": estado,
        "blocking": None,
        "history": [
            {"from_state": "intake", "to_state": estado, "at": "2026-08-06T10:00:00-03:00", "by": "cto"}
        ],
        "gates": {g: dict(v) for g, v in GATES_TODOS_PENDENTES.items()},
        "invocations": [],
    }
    for gate, status in (gates or {}).items():
        dados["gates"][gate] = {"name": gate.lower(), "status": status}
    if extra:
        dados.update(extra)
    import yaml  # local: o monitor já garante a dependência

    return yaml.safe_dump(dados, allow_unicode=True, sort_keys=False)


class BaseFixture(unittest.TestCase):
    """Cria um diretório de demandas descartável por teste."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="teste-monitor-"))
        self.addCleanup(shutil.rmtree, self.dir, True)

    def demanda(self, nome, conteudo=None, log=None):
        pasta = self.dir / nome
        pasta.mkdir(parents=True, exist_ok=True)
        if conteudo is not None:
            (pasta / "state.yaml").write_text(conteudo, encoding="utf-8")
        if log is not None:
            (pasta / "log.md").write_text(log, encoding="utf-8")
        return pasta

    def ler(self, nome):
        return monitor.ler_demanda(self.dir / nome)

    def linha_de(self, tela, nome):
        """Primeira linha da tela que menciona a demanda (evita casar alinhamento)."""
        for linha in tela.splitlines():
            if nome in linha:
                return linha
        self.fail("demanda %s não apareceu na tela" % nome)


# ── AC-2: regra da fila do Owner (por ESTADO — decisions.md D-1) ───────────


class TesteFilaOwner(BaseFixture):
    def test_ready_for_dev_com_g1_pendente_aparece_por_g1(self):
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev"))
        self.assertEqual(monitor.aguarda_owner(self.ler("TASK-10")), "G1")

    def test_minha_avaliacao_com_g6_pendente_aparece_por_g6(self):
        gates = {"G1": "approved", "G2": "approved", "G3": "approved", "G4": "approved", "G5": "approved"}
        self.demanda("TASK-11", state_yaml("TASK-11", "my-review", gates))
        self.assertEqual(monitor.aguarda_owner(self.ler("TASK-11")), "G6")

    def test_pr_open_com_g8_pendente_aparece_por_g8(self):
        gates = {g: "approved" for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]}
        self.demanda("TASK-12", state_yaml("TASK-12", "pr-open", gates))
        self.assertEqual(monitor.aguarda_owner(self.ler("TASK-12")), "G8")

    def test_refinement_com_g1_pendente_NAO_aparece(self):
        """Caso que uma regra 'primeiro gate pendente' erraria (D-1)."""
        self.demanda("TASK-13", state_yaml("TASK-13", "refinement"))
        d = self.ler("TASK-13")
        self.assertEqual(monitor.status_gate(d, "G1"), "pending")
        self.assertIsNone(monitor.aguarda_owner(d))

    def test_intake_e_specifying_e_in_development_NAO_aparecem(self):
        for i, estado in enumerate(["intake", "specifying", "in-development"]):
            nome = "TASK-2%d" % i
            self.demanda(nome, state_yaml(nome, estado))
            self.assertIsNone(monitor.aguarda_owner(self.ler(nome)), estado)

    def test_pr_open_com_g8_aprovado_NAO_aparece(self):
        gates = {g: "approved" for g in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]}
        self.demanda("TASK-14", state_yaml("TASK-14", "pr-open", gates))
        self.assertIsNone(monitor.aguarda_owner(self.ler("TASK-14")))

    def test_gate_reprovado_NAO_aparece(self):
        self.demanda("TASK-15", state_yaml("TASK-15", "ready-for-dev", {"G1": "rejected"}))
        self.assertIsNone(monitor.aguarda_owner(self.ler("TASK-15")))

    def test_blocked_fica_fora_da_fila_e_no_bloco_de_bloqueio(self):
        bloqueio = {
            "blocking": {
                "reason": "esperando acesso ao HML",
                "since": "2026-08-05T09:00:00-03:00",
                "previous_state": "my-review",
            }
        }
        self.demanda("TASK-16", state_yaml("TASK-16", "blocked", extra=bloqueio))
        d = self.ler("TASK-16")
        self.assertIsNone(monitor.aguarda_owner(d))
        tela = monitor.renderizar([d])
        self.assertIn("!! BLOQUEADAS (1)", tela)
        self.assertIn("esperando acesso ao HML", tela)
        self.assertNotIn("TASK-16 [blocked] aguarda", tela)

    def test_cancelled_fica_fora_da_fila(self):
        self.demanda("TASK-17", state_yaml("TASK-17", "cancelled"))
        self.assertIsNone(monitor.aguarda_owner(self.ler("TASK-17")))

    def test_bloco_da_fila_lista_so_quem_aguarda(self):
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev"))
        self.demanda("TASK-13", state_yaml("TASK-13", "refinement"))
        demandas = [self.ler("TASK-10"), self.ler("TASK-13")]
        tela = monitor.renderizar(demandas)
        self.assertIn(">> AGUARDANDO OWNER (1)", tela)
        self.assertIn("TASK-10 [ready-for-dev] aguarda G1", tela)
        self.assertNotIn("TASK-13 [refinement] aguarda", tela)

    def test_marcador_ascii_fora_de_tty_e_emoji_em_tty(self):
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev"))
        d = [self.ler("TASK-10")]
        self.assertIn(">> AGUARDANDO OWNER", monitor.renderizar(d, tty=False))
        self.assertIn("🔔 AGUARDANDO OWNER", monitor.renderizar(d, tty=True))


# ── AC-5: parser, gate corrente e ordenação por número ──────────────────────


class TesteParser(BaseFixture):
    def test_le_campos_principais_do_state_yaml(self):
        self.demanda(
            "TASK-91",
            state_yaml("TASK-91", "in-development", {"G1": "approved", "G2": "approved"},
                       titulo="Monitor CLI", tipo="tech-debt"),
        )
        d = self.ler("TASK-91")
        self.assertIsNone(d["erro"])
        self.assertEqual(d["task"], "TASK-91")
        self.assertEqual(d["state"], "in-development")
        self.assertEqual(d["type"], "tech-debt")
        self.assertEqual(d["title"], "Monitor CLI")
        self.assertEqual(d["issue"], 91)
        self.assertEqual(d["ultima_transicao"]["to_state"], "in-development")

    def test_gate_corrente_e_o_primeiro_pendente(self):
        self.demanda(
            "TASK-91",
            state_yaml("TASK-91", "in-development", {"G1": "approved", "G2": "approved"}),
        )
        self.assertEqual(monitor.gate_corrente(self.ler("TASK-91")), "G3")

    def test_gate_corrente_none_quando_nada_pendente(self):
        gates = {g: "approved" for g in monitor.GATES_ORDEM}
        self.demanda("TASK-77", state_yaml("TASK-77", "done", gates))
        self.assertIsNone(monitor.gate_corrente(self.ler("TASK-77")))

    def test_gate_nao_aplicavel_nao_e_corrente(self):
        gates = {"G1": "approved", "G2": "not-applicable", "G3": "not-applicable"}
        self.demanda("TASK-30", state_yaml("TASK-30", "code-review", gates))
        self.assertEqual(monitor.gate_corrente(self.ler("TASK-30")), "G4")

    def test_ordenacao_e_numerica_nao_lexicografica(self):
        for nome in ["TASK-100", "TASK-9", "TASK-91", "TASK-78"]:
            self.demanda(nome, state_yaml(nome, "intake"))
        nomes = [p.name for p in monitor.descobrir_demandas(self.dir)]
        self.assertEqual(nomes, ["TASK-9", "TASK-78", "TASK-91", "TASK-100"])

    def test_ordenacao_reflete_na_tela(self):
        for nome in ["TASK-100", "TASK-91"]:
            self.demanda(nome, state_yaml(nome, "intake"))
        demandas = [monitor.ler_demanda(p) for p in monitor.descobrir_demandas(self.dir)]
        tela = monitor.renderizar(demandas)
        self.assertLess(tela.index("TASK-91"), tela.index("TASK-100"))

    def test_pasta_sem_prefixo_tarefa_e_ignorada(self):
        (self.dir / "README.md").write_text("nada aqui", encoding="utf-8")
        (self.dir / "rascunhos").mkdir()
        self.demanda("TASK-91", state_yaml("TASK-91", "intake"))
        self.assertEqual([p.name for p in monitor.descobrir_demandas(self.dir)], ["TASK-91"])

    def test_ultima_linha_do_log_md_sem_o_hifen(self):
        log = "- 2026-08-06T10:00:00-03:00 primeira\n- 2026-08-06T11:00:00-03:00 última ação\n\n"
        self.demanda("TASK-91", state_yaml("TASK-91", "intake"), log=log)
        d = self.ler("TASK-91")
        self.assertEqual(d["ultima_linha_log"], "2026-08-06T11:00:00-03:00 última ação")
        self.assertIn("última ação: 2026-08-06T11:00:00-03:00 última ação", monitor.renderizar([d]))

    def test_log_md_ausente_cai_no_historico(self):
        self.demanda("TASK-91", state_yaml("TASK-91", "specifying"))
        d = self.ler("TASK-91")
        self.assertIsNone(d["ultima_linha_log"])
        self.assertIn("intake -> specifying", monitor.renderizar([d]))

    def test_ultima_invocacao_aparece_na_tela(self):
        extra = {"invocations": [{"agent": "senior-developer", "at": "2026-08-06T12:00:00-03:00"}]}
        self.demanda("TASK-91", state_yaml("TASK-91", "in-development", extra=extra))
        tela = monitor.renderizar([self.ler("TASK-91")], largura=200)
        self.assertIn("último agente: senior-developer", tela)

    def test_linha_longa_e_truncada_pela_largura(self):
        self.demanda("TASK-91", state_yaml("TASK-91", "intake", titulo="t" * 300))
        tela = monitor.renderizar([self.ler("TASK-91")], largura=60)
        self.assertTrue(all(len(l) <= 60 for l in tela.splitlines()))


# ── Sanitização de caracteres de controle (review G4, S-1) ──────────────────

# Escape ANSI real (limpa a tela), CR e BEL — como poderiam chegar pelo título
# da issue no GitHub, pelo motivo de bloqueio ou pela última linha do log.md.
VENENO = "\x1b[2J\x1b[31mforjado\rBIP\x07"


class TesteSanitizacao(BaseFixture):
    def test_corta_remove_escape_ansi_cr_e_demais_controles(self):
        limpo = monitor._corta(VENENO, 200)
        self.assertNotIn("\x1b", limpo)
        self.assertNotIn("\r", limpo)
        self.assertNotIn("\x07", limpo)
        self.assertEqual(limpo, "[2J[31mforjadoBIP")

    def test_titulo_com_escape_nao_chega_cru_a_tela(self):
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev", titulo=VENENO))
        d = self.ler("TASK-10")
        self.assertIn("\x1b", d["title"])  # a fixture tem mesmo o escape cru
        tela = monitor.renderizar([d], largura=200)
        self.assertNotIn("\x1b", tela)
        self.assertNotIn("\r", tela)
        self.assertNotIn("\x07", tela)
        self.assertIn("forjadoBIP", tela)  # o texto legível permanece

    def test_motivo_de_bloqueio_e_ultima_linha_do_log_sao_sanitizados(self):
        bloqueio = {
            "blocking": {"reason": VENENO, "since": "2026-08-07", "previous_state": "intake"}
        }
        # log sem \r: splitlines() cortaria a linha antes de chegar ao _corta
        self.demanda(
            "TASK-16",
            state_yaml("TASK-16", "blocked", extra=bloqueio),
            log="- 2026-08-07T10:00:00-03:00 \x1b[2Jforjado\x07\n",
        )
        d = self.ler("TASK-16")
        self.assertIn("\x1b", d["ultima_linha_log"])  # cru na origem
        self.assertIn("\r", d["blocking"]["reason"])
        tela = monitor.renderizar([d], largura=200)
        self.assertNotIn("\x1b", tela)
        self.assertNotIn("\r", tela)
        self.assertNotIn("\x07", tela)


# ── AC-6: robustez (state.yaml malformado, ausente, campos faltando) ────────


class TesteRobustez(BaseFixture):
    def test_state_yaml_malformado_vira_ilegivel_sem_derrubar_as_demais(self):
        self.demanda("TASK-91", state_yaml("TASK-91", "in-development"))
        # Simula leitura no meio de uma escrita de transition.sh/gate-set.sh
        self.demanda("TASK-92", "demanda: TASK-92\nestado: [in-devel")
        demandas = [monitor.ler_demanda(p) for p in monitor.descobrir_demandas(self.dir)]
        self.assertEqual(demandas[1]["erro"], monitor.ERRO_ILEGIVEL)
        tela = monitor.renderizar(demandas)
        self.assertIn("[%s]" % monitor.ERRO_ILEGIVEL, self.linha_de(tela, "TASK-92"))
        self.assertIn("[in-development]", self.linha_de(tela, "TASK-91"))

    def test_state_yaml_vazio_ou_nao_mapa_vira_ilegivel(self):
        self.demanda("TASK-93", "")
        self.demanda("TASK-94", "- só uma lista\n")
        self.assertEqual(self.ler("TASK-93")["erro"], monitor.ERRO_ILEGIVEL)
        self.assertEqual(self.ler("TASK-94")["erro"], monitor.ERRO_ILEGIVEL)

    def test_pasta_sem_state_yaml(self):
        """Janela entre o mkdir do new-task.sh e a escrita do state.yaml."""
        self.demanda("TASK-95")
        d = self.ler("TASK-95")
        self.assertEqual(d["erro"], monitor.ERRO_SEM_STATE)
        self.assertIn("[sem state.yaml]", monitor.renderizar([d]))

    def test_demanda_ilegivel_nao_entra_na_fila_nem_quebra_gate_corrente(self):
        self.demanda("TASK-92", "estado: [in-devel")
        d = self.ler("TASK-92")
        self.assertIsNone(monitor.aguarda_owner(d))
        self.assertIsNone(monitor.gate_corrente(d))

    def test_state_yaml_sem_gates_nem_historico(self):
        self.demanda("TASK-96", "demanda: TASK-96\nestado: intake\n")
        d = self.ler("TASK-96")
        self.assertIsNone(d["erro"])
        self.assertEqual(d["gates"], {})
        self.assertIsNone(monitor.gate_corrente(d))
        self.assertIn("sem registro", monitor.renderizar([d]))

    def test_gates_com_shape_inesperado_nao_quebram(self):
        self.demanda("TASK-97", "demanda: TASK-97\nestado: ready-for-dev\ngates: [G1, G2]\n")
        d = self.ler("TASK-97")
        self.assertIsNone(monitor.aguarda_owner(d))
        self.assertIn("TASK-97", monitor.renderizar([d]))


# ── AC-4: diretório sem nenhuma demanda + CLI ───────────────────────────────


class TesteCLI(BaseFixture):
    def _rodar(self, argv):
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            codigo = monitor.main(argv)
        return codigo, saida.getvalue(), erro.getvalue()

    def test_diretorio_vazio_nao_lanca_e_diz_nenhuma_demanda(self):
        self.assertEqual(monitor.descobrir_demandas(self.dir), [])
        codigo, saida, _ = self._rodar(["--once", "--tasks-dir", str(self.dir)])
        self.assertEqual(codigo, 0)
        self.assertIn("nenhuma demanda ativa", saida)
        self.assertIn("nenhuma demanda aguardando você", saida)

    def test_once_lista_as_demandas_sem_ansi(self):
        # título com escape ANSI real: sem sanitização (S-1) este teste falha
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev", titulo=VENENO))
        self.demanda("TASK-91", state_yaml("TASK-91", "in-development"))
        codigo, saida, _ = self._rodar(["--once", "--tasks-dir", str(self.dir)])
        self.assertEqual(codigo, 0)
        self.assertNotIn("\033", saida)
        self.assertNotIn("\r", saida)
        self.assertIn("TASKS (2)", saida)
        self.assertIn(">> AGUARDANDO OWNER (1)", saida)

    def test_demandas_dir_inexistente_sai_1_com_mensagem(self):
        codigo, _, erro = self._rodar(["--once", "--tasks-dir", str(self.dir / "nao-existe")])
        self.assertEqual(codigo, 1)
        self.assertIn("pasta de demandas não encontrada", erro)

    def test_interval_abaixo_do_minimo_sai_1(self):
        codigo, _, erro = self._rodar(["--interval", "0", "--tasks-dir", str(self.dir)])
        self.assertEqual(codigo, 1)
        self.assertIn("--interval", erro)

    def test_interval_nan_e_inf_sao_recusados(self):
        """R-2: `nan` furava o `<` (comparação sempre falsa) e explodia no sleep."""
        for valor in ("nan", "inf", "-inf"):  # forma `=`: `-inf` viraria opção
            codigo, _, erro = self._rodar(
                ["--interval=%s" % valor, "--tasks-dir", str(self.dir)]
            )
            self.assertEqual(codigo, 1, valor)
            self.assertIn("--interval", erro)

    def test_loop_sobrevive_a_excecao_no_tick(self):
        """R-1: falha fora do caso já tratado não pode matar o loop (spec §3.7)."""
        ticks = []

        def assinatura_instavel(_dir):
            ticks.append(len(ticks) + 1)
            if len(ticks) == 1:
                raise RuntimeError("falha transitória de I/O")
            raise KeyboardInterrupt  # 2º tick: encerra o loop dentro do teste

        erro = io.StringIO()
        with mock.patch.object(monitor, "assinatura", assinatura_instavel), \
                mock.patch.object(monitor, "time", mock.Mock()), \
                redirect_stderr(erro):
            with self.assertRaises(KeyboardInterrupt):
                monitor._loop(self.dir, 0.5, False)
        self.assertEqual(len(ticks), 2)  # houve um 2º tick: o loop sobreviveu
        self.assertIn("falha transitória de I/O", erro.getvalue())

    def test_assinatura_muda_quando_state_yaml_muda(self):
        """Base do AC-3: o loop só redesenha quando a assinatura muda."""
        self.demanda("TASK-10", state_yaml("TASK-10", "ready-for-dev"))
        antes = monitor.assinatura(self.dir)
        self.assertEqual(antes, monitor.assinatura(self.dir))  # estável sem mudança
        self.demanda("TASK-10", state_yaml("TASK-10", "in-development"))
        self.assertNotEqual(antes, monitor.assinatura(self.dir))

    def test_assinatura_muda_quando_surge_demanda_nova(self):
        antes = monitor.assinatura(self.dir)
        self.demanda("TASK-11", state_yaml("TASK-11", "intake"))
        self.assertNotEqual(antes, monitor.assinatura(self.dir))

    def test_cabecalho_mostra_intervalo_so_no_modo_loop(self):
        agora = datetime(2026, 8, 6, 16, 0, 0)
        self.assertIn("polling 1s", monitor.renderizar([], intervalo=1, agora=agora))
        self.assertNotIn("polling", monitor.renderizar([], agora=agora))


if __name__ == "__main__":
    unittest.main(verbosity=2)
