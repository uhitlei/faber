#!/usr/bin/env python3
# =============================================================================
# teste_app.py — testes das rotas do dashboard (test client do Flask; sem
# subir servidor, sem navegador).
#
# Regra das asserções: assertar CONTRATO DE DADOS (atributos data-*), nunca
# aparência — layout muda, contrato não. A prova visual é o G6 do Owner.
# =============================================================================
"""Testes de faber/dashboard/app.py."""

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as aplicacao  # noqa: E402
import banco  # noqa: E402
import leitor  # noqa: E402
import telemetria  # noqa: E402
from teste_telemetria import linha  # noqa: E402  (fixture sintética compartilhada)

ESQUEMA = leitor.carregar_esquema()

FIXTURES = {
    # nome:            (estado, título, extras)
    "TASK-10": ("intake", "Demanda no backlog", ""),
    "TASK-11": ("clarification", "Pergunta pendente para o Owner", ""),
    "TASK-12": ("in-development", "Em desenvolvimento agora", ""),
    "TASK-13": ("blocked", "Travada esperando decisão",
                  "bloqueio:\n  motivo: 'HML fora do ar'\n  desde: '2026-08-09T10:00:00-03:00'\n"
                  "  estado_origem: validation\n"),
    "TASK-14": ("done", "Entregue e mergeada", ""),
    "TASK-15": ("cancelled", "Descartada por decisão do Owner", ""),
    "TASK-16": ("minha-avaliacao", "Esperando a avaliação do Owner", ""),
    "TASK-17": ("specifying", "<script>alert(1)</script> título vindo do GitHub", ""),
}

HISTORICO = (
    "historico:\n"
    "- de: intake\n  para: specifying\n  em: '2026-08-01T10:00:00-03:00'\n  por: cto\n  motivo: null\n"
    "- de: specifying\n  para: refinement\n  em: '2026-08-02T10:00:00-03:00'\n  por: cto\n"
    "  motivo: 'spec pronta'\n"
)

GATES = "gates:\n" + "".join(
    "  %s: {nome: g, status: %s, aprovador: %s, em: null, evidencia: null, obs: null}\n"
    % (g, "aprovado" if g in ("G1", "G2") else "pendente", "owner" if g == "G1" else "null")
    for g in leitor.GATES_ORDEM
)


def escrever_faber(base):
    """Monta uma fábrica sintética de 8 demandas + 1 leitura inválida."""
    demandas = Path(base) / "faber" / "tasks"
    for nome, (estado, titulo, extra) in FIXTURES.items():
        pasta = demandas / nome
        pasta.mkdir(parents=True, exist_ok=True)
        texto = (
            "demanda: %s\nissue: %s\ntitulo: %s\ntipo: feature\n"
            "estado: %s\natualizada_em: '2026-08-0%dT10:00:00-03:00'\n"
            % (nome, nome.split("-")[1], repr(titulo), estado, 1 + len(nome) % 8)
        )
        texto += extra + HISTORICO + GATES
        texto += "invocacoes:\n- agente: senior-developer\n  em: '2026-08-02T11:00:00-03:00'\n"
        (pasta / "state.yaml").write_text(texto, encoding="utf-8")
    # demanda recém-criada, sem transições (caso de borda)
    nova = demandas / "TASK-18"
    nova.mkdir(parents=True, exist_ok=True)
    (nova / "state.yaml").write_text(
        "demanda: TASK-18\ntitulo: 'Recém-criada'\ntipo: feature\nestado: intake\n"
        "atualizada_em: '2026-08-01T10:00:00-03:00'\nhistorico: []\n", encoding="utf-8")
    # state.yaml truncado no meio da escrita: parseia e devolve 'refi' (AC-10)
    suja = demandas / "TASK-19"
    suja.mkdir(parents=True, exist_ok=True)
    (suja / "state.yaml").write_text(
        "demanda: TASK-19\ntitulo: 'Lida durante a escrita'\ntipo: feature\nestado: refi",
        encoding="utf-8")
    # timestamp bem formado e absurdo (sentinela "nunca"): parseia e estoura na
    # conversão de fuso. Tem que derrubar o CARD, jamais o dashboard (AC-10).
    extrema = demandas / "TASK-20"
    extrema.mkdir(parents=True, exist_ok=True)
    (extrema / "state.yaml").write_text(
        "demanda: TASK-20\ntitulo: 'Carimbo fora da faixa'\ntipo: feature\n"
        "estado: validation\natualizada_em: '9999-12-31T23:59:59'\n", encoding="utf-8")
    return demandas


class BaseApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="teste-dashboard-app-"))
        cls.demandas = escrever_faber(cls.tmp)
        aplicacao.app.config["RAIZ"] = cls.tmp
        aplicacao.app.config["ESQUEMA"] = ESQUEMA
        aplicacao.app.config["TESTING"] = True
        # Sem isto, a suíte varreria os transcripts REAIS desta máquina e
        # escreveria no banco REAL do dashboard. Teste que toca
        # o disco de verdade não é portátil nem inofensivo.
        (cls.tmp / "projects").mkdir(exist_ok=True)
        aplicacao.app.config["PROJETOS"] = cls.tmp / "projects"
        aplicacao.app.config["BANCO"] = cls.tmp / "dados" / "telemetria.sqlite"
        cls.cliente = aplicacao.app.test_client()

    @classmethod
    def tearDownClass(cls):
        aplicacao.app.config["RAIZ"] = None
        aplicacao.app.config["PROJETOS"] = None
        aplicacao.app.config["BANCO"] = banco.BANCO_PADRAO
        aplicacao.app.config["AGORA"] = None
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def html(self, url="/"):
        r = self.cliente.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.data.decode("utf-8")

    def cards(self, html):
        """(demanda → (estado, coluna, valido)) a partir dos atributos data-*."""
        import html as escapador
        import re

        achados = {}
        for bloco in re.findall(r"<article class=\"card[^\"]*\"[^>]*>", html):
            attrs = {k: escapador.unescape(v) for k, v in re.findall(r"data-(\w+)=\"([^\"]*)\"", bloco)}
            achados[attrs["demanda"]] = (attrs["estado"], attrs["coluna"], attrs["valido"])
        return achados


class TesteKanban(BaseApp):
    def test_rota_responde(self):
        self.assertEqual(self.cliente.get("/").status_code, 200)

    def test_cada_demanda_uma_vez_na_coluna_certa(self):  # AC-1 / RN-4 / RN-11
        cards = self.cards(self.html())
        self.assertEqual(cards["TASK-10"], ("intake", "Backlog", "sim"))
        self.assertEqual(cards["TASK-11"], ("clarification", "Backlog", "sim"))
        self.assertEqual(cards["TASK-12"], ("in-development", "Em Desenvolvimento", "sim"))
        self.assertEqual(cards["TASK-13"], ("blocked", "Bloqueada", "sim"))
        self.assertEqual(cards["TASK-14"], ("done", "Done", "sim"))
        self.assertEqual(cards["TASK-16"], ("minha-avaliacao", "Minha Avaliação", "sim"))

    def test_nove_colunas_oficiais(self):  # RN-4
        import html as escapador

        texto = self.html()
        for nome, _ in ESQUEMA.colunas:
            self.assertIn('data-coluna="%s"' % escapador.escape(nome), texto)

    def test_clarification_tem_destaque(self):  # AC-2 / RN-5
        html = self.html()
        self.assertIn("destaque-clarification", html)
        self.assertIn("Aguardando decisão do Owner", html)

    def test_blocked_mostra_motivo(self):  # AC-3 / RN-6
        html = self.html()
        self.assertIn("destaque-blocked", html)
        self.assertIn("HML fora do ar", html)

    def test_cancelled_fora_do_quadro(self):  # AC-9
        self.assertNotIn("TASK-15", self.cards(self.html()))

    def test_cancelled_alcancavel_por_busca(self):  # AC-9 / AC-8
        self.assertIn("TASK-15", self.cards(self.html("/?q=TASK-15")))

    def test_leitura_invalida_sinalizada_sem_derrubar_a_tela(self):  # AC-10
        cards = self.cards(self.html())
        self.assertEqual(cards["TASK-19"], ("refi", "", "nao"))
        self.assertIn("leitura inválida", self.html())
        # e as demais continuam na tela:
        self.assertIn("TASK-12", cards)

    def test_timestamp_absurdo_derruba_o_card_nao_o_dashboard(self):  # AC-10
        # `9999-12-31T23:59:59` fazia GET / responder 500: a exceção de UMA
        # cópia levava a tela inteira. self.html() já exige 200.
        cards = self.cards(self.html())
        self.assertIn("TASK-20", cards)
        self.assertIn("TASK-12", cards)  # as demais continuam na tela
        self.assertEqual(self.cliente.get("/faber-task/TASK-20").status_code, 200)

    def test_kpis(self):  # AC-6
        html = self.html()
        self.assertIn("em andamento", html)
        self.assertIn("aguardando Owner", html)
        self.assertIn("concluídas (done)", html)
        self.assertIn("leituras inválidas", html)

    def test_kpi_em_andamento_nao_conta_done(self):
        # A fixture tem 1 done (TASK-14) e 1 cancelled (TASK-15).
        projecao = leitor.projetar(raiz=self.tmp, esquema=ESQUEMA)
        k = projecao["kpis"]
        self.assertEqual(k["concluidas"], 1)
        self.assertNotIn("TASK-14", [d["nome"] for d in projecao["demandas"]
                                       if d["valido"] and d["estado"] != "done"])
        self.assertEqual(k["ativas"], k["total"] - k["concluidas"] - k["canceladas"] - k["invalidas"])

    def test_busca_por_id_e_por_titulo(self):  # AC-8
        self.assertEqual(list(self.cards(self.html("/?q=TASK-12"))), ["TASK-12"])
        self.assertEqual(list(self.cards(self.html("/?q=desenvolvimento agora"))), ["TASK-12"])

    def test_busca_sem_resultado_tem_estado_vazio_explicito(self):
        html = self.html("/?q=xyz-nao-existe")
        self.assertIn("Nenhuma demanda encontrada", html)

    def test_titulo_do_github_e_escapado(self):  # XSS
        html = self.html()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)


class TesteLeituraDegradada(BaseApp):
    """A tela precisa DIZER que está incompleta, não mostrar um quadro
    parcial como se fosse completo.

    A fábrica sintética destes testes vive num tempdir que não é repositório
    git — as fontes de ref realmente não podem ser lidas, e é exatamente esse
    o caso que antes sumia em silêncio.
    """

    def test_aviso_de_leitura_degradada_nas_duas_telas(self):
        for url in ("/", "/faber-task/TASK-12"):
            html = self.html(url)
            self.assertIn('data-degradada="sim"', html, url)
            self.assertIn("INCOMPLETO", html, url)

    def test_aviso_diz_qual_comando_falhou(self):
        html = self.html()
        self.assertIn("git for-each-ref", html)
        self.assertIn("exit 128", html)

    def test_sem_falha_nao_ha_aviso(self):
        """Aviso é sinal, não decoração: leitura completa não alarma."""
        projecao = dict(leitor.projetar(raiz=self.tmp, esquema=ESQUEMA), falhas=[], degradada=False)
        with aplicacao.app.test_request_context("/"):
            html = aplicacao.render_template(
                "kanban.html", projecao=projecao,
                quadro=leitor.quadro(projecao, ESQUEMA, ""), termo="")
        self.assertNotIn('data-degradada="sim"', html)
        self.assertNotIn("INCOMPLETO", html)


class TesteDetalhe(BaseApp):
    def test_detalhe_tem_id_titulo_estado_historico_e_nove_gates(self):  # AC-4
        html = self.html("/faber-task/TASK-12")
        self.assertIn('data-demanda="TASK-12"', html)
        self.assertIn("Em desenvolvimento agora", html)
        self.assertIn('data-estado="in-development"', html)
        for gate in leitor.GATES_ORDEM:
            self.assertIn('data-gate="%s"' % gate, html)
        self.assertIn("spec pronta", html)  # motivo da transição
        self.assertIn("senior-developer", html)  # agente atuante

    def test_detalhe_de_demanda_sem_historico(self):  # borda: sem transições
        self.assertIn("Sem transições registradas ainda", self.html("/faber-task/TASK-18"))

    def test_detalhe_de_leitura_invalida_nao_exibe_estado(self):  # AC-10
        html = self.html("/faber-task/TASK-19")
        self.assertIn("Leitura inválida", html)
        self.assertIn("estado fora da lista", html)

    def test_detalhe_lista_as_copias_e_marca_a_autoritativa(self):  # RN-13
        html = self.html("/faber-task/TASK-13")
        self.assertIn("Cópias desta demanda", html)
        self.assertIn("vencedora", html)

    def test_demanda_inexistente_404(self):
        r = self.cliente.get("/faber-task/TASK-999")
        self.assertEqual(r.status_code, 404)
        self.assertIn("não encontrada", r.data.decode("utf-8").lower())

    def test_cancelled_tem_detalhe_acessivel(self):  # AC-9 (fora do quadro, não do sistema)
        self.assertIn('data-estado="cancelled"', self.html("/faber-task/TASK-15"))


class TesteSomenteLeitura(BaseApp):
    """AC-7: exercitar todas as rotas não pode tocar em nada no disco."""

    def impressao(self, raiz):
        itens = []
        for p in sorted(Path(raiz).rglob("*")):
            if p.is_file():
                st = p.stat()
                itens.append((str(p), st.st_size, st.st_mtime_ns,
                              hashlib.sha256(p.read_bytes()).hexdigest()))
            else:
                itens.append((str(p), None, None, None))
        return itens

    def test_nenhuma_escrita_em_nenhuma_rota(self):
        antes = self.impressao(self.tmp)
        for url in ("/", "/?q=TASK-12", "/?q=", "/faber-task/TASK-13", "/faber-task/TASK-19",
                    "/faber-task/TASK-15", "/faber-task/TASK-999", "/static/dashboard.css"):
            self.cliente.get(url).close()
        self.assertEqual(antes, self.impressao(self.tmp))

    def test_armazenamento_local_restrito_ao_banco_de_telemetria(self):  # AC-11 / RN-2
        """O Kanban puro não tinha banco nenhum, e este teste travava isso.

        A telemetria introduz UM armazenamento local declarado
        (`dados/telemetria.sqlite`), então a asserção deixa de ser "nada" e
        passa a ser "nada além dele" — qualquer outro arquivo novo continua
        falhando aqui.

        A garantia que o teste antigo comprava (o quadro é função pura do disco
        versionado) não se perde: ela virou o teste
        `test_kanban_identico_com_o_banco_apagado`.
        """
        dashboard = Path(aplicacao.__file__).resolve().parent
        permitidos = {"dados", ".venv", "__pycache__"}
        antes = {p.name for p in dashboard.iterdir()}
        self.cliente.get("/")
        self.cliente.get("/faber-task/TASK-12")
        novos = {p.name for p in dashboard.iterdir()} - antes - permitidos
        self.assertEqual(novos, set())
        self.assertFalse((dashboard / "data").exists())
        # Nenhum banco fora da pasta `dados/`. `.venv` é runtime instalado por
        # pip, não dado do dashboard: fora da conta.
        bancos = [p for p in dashboard.rglob("*.db")
                  if ".venv" not in p.parts and "dados" not in p.parts]
        self.assertEqual(bancos, [])
        soltos = [p for p in dashboard.glob("*.sqlite*")]
        self.assertEqual(soltos, [], "banco fora de dados/: %s" % soltos)

    def test_quadro_identico_entre_cargas(self):  # AC-11 / AC-5
        import re

        # `telemetria: … em X ms` está no rodapé e varia por leitura,
        # como o custo da projeção — é medição, não conteúdo do quadro.
        limpar = lambda h: re.sub(
            r"(leitura completa em [\d.]+ ms|lido em [^<]+|telemetria: [^<]+)", "", h)
        self.assertEqual(limpar(self.html()), limpar(self.html()))

    def test_mudanca_no_state_yaml_move_o_card(self):  # AC-5
        alvo = self.demandas / "TASK-10" / "state.yaml"
        original = alvo.read_text(encoding="utf-8")
        try:
            alvo.write_text(original.replace("estado: intake", "estado: code-review"),
                            encoding="utf-8")
            self.assertEqual(self.cards(self.html())["TASK-10"][1], "Review & Validação")
        finally:
            alvo.write_text(original, encoding="utf-8")


class TesteLancador(unittest.TestCase):
    """"Não escreve nada em disco" não pode depender de quem lança.

    `-B` vale só para o processo que o recebe; a variável exportada é herdada
    por TODO subprocesso do lançador (a suíte, as sondas, o que vier depois).
    O `sys.dont_write_bytecode` dentro do módulo só passa a valer depois de o
    próprio módulo ter sido compilado — por isso existia
    `faber/dashboard/__pycache__/leitor.cpython-*.pyc` no worktree.
    """

    LANCADOR = Path(aplicacao.__file__).resolve().parent / "dashboard.sh"

    def texto(self):
        return self.LANCADOR.read_text(encoding="utf-8")

    def test_exporta_pythondontwritebytecode(self):
        self.assertRegex(self.texto(), r"(?m)^export PYTHONDONTWRITEBYTECODE=1\b")

    def test_continua_passando_B_ao_interpretador(self):
        self.assertIn('"$PY" -B', self.texto())

    def test_nenhum_pycache_versionado(self):
        """Cinto e suspensório: nada de bytecode entrando no repositório."""
        dashboard = self.LANCADOR.parent
        versionados = [p for p in dashboard.rglob("*.pyc") if ".venv" not in p.parts]
        self.assertEqual(versionados, [])


class TesteAnfitriao(BaseApp):
    """Bind em 127.0.0.1 não fecha a porta do NAVEGADOR.

    DNS rebinding: um site aberto numa aba aponta um nome próprio para
    127.0.0.1 e passa a ler estas respostas como mesma-origem. O `Host` da
    requisição é o único lugar onde esse ataque se distingue de um acesso
    legítimo — o pacote chega igual.
    """

    def test_host_forjado_e_recusado(self):
        for url in ("/", "/?q=TASK-12", "/faber-task/TASK-12"):
            r = self.cliente.get(url, headers={"Host": "dashboard.faber.example.com"})
            self.assertEqual(r.status_code, 403, url)
            self.assertNotIn("TASK-12", r.data.decode("utf-8"), url)

    def test_hosts_locais_continuam_passando(self):
        for host in ("localhost", "localhost:8099", "127.0.0.1", "127.0.0.1:8099",
                     "[::1]:8099", "LocalHost:8099"):
            r = self.cliente.get("/", headers={"Host": host})
            self.assertEqual(r.status_code, 200, host)

    def test_estatico_tambem_e_recusado(self):
        r = self.cliente.get("/static/dashboard.css", headers={"Host": "evil.example"})
        self.assertEqual(r.status_code, 403)

    def test_recusa_explica_o_motivo(self):
        r = self.cliente.get("/", headers={"Host": "evil.example"})
        self.assertIn("Host", r.data.decode("utf-8"))


# =============================================================================
# Telemetria ao vivo nas telas.
# Cenários de INTEGRAÇÃO (test client do Flask + fixtures em disco). Continua
# valendo a regra: assertar contrato de dados (data-*), nunca aparência.
# =============================================================================

class BaseTelemetria(BaseApp):
    """Cada teste monta os próprios transcripts e o próprio banco.

    O relógio é INJETADO (`AGORA`): o limiar de 90 s tem que ser
    determinístico — `time.sleep` em teste é lentidão comprada com
    intermitência.
    """

    AGORA = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.caixa = Path(tempfile.mkdtemp(prefix="tel-app-", dir=str(self.tmp)))
        self.projetos = self.caixa / "projects"
        self.pasta = self.projetos / telemetria.slug_de(self.tmp)
        self.pasta.mkdir(parents=True)
        anterior = (aplicacao.app.config["PROJETOS"], aplicacao.app.config["BANCO"],
                    aplicacao.app.config["AGORA"])
        aplicacao.app.config["PROJETOS"] = self.projetos
        aplicacao.app.config["BANCO"] = self.caixa / "dados" / "telemetria.sqlite"
        aplicacao.app.config["AGORA"] = self.AGORA
        self.addCleanup(self.restaurar, anterior)

    def restaurar(self, anterior):
        (aplicacao.app.config["PROJETOS"], aplicacao.app.config["BANCO"],
         aplicacao.app.config["AGORA"]) = anterior

    def ha(self, segundos):
        """Timestamp a N segundos do relógio injetado."""
        return (self.AGORA - timedelta(seconds=segundos)).isoformat()

    def transcript(self, nome, linhas):
        alvo = self.pasta / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(b"\n".join(linhas) + b"\n")
        return alvo

    def card(self, html, demanda="TASK-12"):
        """Atributos data-* do card de uma demanda (o contrato dos testes)."""
        import html as escapador
        import re

        for bloco in re.findall(r"<article class=\"card[^\"]*\"[^>]*>", html):
            attrs = {k: escapador.unescape(v)
                     for k, v in re.findall(r"data-([\w-]+)=\"([^\"]*)\"", bloco)}
            if attrs.get("demanda") == demanda:
                return attrs
        self.fail("card de %s não encontrado" % demanda)

    def bloco_saida(self, html, demanda="TASK-12"):
        """`ao-vivo` | `historico` | None — o rótulo do bloco de output."""
        import re

        trecho = html.split('data-demanda="%s"' % demanda, 1)[-1].split("</article>", 1)[0]
        achado = re.search(r'data-saida-tipo="([^"]*)"', trecho)
        return achado.group(1) if achado else None

    def mensagens_do_card(self, html, demanda="TASK-12"):
        """Textos exibidos no bloco de saída do card."""
        import html as escapador
        import re

        trecho = html.split('data-demanda="%s"' % demanda, 1)[-1].split("</article>", 1)[0]
        return [" ".join(escapador.unescape(re.sub(r"<[^>]+>", " ", m)).split())
                for m in re.findall(r'<li class="msg[^"]*">(.*?)</li>', trecho, re.S)]


class TesteCardAoVivo(BaseTelemetria):
    """AC-1, AC-9, AC-10 — o que aparece (e o que não aparece) no card."""

    def povoar(self, quantas, segundos=10, agente="senior-developer", demanda="TASK-12"):
        self.transcript("sessao.jsonl", [
            linha(request_id="r%d" % i, branch="feature/%s" % demanda, agente=agente,
                  em=self.ha(segundos), conteudo=[{"type": "text", "text": "mensagem %d" % i}])
            for i in range(quantas)])

    def test_execucao_ativa_mostra_as_ultimas_cinco(self):  # AC-1 (positivo)
        self.povoar(10)
        card = self.card(self.html())
        self.assertEqual(card["mensagens"], "5")
        self.assertEqual(self.mensagens_do_card(self.html())[-1], "senior-developer mensagem 9")

    def test_menos_de_quatro_mostra_as_que_existem(self):  # AC-1 (borda)
        self.povoar(2)
        self.assertEqual(self.card(self.html())["mensagens"], "2")

    def test_demanda_sem_execucao_nao_tem_output_nem_ao_vivo(self):  # AC-1/AC-9 (negativo)
        card = self.card(self.html(), "TASK-14")
        self.assertEqual(card["ao-vivo"], "nao")
        self.assertEqual(card["mensagens"], "0")
        self.assertEqual(card["tokens-saida"], "")

    # ── Os três estados do bloco de output, travados ──────────────────────
    # O comportamento (mostrar output de execução encerrada) é exigido pelo
    # AC-11 e fica; o que faltava era decidir e travar. Sem rótulo, output de
    # semanas atrás parecia trabalho acontecendo agora — a tela estaria
    # enganando mesmo exibindo dado verdadeiro.

    def test_com_atividade_o_output_e_marcado_como_ao_vivo(self):
        self.povoar(5, segundos=10)
        self.assertEqual(self.bloco_saida(self.html()), "ao-vivo")
        self.assertNotIn("última execução", self.html())

    def test_sem_atividade_o_output_historico_aparece_rotulado(self):
        self.povoar(5, segundos=6000)
        html = self.html()
        card = self.card(html)
        self.assertEqual(card["ao-vivo"], "nao")
        self.assertEqual(card["mensagens"], "5")       # continua visível (AC-11)
        self.assertEqual(self.bloco_saida(html), "historico")
        self.assertIn("última execução", html)

    def test_sem_execucao_nenhuma_nao_ha_bloco_de_output(self):
        html = self.html()
        self.assertEqual(self.card(html, "TASK-14")["mensagens"], "0")
        self.assertIsNone(self.bloco_saida(html, "TASK-14"))

    def test_idade_aparece_tambem_com_o_live_apagado(self):
        """O README promete que 'há Xs' explica a piscada — a explicação tem
        que existir justamente quando o indicador some."""
        self.povoar(1, segundos=200)
        self.assertIn("há 200s", self.html())

    def test_atividade_no_futuro_nao_acende_o_live(self):
        """Skew de relógio não é atividade recente. A janela é do passado."""
        self.povoar(1, segundos=-30)  # 30 s à frente do relógio injetado
        self.assertEqual(self.card(self.html())["ao-vivo"], "nao")

    def test_atividade_recente_acende_o_ao_vivo(self):  # AC-10
        self.povoar(5, segundos=10)
        card = self.card(self.html())
        self.assertEqual(card["ao-vivo"], "sim")
        self.assertEqual(card["agente-vivo"], "senior-developer")

    def test_atividade_antiga_nao_acende(self):  # AC-9
        self.povoar(5, segundos=600)
        card = self.card(self.html())
        self.assertEqual(card["ao-vivo"], "nao")
        self.assertEqual(card["agente-vivo"], "")

    def test_limiar_89_segundos_ainda_e_ao_vivo(self):  # AC-9/AC-10 (borda)
        self.povoar(1, segundos=89)
        self.assertEqual(self.card(self.html())["ao-vivo"], "sim")

    def test_limiar_91_segundos_ja_nao_e(self):  # AC-9/AC-10 (borda)
        self.povoar(1, segundos=91)
        self.assertEqual(self.card(self.html())["ao-vivo"], "nao")

    def test_sem_atividade_ao_vivo_cai_para_o_state_yaml(self):  # RN-13 (negativo)
        self.povoar(1, segundos=600)
        html = self.html()
        self.assertEqual(self.card(html)["agente-vivo"], "")
        # o agente da última invocação registrada continua aparecendo (state.yaml)
        self.assertIn("senior-developer", html)

    def test_dois_subagentes_na_janela_mostram_sufixo(self):  # AC-10
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", agente="qa", em=self.ha(30)),
            linha(request_id="r2", branch="feature/TASK-12", agente="code-reviewer",
                  em=self.ha(5)),
        ])
        card = self.card(self.html())
        self.assertEqual(card["agente-vivo"], "code-reviewer")  # o mais recente
        self.assertEqual(card["outros-agentes"], "1")           # "+1"
        self.assertIn("code-reviewer +1", self.html())

    def test_um_subagente_so_nao_ganha_sufixo(self):  # AC-10 (negativo)
        self.povoar(3, segundos=20, agente="qa")
        card = self.card(self.html())
        self.assertEqual(card["agente-vivo"], "qa")
        self.assertEqual(card["outros-agentes"], "0")
        self.assertNotIn("qa +", self.html())

    def test_agente_ausente_vira_sessao_principal(self):  # AC-10 (borda)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", agente=None, em=self.ha(10))])
        self.assertEqual(self.card(self.html())["agente-vivo"], "cto")

    def test_thinking_nunca_chega_a_tela(self):
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10),
                  conteudo=[{"type": "thinking", "thinking": "SEGREDO_DO_RACIOCINIO"},
                            {"type": "text", "text": "resposta pública"}])])
        html = self.html()
        self.assertIn("resposta pública", html)
        self.assertNotIn("SEGREDO_DO_RACIOCINIO", html)

    def test_ferramenta_vira_resumo_de_uma_linha(self):
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10),
                  conteudo=[{"type": "tool_use", "name": "Bash",
                             "input": {"command": "npm run build"}}])])
        self.assertIn("Bash: npm run build", self.html())

    def test_output_de_outra_demanda_nao_vaza_para_o_card(self):
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-13", em=self.ha(10),
                  conteudo=[{"type": "text", "text": "trabalho da TASK-13"}]),
            linha(request_id="r2", branch="feature/TASK-12", em=self.ha(10),
                  conteudo=[{"type": "text", "text": "trabalho da TASK-12"}])])
        self.assertEqual(self.mensagens_do_card(self.html()),
                         ["senior-developer trabalho da TASK-12"])

    def test_conteudo_do_transcript_e_escapado(self):  # XSS (superfície da telemetria)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10),
                  conteudo=[{"type": "text", "text": "<script>alert(1)</script>"}])])
        html = self.html()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TesteTokens(BaseTelemetria):
    """AC-8, AC-5 e o KPI de consumo fora de demanda."""

    def test_tokens_deduplicados_aparecem_no_card(self):  # AC-8 (positivo)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=100, em=self.ha(10)),
            linha(request_id="r1", branch="feature/TASK-12", saida=100, em=self.ha(10)),
            linha(request_id="r2", branch="feature/TASK-12", saida=50, em=self.ha(10))])
        self.assertEqual(self.card(self.html())["tokens-saida"], "150")  # MAX, não 250

    def test_subagente_soma_no_card(self):  # AC-5 (positivo, integração)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=100, em=self.ha(10))])
        self.transcript("sessao/subagents/agent-a1.jsonl", [
            linha(request_id="r2", branch="feature/TASK-12", saida=250, em=self.ha(10))])
        self.assertEqual(self.card(self.html())["tokens-saida"], "350")

    def test_nenhum_simbolo_monetario_na_tela(self):  # AC-8 (negativo) / RN-10
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=100, em=self.ha(10))])
        for tela in (self.html(), self.html("/faber-task/TASK-12")):
            for proibido in ("R$", "custo estimado", "USD", "US$"):
                self.assertNotIn(proibido, tela)

    def test_consumo_sem_demanda_vira_kpi_nunca_rateio(self):
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="develop", saida=999, em=self.ha(10)),
            linha(request_id="r2", branch="feature/TASK-12", saida=100, em=self.ha(10))])
        html = self.html()
        self.assertEqual(self.card(html)["tokens-saida"], "100")  # não recebeu nada do develop
        self.assertIn('data-kpi="fora-de-demanda"', html)
        self.assertIn("999", html.split('data-kpi="fora-de-demanda"', 1)[1][:200])


class TesteDetalhe(BaseTelemetria):
    """AC-2, AC-11 e AC-13 no painel de detalhe."""

    def test_historico_completo_sem_autenticacao(self):  # AC-2 (positivo)
        self.transcript("sessao.jsonl", [
            linha(request_id="r%d" % i, branch="feature/TASK-12", em=self.ha(100 - i),
                  conteudo=[{"type": "text", "text": "linha %d" % i}]) for i in range(30)])
        r = self.cliente.get("/faber-task/TASK-12")
        self.assertEqual(r.status_code, 200)  # sem 401/403, sem redirect de login
        html = r.data.decode("utf-8")
        self.assertIn('data-mensagens="30"', html)
        self.assertIn("linha 29", html)

    def test_demanda_sem_historico_nao_da_erro(self):  # AC-2 (negativo)
        html = self.html("/faber-task/TASK-14")
        self.assertIn('data-historico="vazio"', html)
        self.assertIn('data-sem-telemetria="sim"', html)

    def test_historico_gigante_e_paginado(self):  # AC-2 (borda)
        self.transcript("sessao.jsonl", [
            linha(request_id="r%d" % i, branch="feature/TASK-12", em=self.ha(3000 - i),
                  conteudo=[{"type": "text", "text": "m%d" % i}]) for i in range(1200)])
        html = self.html("/faber-task/TASK-12")
        self.assertIn('data-mensagens="%d"' % aplicacao.MENSAGENS_POR_PAGINA, html)
        self.assertIn('data-paginas="6"', html)
        pagina2 = self.html("/faber-task/TASK-12?pagina=2")
        self.assertIn('data-pagina="2"', pagina2)
        # página fora da faixa não quebra: cai na última
        self.assertIn('data-pagina="6"', self.html("/faber-task/TASK-12?pagina=999"))
        self.assertIn('data-pagina="1"', self.html("/faber-task/TASK-12?pagina=abc"))

    def test_detalhe_lista_todos_os_agentes_ao_vivo(self):  # AC-10
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", agente="qa", em=self.ha(30)),
            linha(request_id="r2", branch="feature/TASK-12", agente="code-reviewer",
                  em=self.ha(5))])
        html = self.html("/faber-task/TASK-12")
        trecho = html.split("agentes ao vivo", 1)[1][:400]
        self.assertIn("qa", trecho)
        self.assertIn("code-reviewer", trecho)

    def test_modelo_desconhecido_vira_sem_dados(self):  # AC-13 (positivo)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", modelo=None, em=self.ha(10))])
        self.assertIn("sem dados", self.html("/faber-task/TASK-12"))

    def test_modelo_reconhecido_aparece_como_veio(self):  # AC-13 (negativo)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", modelo="<synthetic>",
                  em=self.ha(10))])
        html = self.html("/faber-task/TASK-12")
        self.assertIn("&lt;synthetic&gt;", html)  # como veio, escapado


class TestePersistenciaEDegradacao(BaseTelemetria):
    """AC-11: tokens do banco, output do JSONL — e o que acontece quando
    cada um dos dois some."""

    def test_transcript_removido_mantem_tokens_e_degrada_o_output(self):  # AC-11 (borda)
        """A tensão AC-15 × AC-11 foi decidida pelo Owner: **retenção**.
        O transcript sai do disco (o Claude Code limpa os antigos sozinho),
        o total de tokens NÃO encolhe — é
        registro durável do que foi medido — e só o conteúdo, que nunca esteve
        no banco (RN-2), degrada para "sem dados"."""
        alvo = self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=123, em=self.ha(10),
                  conteudo=[{"type": "text", "text": "vai sumir"}])])
        self.assertEqual(self.card(self.html())["tokens-saida"], "123")

        alvo.unlink()
        html = self.html("/faber-task/TASK-12")
        # os tokens continuam: não dependem do transcript ainda existir
        self.assertIn('data-tokens-saida="123"', html)
        # o conteúdo, esse, não tem mais de onde vir
        self.assertIn('data-historico="sem-dados"', html)
        self.assertNotIn("vai sumir", html)

    def test_transcript_que_volta_repoe_o_output_sem_duplicar_tokens(self):
        alvo = self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=123, em=self.ha(10),
                  conteudo=[{"type": "text", "text": "conteudo vivo"}])])
        self.html()
        guardado = alvo.read_bytes()

        alvo.unlink()
        self.assertNotIn("conteudo vivo", self.html())

        alvo.write_bytes(guardado)
        html = self.html()
        self.assertIn("conteudo vivo", html)
        self.assertEqual(self.card(html)["tokens-saida"], "123")  # não virou 246

    def test_conteudo_nunca_vem_do_banco_so_do_transcript(self):  # AC-11
        """A metade não contraditória da AC-11: o output é SEMPRE relido do
        JSONL. Com o transcript no lugar, aparece; sem ele, não há de onde
        tirar — e o banco não ajuda, porque não guarda conteúdo (RN-2)."""
        alvo = self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=123, em=self.ha(10),
                  conteudo=[{"type": "text", "text": "conteudo vivo"}])])
        self.assertIn("conteudo vivo", self.html())
        alvo.unlink()
        self.assertNotIn("conteudo vivo", self.html())

    def test_processo_novo_le_os_tokens_do_banco_sem_sessao_viva(self):  # AC-11 (E2E)
        """Processo SEPARADO, sem nenhuma sessão do Claude Code viva: os tokens
        têm que estar no banco que o dashboard gravou."""
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", saida=4242, em=self.ha(10))])
        self.html()  # o request do dashboard é quem popula o banco

        codigo = (
            "import sys; sys.path.insert(0, %r); import banco;"
            "con = banco.abrir(%r);"
            "print(banco.tokens_por_demanda(con)['TASK-12']['saida'])"
            % (str(Path(aplicacao.__file__).resolve().parent),
               str(aplicacao.app.config["BANCO"])))
        r = subprocess.run([sys.executable, "-B", "-c", codigo], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "4242")

    def test_pasta_de_projetos_ilegivel_vira_telemetria_indisponivel(self):
        """Antes isto degradava em SILÊNCIO: tudo zerado, sem LIVE,
        indistinguível de 'nunca houve execução'. Ler zero como 'custou zero'
        é exatamente o que o aviso da tela existe para evitar."""
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10))])
        self.projetos.chmod(0o000)
        self.addCleanup(self.projetos.chmod, 0o755)
        try:
            list(self.projetos.iterdir())  # root ignora permissão: pula o teste
            self.skipTest("permissões não são aplicadas para este usuário")
        except PermissionError:
            pass
        html = self.html()
        self.assertIn('data-telemetria="indisponivel"', html)
        self.assertEqual(self.cards(html)["TASK-12"][0], "in-development")  # Kanban íntegro

    def test_pasta_de_projetos_inexistente_e_ausencia_nao_falha(self):  # o outro lado
        aplicacao.app.config["PROJETOS"] = self.caixa / "nunca-existiu"
        html = self.html()
        self.assertNotIn('data-telemetria="indisponivel"', html)
        self.assertEqual(self.card(html)["ao-vivo"], "nao")

    def test_banco_corrompido_degrada_sem_derrubar_o_kanban(self):  # AC-11 (negativo)
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10))])
        self.html()
        alvo = Path(aplicacao.app.config["BANCO"])
        for sufixo in ("-wal", "-shm"):
            Path(str(alvo) + sufixo).unlink(missing_ok=True)
        alvo.write_bytes(b"isto nao e um banco sqlite" * 500)
        html = self.html()
        self.assertIn('data-telemetria="indisponivel"', html)
        # o Kanban continua inteiro: 9 colunas e os cards no lugar
        self.assertEqual(self.cards(html)["TASK-12"], ("in-development", "Em Desenvolvimento", "sim"))

    def test_kanban_identico_com_o_banco_apagado(self):  # AC-11
        """A promessa do Kanban que sobrevive à telemetria: o quadro é função
        pura do disco versionado. Apagar o armazenamento local e recarregar devolve
        o mesmo quadro — o banco é cache, nunca fonte."""
        import re

        limpar = lambda h: re.sub(
            r"(leitura completa em [\d.]+ ms|lido em [^<]+|telemetria: [^<]+)", "", h)
        antes = limpar(self.html())
        for sufixo in ("", "-wal", "-shm"):
            Path(str(aplicacao.app.config["BANCO"]) + sufixo).unlink(missing_ok=True)
        self.assertEqual(limpar(self.html()), antes)


class TesteAutoRefresh(BaseTelemetria):
    """Recarrega sozinho só quando há o que mudar, e dá para desligar."""

    def viva(self, segundos=10):
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(segundos))])

    def test_com_demanda_ao_vivo_a_tela_se_recarrega(self):
        self.viva()
        self.assertIn('http-equiv="refresh"', self.html())

    def test_sem_demanda_ao_vivo_nao_recarrega(self):
        self.viva(segundos=600)
        self.assertNotIn('http-equiv="refresh"', self.html())

    def test_parametro_desliga_o_refresh(self):
        self.viva()
        self.assertNotIn('http-equiv="refresh"', self.html("/?vivo=0"))

    def test_detalhe_nunca_se_recarrega_sozinho(self):
        self.viva()
        self.assertNotIn('http-equiv="refresh"', self.html("/faber-task/TASK-12"))


class TesteSomenteLeituraFase2(BaseTelemetria):
    """AC-14: com telemetria ligada, nenhuma rota escreve no estado da fábrica."""

    def impressao(self, raiz):
        itens = []
        for p in sorted(Path(raiz).rglob("*")):
            if p.is_file():
                st = p.stat()
                itens.append((str(p), st.st_size, st.st_mtime_ns,
                              hashlib.sha256(p.read_bytes()).hexdigest()))
            else:
                itens.append((str(p), None, None, None))
        return itens

    def test_nenhuma_escrita_em_state_yaml_nem_nos_transcripts(self):  # AC-14
        self.transcript("sessao.jsonl", [
            linha(request_id="r1", branch="feature/TASK-12", em=self.ha(10),
                  conteudo=[{"type": "text", "text": "oi"}])])
        antes_demandas = self.impressao(self.demandas)
        antes_transcripts = self.impressao(self.projetos)
        for url in ("/", "/?q=TASK-12", "/?vivo=0", "/faber-task/TASK-12",
                    "/faber-task/TASK-12?pagina=2", "/faber-task/TASK-14"):
            self.cliente.get(url).close()
        self.assertEqual(antes_demandas, self.impressao(self.demandas))
        self.assertEqual(antes_transcripts, self.impressao(self.projetos))


class TesteBind(unittest.TestCase):
    """Decisão do Owner: não existe opção de bind fora do localhost."""

    def test_host_fixo_em_localhost(self):
        self.assertEqual(aplicacao.HOST, "127.0.0.1")

    def test_cli_nao_aceita_host(self):
        with self.assertRaises(SystemExit):
            aplicacao.main(["--host", "0.0.0.0"])

    def test_codigo_nao_menciona_bind_aberto(self):
        fonte = Path(aplicacao.__file__).resolve()
        texto = fonte.read_text(encoding="utf-8")
        self.assertNotIn('"0.0.0.0"', texto)
        self.assertNotIn("app.run(host=args", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
