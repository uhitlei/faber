#!/usr/bin/env python3
# =============================================================================
# teste_leitor.py — testes da leitura multi-fonte e da validação de estado.
# AC-1/AC-9/AC-10/AC-11 + RN-13.
#
# São as duas coisas que, se falharem, produzem um quadro ERRADO com cara de
# certo: a resolução da cópia autoritativa e a recusa de estado inventado.
# Fixtures sintéticas em tempdir (e um repositório git de brinquedo para o
# caminho das refs) — nenhum teste ESCREVE no repositório real.
# =============================================================================
"""Testes de faber/dashboard/leitor.py."""

import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitor  # noqa: E402

ESQUEMA = leitor.carregar_esquema()

STATE_BOM = """\
demanda: TASK-999
issue: 999
titulo: 'Demanda de teste'
tipo: feature
estado: refinement
bloqueio: null
criada_em: '2026-08-01T10:00:00-03:00'
atualizada_em: '2026-08-02T10:00:00-03:00'
historico:
- de: intake
  para: specifying
  em: '2026-08-01T11:00:00-03:00'
  por: cto
  motivo: null
gates:
  G1: {nome: ready-for-development, status: pendente, aprovador: null}
invocacoes:
- agente: senior-developer
  em: '2026-08-02T09:00:00-03:00'
"""


def state(estado="refinement", atualizada="2026-08-02T10:00:00-03:00", **campos):
    """Monta um state.yaml sintético mínimo."""
    base = {
        "demanda": campos.pop("demanda", "TASK-999"),
        "titulo": campos.pop("titulo", "titulo"),
        "tipo": campos.pop("tipo", "feature"),
        "estado": estado,
        "atualizada_em": atualizada,
    }
    linhas = ["%s: '%s'" % (k, v) for k, v in base.items() if v is not None]
    for chave, valor in campos.items():
        linhas.append("%s: %s" % (chave, valor))
    return "\n".join(linhas) + "\n"


class TesteEsquema(unittest.TestCase):
    """O esquema vem do state.template.yaml — nunca copiado para o código."""

    def test_quinze_estados_dez_tipos_nove_colunas(self):
        self.assertEqual(len(ESQUEMA.estados), 15)
        self.assertEqual(len(ESQUEMA.tipos), 10)
        self.assertEqual(len(ESQUEMA.colunas), 9)

    def test_ordem_das_colunas_e_a_do_board(self):
        self.assertEqual(
            [nome for nome, _ in ESQUEMA.colunas],
            [
                "Backlog",
                "Especificação",
                "Ready for Dev",
                "Em Desenvolvimento",
                "Review & Validação",
                "Minha Avaliação",
                "PR Aberta",
                "Done",
                "Bloqueada",
            ],
        )

    def test_todo_estado_tem_coluna_menos_cancelled(self):
        sem_coluna = [e for e in ESQUEMA.estados if ESQUEMA.coluna_de(e) is None]
        self.assertEqual(sem_coluna, ["cancelled"])  # RN-4 / AC-9

    def test_mapeamento_rn4_ponto_a_ponto(self):
        esperado = {
            "intake": "Backlog",
            "clarification": "Backlog",
            "specifying": "Especificação",
            "refinement": "Especificação",
            "ready-for-dev": "Ready for Dev",
            "in-development": "Em Desenvolvimento",
            "developed": "Em Desenvolvimento",
            "code-review": "Review & Validação",
            "validation": "Review & Validação",
            "minha-avaliacao": "Minha Avaliação",
            "ready-for-pr": "Minha Avaliação",
            "pr-open": "PR Aberta",
            "done": "Done",
            "blocked": "Bloqueada",
        }
        for estado, coluna in esperado.items():
            self.assertEqual(ESQUEMA.coluna_de(estado), coluna, estado)

    def test_esquema_sem_schema_falha_alto(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruim = Path(tmp) / "t.yaml"
            ruim.write_text("estado: intake\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                leitor.carregar_esquema(ruim)


class TesteLerState(unittest.TestCase):
    """AC-10: nunca levanta exceção, nunca inventa estado."""

    def ler(self, texto):
        return leitor.ler_state(texto, ESQUEMA, "TASK-999")

    def test_state_completo(self):
        c = self.ler(STATE_BOM)
        self.assertTrue(c["valido"])
        self.assertEqual(c["estado"], "refinement")
        self.assertEqual(c["tipo"], "feature")
        self.assertTrue(c["tipo_valido"])
        self.assertEqual(len(c["historico"]), 1)
        self.assertEqual(leitor.agente_atuante(c), "senior-developer")

    def test_arquivo_vazio(self):
        c = self.ler("")
        self.assertFalse(c["valido"])
        self.assertEqual(c["erro"], leitor.ERRO_VAZIO)

    def test_topo_nao_e_mapa(self):
        c = self.ler("- item\n- outro\n")
        self.assertFalse(c["valido"])
        self.assertEqual(c["erro"], leitor.ERRO_NAO_MAPA)

    def test_yaml_quebrado(self):
        c = self.ler("estado: intake\n  indentacao: errada\nlixo: [\n")
        self.assertFalse(c["valido"])
        self.assertEqual(c["erro"], leitor.ERRO_PARSE)

    def test_estado_ausente_nulo_ou_desconhecido(self):
        for texto in ("titulo: x\n", "estado: null\n", "estado: refi\n", "estado: em-teste\n"):
            c = self.ler(texto)
            self.assertFalse(c["valido"], texto)
            self.assertIn("estado", c["erro"])

    def test_estado_truncado_e_leitura_invalida_nao_estado(self):
        # O modo de falha medido no refinamento: state.yaml lido no meio da
        # escrita PARSEIA e devolve 'refi'/'refine'/'refineme'.
        for pedaco in ("refi", "refine", "refineme", "refinemen"):
            c = self.ler("estado: %s\n" % pedaco)
            self.assertFalse(c["valido"], pedaco)

    def test_qualquer_truncamento_do_arquivo_real_nunca_inventa_estado(self):
        """Propriedade: para TODO corte do arquivo, ou é inválido, ou o estado
        está na lista fechada. Nenhum prefixo pode produzir estado plausível."""
        for corte in range(1, len(STATE_BOM)):
            c = self.ler(STATE_BOM[:corte])
            if c["valido"]:
                self.assertIn(c["estado"], ESQUEMA.estados, "corte %d" % corte)

    def test_tipo_fora_da_lista_e_marcado(self):
        c = self.ler(state(tipo="feat"))
        self.assertTrue(c["valido"])  # o estado é válido: a coluna não muda
        self.assertFalse(c["tipo_valido"])  # mas o tipo nunca é exibido como bom

    def test_shape_inesperado_de_gates_historico_e_bloqueio(self):
        c = self.ler(state(**{"gates": "[G1, G2]", "historico": "'texto'", "bloqueio": "'x'"}))
        self.assertTrue(c["valido"])
        self.assertEqual(c["gates"], {})
        self.assertEqual(c["historico"], [])
        self.assertIsNone(c["bloqueio"])

    def test_tag_python_e_recusada(self):
        c = self.ler("estado: !!python/object/apply:os.system ['echo x']\n")
        self.assertFalse(c["valido"])

    def test_titulo_com_html_e_preservado_cru(self):
        # Escapar é responsabilidade do Jinja2 na renderização, não do leitor:
        # escapar duas vezes esconde o dado real.
        c = self.ler(state(titulo="<script>alert(1)</script>"))
        self.assertEqual(c["titulo"], "<script>alert(1)</script>")

    def test_atualizada_em_ilegivel_nao_derruba(self):
        c = self.ler(state(atualizada="ontem"))
        self.assertTrue(c["valido"])
        self.assertIsNone(c["atualizada_dt"])

    def test_timestamp_fora_de_faixa_nao_levanta(self):
        # Valores sentinela plausíveis ("nunca"/"infinito"): PARSEIAM em
        # fromisoformat e estouram só no astimezone(). Antes da correção o
        # ValueError subia por ler_state e derrubava a tela inteira (AC-10).
        for extremo in ("9999-12-31T23:59:59", "0001-01-01T00:00:00"):
            c = self.ler(state(atualizada=extremo))
            self.assertTrue(c["valido"], extremo)
            self.assertIsNone(c["atualizada_dt"], extremo)
            self.assertEqual(c["atualizada_em"], extremo)  # o dado cru continua na tela

    def test_copia_com_timestamp_fora_de_faixa_nao_vence_de_uma_datada(self):
        absurda = leitor.ler_state(state(estado="intake", atualizada="9999-12-31T23:59:59"),
                                   ESQUEMA, "TASK-999", "git:x")
        datada = leitor.ler_state(state(estado="done", atualizada="2026-08-05T10:00:00-03:00"),
                                  ESQUEMA, "TASK-999", "checkout:principal")
        self.assertEqual(leitor.resolver([absurda, datada])["estado"], "done")


class TesteResolucao(unittest.TestCase):
    """RN-13: vence a cópia de maior `atualizada_em`, varridas todas as fontes."""

    def copia(self, fonte, estado="refinement", atualizada="2026-08-02T10:00:00-03:00", historico=0):
        c = leitor.ler_state(state(estado=estado, atualizada=atualizada), ESQUEMA, "TASK-999", fonte)
        c["historico"] = [{"em": "x"}] * historico
        return c

    def test_vence_a_mais_recente_independente_da_fonte(self):
        antiga = self.copia("git:feature/TASK-999", "pr-open", "2026-08-01T10:00:00-03:00")
        nova = self.copia("git:docs/outra-branch", "done", "2026-08-05T10:00:00-03:00")
        self.assertEqual(leitor.resolver([antiga, nova])["estado"], "done")
        self.assertEqual(leitor.resolver([nova, antiga])["estado"], "done")

    def test_branch_propria_nao_tem_privilegio(self):
        # A regra alternativa "vale a branch da demanda" erra quando o `done`
        # é commitado numa branch docs/ de outra demanda.
        propria = self.copia("git:feature/TASK-999", "pr-open", "2026-08-01T10:00:00-03:00")
        outra = self.copia("git:docs/TASK-88-specs", "done", "2026-08-09T10:00:00-03:00")
        self.assertEqual(leitor.resolver([propria, outra])["fonte"], "git:docs/TASK-88-specs")

    def test_fuso_diferente_e_comparado_como_instante(self):
        # String '2026-08-02T09:00:00-06:00' < '2026-08-02T10:00:00-03:00',
        # mas o instante é POSTERIOR. Comparar texto erraria.
        cedo = self.copia("git:a", "pr-open", "2026-08-02T10:00:00-03:00")
        tarde = self.copia("git:b", "done", "2026-08-02T09:00:00-06:00")
        self.assertEqual(leitor.resolver([cedo, tarde])["estado"], "done")

    def test_invalida_nunca_vence_de_valida_mesmo_sendo_mais_nova(self):
        # Leitura suja (arquivo sendo reescrito) é mais nova, mas não é estado.
        valida = self.copia("checkout:principal", "done", "2026-08-01T10:00:00-03:00")
        suja = leitor.ler_state("estado: refi\natualizada_em: '2026-09-01T10:00:00-03:00'\n",
                                ESQUEMA, "TASK-999", "checkout:worktree")
        vencedora = leitor.resolver([valida, suja])
        self.assertTrue(vencedora["valido"])
        self.assertEqual(vencedora["estado"], "done")

    def test_todas_invalidas_a_demanda_aparece_como_invalida(self):
        a = leitor.ler_state("", ESQUEMA, "TASK-999", "checkout:principal")
        b = leitor.ler_state("estado: refi\n", ESQUEMA, "TASK-999", "git:x")
        self.assertFalse(leitor.resolver([a, b])["valido"])

    def test_empate_desempata_por_historico_mais_longo(self):
        curta = self.copia("git:a", "pr-open", historico=2)
        longa = self.copia("git:b", "done", historico=9)
        self.assertEqual(leitor.resolver([curta, longa])["estado"], "done")

    def test_sem_copias(self):
        self.assertIsNone(leitor.resolver([]))


class TesteFonteQueFalha(unittest.TestCase):
    """Fonte que falha tem que APARECER na projeção.

    Antes disto, `_git` devolvia b"" ignorando exit code/timeout e cada
    consumidor lia vazio como "não há nada aqui": o quadro voltava a ser a
    leitura de um checkout só, sem um único campo registrando a perda.
    """

    def faber_sintetica(self, base):
        pasta = Path(base) / "faber" / "tasks" / "TASK-7"
        pasta.mkdir(parents=True)
        (pasta / "state.yaml").write_text(
            state(estado="in-development", demanda="TASK-7", titulo="Só no checkout"),
            encoding="utf-8")

    def test_exit_code_nao_zero_e_declarado(self):
        # Pasta que não é repositório git: `rev-parse` sai 128 e antes esse
        # 128 era descartado junto com o stderr.
        with tempfile.TemporaryDirectory() as tmp:
            coleta = leitor.Coleta()
            self.assertEqual(leitor._git(tmp, ["rev-parse", "--git-common-dir"], coleta=coleta), b"")
            self.assertEqual(len(coleta.falhas), 1)
            self.assertIn("exit 128", coleta.falhas[0]["motivo"])

    def test_orcamento_esgotado_interrompe_e_declara(self):
        # O timeout é POR CHAMADA e a projeção faz ~22: sem teto de tempo
        # total, um repositório lento prende a tela por minutos.
        with tempfile.TemporaryDirectory() as tmp:
            coleta = leitor.Coleta(orcamento=0)
            self.assertEqual(leitor._git(tmp, ["worktree", "list"], coleta=coleta), b"")
            self.assertIn("orçamento", coleta.falhas[0]["motivo"])

    def test_falhas_repetidas_viram_contagem(self):
        coleta = leitor.Coleta()
        for _ in range(3):
            coleta.registrar("git ls-tree", "exit 128 — x")
        self.assertEqual(len(coleta.falhas), 1)
        self.assertEqual(coleta.falhas[0]["vezes"], 3)

    def test_projecao_fora_de_repositorio_git_se_declara_degradada(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.faber_sintetica(tmp)
            p = leitor.projetar(raiz=Path(tmp), esquema=ESQUEMA)
            self.assertTrue(p["degradada"])
            self.assertTrue(p["falhas"])
            # degradar não é apagar: o que deu para ler continua na tela
            self.assertEqual([d["nome"] for d in p["demandas"]], ["TASK-7"])

    def test_git_ausente_no_path_nao_vira_quadro_vazio_silencioso(self):
        """Regressão: sem `git` no PATH o quadro vinha vazio e exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            self.faber_sintetica(tmp)
            original = os.environ.get("PATH", "")
            os.environ["PATH"] = "/caminho/inexistente"
            try:
                p = leitor.projetar(raiz=Path(tmp), esquema=ESQUEMA)
            finally:
                os.environ["PATH"] = original
            self.assertTrue(p["degradada"])
            self.assertTrue(any("FileNotFoundError" in f["motivo"] for f in p["falhas"]),
                            p["falhas"])


class TesteReusoDoMonitor(unittest.TestCase):
    """monitor.py ausente tem que virar mensagem útil, não erro cru."""

    def test_carrega_o_monitor_de_verdade(self):
        modulo = leitor._carregar_monitor(leitor._AQUI.parent / "scripts" / "monitor.py")
        self.assertTrue(modulo.GATES_ORDEM)

    def test_arquivo_ausente_diz_o_que_falta_e_onde(self):
        with tempfile.TemporaryDirectory() as tmp:
            faltando = Path(tmp) / "monitor.py"
            with self.assertRaises(ImportError) as ctx:
                leitor._carregar_monitor(faltando)
        self.assertIn(str(faltando), str(ctx.exception))
        self.assertIn("monitor.py", str(ctx.exception))


class TesteCaminhoNaoASCII(unittest.TestCase):
    """`ls-tree` sem `-z` cita caminho não-ASCII em C-style ("\\303\\247"),
    e a demanda sumia do quadro em silêncio por não começar com `TASK-`."""

    def test_demanda_com_acento_no_nome_nao_some_da_ref(self):
        tmp = Path(tempfile.mkdtemp(prefix="teste-dashboard-acento-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        nome = "TASK-77-conversão"
        pasta = tmp / "faber" / "tasks" / nome
        pasta.mkdir(parents=True)
        (pasta / "state.yaml").write_text(state(estado="done", demanda=nome), encoding="utf-8")
        git = lambda *a: subprocess.run(["git", "-C", str(tmp)] + list(a), check=True,
                                        capture_output=True)
        git("init", "-q", "-b", "develop")
        git("config", "user.email", "teste@faber.local")
        git("config", "user.name", "teste")
        git("config", "core.quotepath", "true")  # o padrão do git, explícito
        git("add", "-A")
        git("commit", "-q", "-m", "demanda com acento")

        copias = leitor.coletar_git(tmp, ESQUEMA)
        achadas = [c for c in copias if c["nome"].startswith("TASK-77")]
        self.assertEqual(len(achadas), 1, [c["nome"] for c in copias])
        self.assertEqual(achadas[0]["estado"], "done")


class TesteParserBatch(unittest.TestCase):
    """Um objeto ausente não pode zerar os blobs seguintes."""

    A, B, C = "1" * 40, "2" * 40, "3" * 40
    # Saída realista do `--batch` quando o 1º objeto foi podado (gc) entre o
    # ls-tree e o cat-file, e os dois seguintes existem.
    COM_AUSENTE = (
        b"1111111111111111111111111111111111111111 missing\n"
        b"2222222222222222222222222222222222222222 blob 18\n"
        b"estado: refinement\n"
        b"3333333333333333333333333333333333333333 blob 12\n"
        b"estado: done\n"
    )

    def test_caminho_feliz(self):
        bruto = b"%s blob 12\nestado: done\n" % self.A.encode()
        self.assertEqual(leitor._parsear_batch(bruto, [self.A]), {self.A: "estado: done"})

    def test_objeto_ausente_nao_contamina_os_seguintes(self):
        coleta = leitor.Coleta()
        conteudo = leitor._parsear_batch(self.COM_AUSENTE, [self.A, self.B, self.C], coleta)
        self.assertEqual(conteudo[self.A], "")  # esse sim está ausente
        self.assertEqual(conteudo[self.B], "estado: refinement")
        self.assertEqual(conteudo[self.C], "estado: done")
        self.assertTrue(coleta.falhas)  # e a ausência é declarada, não engolida

    def test_saida_truncada_declara_quantos_ficaram_sem_resposta(self):
        coleta = leitor.Coleta()
        conteudo = leitor._parsear_batch(b"", [self.A, self.B], coleta)
        self.assertEqual(conteudo, {self.A: "", self.B: ""})
        self.assertIn("2 blob(s) sem resposta", coleta.falhas[0]["motivo"])


class TesteProjecaoSintetica(unittest.TestCase):
    """Projeção sobre uma fábrica de brinquedo (checkouts + refs git reais)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="teste-dashboard-"))
        cls.raiz = cls.tmp / "repo"
        (cls.raiz / "faber" / "tasks").mkdir(parents=True)
        cls.git("init", "-q", "-b", "develop")
        cls.git("config", "user.email", "teste@faber.local")
        cls.git("config", "user.name", "teste")

        # TASK-1: commitada em develop como pr-open...
        cls.escrever("TASK-1", state(estado="pr-open", atualizada="2026-08-01T10:00:00-03:00",
                                       demanda="TASK-1", titulo="Primeira demanda"))
        # TASK-2: só existe commitada (nenhum checkout vivo a enxerga)
        cls.escrever("TASK-2", state(estado="cancelled", atualizada="2026-08-01T10:00:00-03:00",
                                       demanda="TASK-2", titulo="Cancelada"))
        cls.git("add", "-A")
        cls.git("commit", "-q", "-m", "demandas")

        # ...e depois avançada para `done` numa OUTRA branch (docs/)
        cls.git("checkout", "-q", "-b", "docs/notas")
        cls.escrever("TASK-1", state(estado="done", atualizada="2026-08-09T10:00:00-03:00",
                                       demanda="TASK-1", titulo="Primeira demanda"))
        cls.git("add", "-A")
        cls.git("commit", "-q", "-m", "done da 1")
        cls.git("checkout", "-q", "develop")

        # Não commitadas, só no sistema de arquivos:
        cls.escrever("TASK-3", state(estado="blocked", atualizada="2026-08-10T10:00:00-03:00",
                                       demanda="TASK-3", titulo="Bloqueada",
                                       bloqueio="{motivo: 'esperando decisão', desde: 'x'}"))
        cls.escrever("TASK-4", "estado: refi\natualizada_em: '2026-08-11T10:00:00-03:00'\n")
        cls.projecao = leitor.projetar(raiz=cls.raiz, esquema=ESQUEMA)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def git(cls, *args):
        subprocess.run(["git", "-C", str(cls.raiz)] + list(args), check=True,
                       capture_output=True)

    @classmethod
    def escrever(cls, nome, texto):
        pasta = cls.raiz / "faber" / "tasks" / nome
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "state.yaml").write_text(texto, encoding="utf-8")

    def demanda(self, nome):
        return next(d for d in self.projecao["demandas"] if d["nome"] == nome)

    def test_uniao_das_fontes_ve_mais_que_o_checkout(self):
        # AC-1: a demanda que só existe numa ref antiga não some do quadro.
        nomes = [d["nome"] for d in self.projecao["demandas"]]
        self.assertEqual(sorted(nomes), ["TASK-1", "TASK-2", "TASK-3", "TASK-4"])

    def test_cada_demanda_uma_unica_vez(self):  # RN-11
        nomes = [d["nome"] for d in self.projecao["demandas"]]
        self.assertEqual(len(nomes), len(set(nomes)))

    def test_leitura_completa_nao_inventa_falha(self):
        # O contrapeso do aviso de degradação: repositório são, zero alarme.
        self.assertEqual(self.projecao["falhas"], [])
        self.assertFalse(self.projecao["degradada"])

    def test_estado_vem_da_copia_autoritativa_e_nao_do_checkout(self):
        # No sistema de arquivos a TASK-1 está pr-open; o `done` só existe
        # numa branch docs/. Vence o carimbo mais recente (RN-13).
        d = self.demanda("TASK-1")
        self.assertEqual(d["estado"], "done")
        self.assertEqual(d["coluna"], "Done")
        self.assertEqual(d["estados_divergentes"], ["done", "pr-open"])

    def test_bloqueada_expoe_motivo(self):  # AC-3 / RN-6
        d = self.demanda("TASK-3")
        self.assertEqual(d["coluna"], "Bloqueada")
        self.assertEqual(d["motivo_bloqueio"], "esperando decisão")
        self.assertEqual(d["destaque"], "blocked")

    def test_bloqueada_sem_motivo_registrado(self):
        c = leitor.ler_state(state(estado="blocked"), ESQUEMA, "TASK-9")
        d = leitor.montar_demanda("TASK-9", [c], ESQUEMA)
        self.assertEqual(d["motivo_bloqueio"], "motivo não registrado")

    def test_leitura_invalida_nao_ganha_coluna(self):  # AC-10
        d = self.demanda("TASK-4")
        self.assertFalse(d["valido"])
        self.assertIsNone(d["coluna"])

    def test_cancelled_fica_fora_do_quadro_ativo(self):  # AC-9 / RN-4
        quadro = leitor.quadro(self.projecao, ESQUEMA)
        na_tela = [d["nome"] for col in quadro["colunas"] for d in col["demandas"]]
        self.assertNotIn("TASK-2", na_tela)
        self.assertEqual(quadro["canceladas"], [])

    def test_cancelled_aparece_na_busca_explicita(self):  # AC-9
        quadro = leitor.quadro(self.projecao, ESQUEMA, "cancelada")
        self.assertEqual([d["nome"] for d in quadro["canceladas"]], ["TASK-2"])

    def test_kpis(self):  # AC-6
        k = self.projecao["kpis"]
        self.assertEqual(k["total"], 4)
        self.assertEqual(k["ativas"], 1)  # só a 3 (1 é done, 2 cancelled, 4 inválida)
        self.assertEqual(k["canceladas"], 1)
        self.assertEqual(k["invalidas"], 1)
        # A contagem por coluna é a do próprio quadro — não há segundo cálculo.
        colunas = {c["nome"]: len(c["demandas"])
                   for c in leitor.quadro(self.projecao, ESQUEMA)["colunas"]}
        self.assertEqual(colunas["Done"], 1)
        self.assertEqual(colunas["Bloqueada"], 1)
        self.assertEqual(colunas["Backlog"], 0)
        self.assertNotIn("por_coluna", k)

    def test_done_nao_conta_como_em_andamento(self):
        # "ativas" responde "o que está em andamento": a TASK-1 está done,
        # aparece na coluna Done, e não é trabalho em curso.
        k = self.projecao["kpis"]
        self.assertEqual(k["ativas"], 1)      # TASK-3 (blocked continua em curso)
        self.assertEqual(k["concluidas"], 1)  # TASK-1
        # a coluna Done segue contando a demanda concluída (é outra pergunta):
        colunas = {c["nome"]: len(c["demandas"])
                   for c in leitor.quadro(self.projecao, ESQUEMA)["colunas"]}
        self.assertEqual(colunas["Done"], 1)
        # invariante: toda demanda cai em exatamente um balde
        self.assertEqual(k["ativas"] + k["concluidas"] + k["canceladas"] + k["invalidas"],
                         k["total"])

    def test_filtro_por_id_numero_titulo_e_acento(self):  # AC-8
        d = self.projecao["demandas"]
        self.assertEqual([x["nome"] for x in leitor.filtrar(d, "TASK-3")], ["TASK-3"])
        self.assertEqual([x["nome"] for x in leitor.filtrar(d, "3")], ["TASK-3"])
        self.assertEqual([x["nome"] for x in leitor.filtrar(d, "primeira")], ["TASK-1"])
        self.assertEqual([x["nome"] for x in leitor.filtrar(d, "DECISAO")], [])
        self.assertEqual(leitor.filtrar(d, "  "), d)
        self.assertEqual(leitor.filtrar(d, "nao-existe"), [])

    def test_projecao_nao_escreve_nada(self):  # AC-7
        antes = self.arvore()
        leitor.projetar(raiz=self.raiz, esquema=ESQUEMA)
        self.assertEqual(antes, self.arvore())

    def test_reconstrucao_do_zero_e_identica(self):  # AC-11
        # Não há armazenamento local a apagar: a projeção é função pura do
        # disco versionado. Duas leituras independentes dão o mesmo quadro.
        segunda = leitor.projetar(raiz=self.raiz, esquema=ESQUEMA)
        chave = lambda p: [(d["nome"], d["estado"], d["coluna"], d["valido"]) for d in p["demandas"]]
        self.assertEqual(chave(self.projecao), chave(segunda))

    def arvore(self):
        itens = []
        for p in sorted(self.raiz.rglob("*")):
            if ".git/" in str(p):
                continue
            st = p.stat()
            itens.append((str(p), st.st_size, st.st_mtime_ns))
        return itens


class TesteFabricaReal(unittest.TestCase):
    """Sobre as demandas REAIS desta instalação — o que a AC-1 promete.

    Aqui ficam só as propriedades verdadeiras em QUALQUER instalação
    (portáteis), inclusive numa fábrica recém-instalada, sem demanda nenhuma.
    O que depende do estado desta máquina — quantos worktrees existem, se há
    divergência entre cópias agora — vive em `faber_real.py`, fora do
    discover, e roda por `rodar.py --faber-real` (dois testes assim faziam a
    suíte falhar em clone limpo).
    """

    @classmethod
    def setUpClass(cls):
        cls.projecao = leitor.projetar(esquema=ESQUEMA)

    def test_projecao_e_bem_formada_mesmo_sem_demandas(self):
        p = self.projecao
        self.assertIsInstance(p["demandas"], list)
        self.assertEqual(p["kpis"]["total"], len(p["demandas"]))
        self.assertEqual(p["total_copias"], sum(d["total_copias"] for d in p["demandas"]))
        for d in p["demandas"]:
            self.assertTrue(d["copias"], d["nome"])

    def test_cada_demanda_uma_unica_vez(self):
        nomes = [d["nome"] for d in self.projecao["demandas"]]
        self.assertEqual(len(nomes), len(set(nomes)))

    def test_uniao_nunca_ve_menos_que_a_melhor_fonte_isolada(self):
        """Portátil: a união das fontes é superconjunto de qualquer fonte.

        Que ela veja ESTRITAMENTE mais depende de haver mais de um checkout
        vivo — isso é estado desta máquina e foi para faber_real.py.
        """
        por_fonte = {}
        for d in self.projecao["demandas"]:
            for c in d["copias"]:
                por_fonte.setdefault(c["fonte"], set()).add(c["nome"])
        melhor = max((len(v) for v in por_fonte.values()), default=0)
        self.assertGreaterEqual(len(self.projecao["demandas"]), melhor)

    def test_estado_exibido_e_o_da_copia_de_maior_atualizada_em(self):
        for d in self.projecao["demandas"]:
            validas = [c for c in d["copias"] if c["valido"]]
            if not validas:
                continue
            esperado = max(validas, key=leitor.chave_resolucao)
            self.assertEqual(d["estado"], esperado["estado"], d["nome"])

    def test_todo_estado_exibido_esta_na_lista_fechada(self):
        for d in self.projecao["demandas"]:
            if d["valido"]:
                self.assertIn(d["estado"], ESQUEMA.estados, d["nome"])

    def test_nao_escreve_no_repositorio(self):  # AC-7
        raiz = Path(self.projecao["raiz"]) / "faber" / "tasks"
        antes = sorted((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in raiz.rglob("state.yaml"))
        leitor.projetar(esquema=ESQUEMA)
        depois = sorted((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in raiz.rglob("state.yaml"))
        self.assertEqual(antes, depois)


if __name__ == "__main__":
    unittest.main(verbosity=2)
