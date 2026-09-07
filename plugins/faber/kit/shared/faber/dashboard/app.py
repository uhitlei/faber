#!/usr/bin/env python3
# =============================================================================
# app.py — dashboard local da fábrica: Kanban das colunas oficiais projetado
# dos state.yaml, com telemetria ao vivo dos agentes lida dos transcripts JSONL
# do Claude Code.
#
# CANÁRIO-TRAVA-DEPLOY: FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH
# Esta string existe para ser PROCURADA em artefato de build: se ela aparecer
# em dist/, o dashboard interno vazou para o site público e a trava falha
# (faber/dashboard/trava_deploy.py). Não remover.
#
# Restrição de arquitetura (decisão do Owner): o servidor só faz bind em
# 127.0.0.1. Não existe opção de host: sem superfície de REDE não há o que
# autenticar, e expor a tela sem autenticação vazaria conteúdo de sessão.
# Mudar isso exige nova decisão do Owner e reabre a avaliação de segurança.
#
# O bind, porém, não fecha a porta do NAVEGADOR: um site aberto numa aba pode
# apontar um nome próprio para 127.0.0.1 (DNS rebinding) e ler estas respostas
# como mesma-origem. Como ESTA TELA SERVE SAÍDA DE SESSÃO (RN-1), a checagem
# de `Host` abaixo é o controle que segura a decisão de não autenticar.
#
# Somente leitura do ESTADO da fábrica (RN-1/AC-7/AC-14): nenhuma rota escreve
# em state.yaml, issue ou board. A única escrita é o banco local de telemetria
# em `dados/` (RN-12), que é cache de fonte durável: apagá-lo e recarregar
# devolve o mesmo Kanban, e conteúdo de mensagem nunca entra nele (RN-2,
# travado pelo canário em testes/teste_canario.py).
#
# Uso: faber/dashboard/dashboard.sh [porta]
#      ou .venv/bin/python faber/dashboard/app.py --porta 8099
# =============================================================================
"""Servidor local do dashboard da fábrica (Kanban somente leitura)."""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, abort, render_template, request  # noqa: E402

import banco  # noqa: E402
import leitor  # noqa: E402
import telemetria  # noqa: E402

HOST = "127.0.0.1"  # inegociável: ver cabeçalho
PORTA_PADRAO = 8099

# A telemetria é lida a cada request, sem daemon: a varredura incremental
# custa 0,87–19,6 ms medidos, contra 660–740 ms que a projeção do Kanban já
# gasta. Gatilho para promover a thread, se um dia doer: incremental acima de
# ~150 ms em regime.
MENSAGENS_POR_PAGINA = 200      # paginação do histórico (AC-2 borda)
TRANSCRIPTS_NO_CARD = 3         # quantos arquivos o card relê para achar as últimas
SEGUNDOS_AUTO_REFRESH = 15      # só quando há demanda ao vivo
# Nomes aceitos no cabeçalho `Host`. Qualquer outro é rebinding ou proxy: o
# pacote chega igual ao de um acesso legítimo, e o `Host` é o único lugar onde
# os dois se distinguem.
ANFITRIOES = ("127.0.0.1", "localhost", "[::1]")

app = Flask(__name__)
# Jinja2 com autoescape (padrão do Flask para .html) é o controle de XSS do
# `titulo`, que vem do título da issue no GitHub. Nenhum template usa |safe.
app.jinja_env.autoescape = True
app.config["ESQUEMA"] = leitor.carregar_esquema()
app.config["RAIZ"] = None  # None = descobre pelo git-common-dir (testes injetam)
app.config["BANCO"] = banco.BANCO_PADRAO      # faber/dashboard/dados/telemetria.sqlite
app.config["PROJETOS"] = None                 # None = ~/.claude/projects (testes injetam)
app.config["AGORA"] = None                    # None = relógio real (testes injetam)


def _projetar():
    return leitor.projetar(raiz=app.config["RAIZ"], esquema=app.config["ESQUEMA"])


def _mensagens_recentes(caminhos, demanda, demandas):
    """Últimas mensagens da demanda, relidas do JSONL: nunca do banco.

    Percorre os transcripts do mais recente para trás e para assim que tem o
    suficiente. O conteúdo nasce no request e morre nele — exibir não é reter
    (RN-1 × RN-2).
    """
    achadas = []
    for caminho in caminhos[:TRANSCRIPTS_NO_CARD]:
        achadas += telemetria.mensagens_do_arquivo(caminho, demanda, demandas)
        if len(achadas) >= telemetria.MENSAGENS_NO_CARD:
            break
    achadas.sort(key=lambda m: m.em)
    return achadas[-telemetria.MENSAGENS_NO_CARD:]


def _telemetria(projecao, com_mensagens=True):
    """Varre os transcripts, atualiza o banco e monta o que as telas exibem.

    Falha de banco (ausente, corrompido, travado) NUNCA derruba o Kanban: vira
    `indisponivel`, a tela avisa, e a projeção do `state.yaml` segue inteira.
    É a mesma disciplina do `degradada` do Kanban — quem não conseguiu ler diz
    que não conseguiu, em vez de devolver vazio.
    """
    demandas = {d["nome"] for d in projecao["demandas"]}
    dados = {"por_demanda": {}, "fora": {"saida": 0, "requisicoes": 0},
             "indisponivel": None, "varredura": None, "ao_vivo": 0}
    agora = app.config["AGORA"]
    try:
        con = banco.abrir(app.config["BANCO"])
        try:
            dados["varredura"] = banco.sincronizar(
                con, projecao["raiz"], demandas, app.config["PROJETOS"])
            dados["fora"] = banco.fora_de_demanda(con)
            for nome, tokens in banco.tokens_por_demanda(con).items():
                agentes = [(a, e) for a, e in banco.agentes_da_demanda(con, nome)
                           if telemetria.esta_ao_vivo(e, agora)]
                caminhos = banco.transcripts_da_demanda(con, nome)
                ao_vivo = telemetria.esta_ao_vivo(tokens["ultimo_em"], agora)
                dados["por_demanda"][nome] = {
                    "tokens": tokens,
                    "ao_vivo": ao_vivo,
                    "idade": telemetria.idade_em_segundos(tokens["ultimo_em"], agora),
                    # o mais recente na janela + quantos outros atuam junto
                    "agente": agentes[0][0] if agentes else "",
                    "outros": max(0, len(agentes) - 1),
                    "agentes_vivos": agentes,
                    "modelo": banco.modelo_da_demanda(con, nome),  # None ⇒ "sem dados"
                    "transcripts": caminhos,
                    "mensagens": _mensagens_recentes(caminhos, nome, demandas)
                    if com_mensagens else [],
                }
                dados["ao_vivo"] += 1 if ao_vivo else 0
        finally:
            con.close()
    except banco.ErroTelemetria as erro:
        dados["indisponivel"] = "%s: %s" % (type(erro).__name__, erro)
    except OSError as erro:  # pasta de dados sem permissão, disco cheio…
        dados["indisponivel"] = "armazenamento local indisponível: %s" % erro
    return dados


def anfitriao(host):
    """Nome do `Host` sem a porta (`[::1]:8099` → `[::1]`), em caixa baixa."""
    host = (host or "").strip().lower()
    if host.startswith("["):  # literal IPv6
        return host.split("]")[0] + "]"
    return host.split(":")[0]


@app.before_request
def so_anfitriao_local():
    """Recusa request cujo `Host` não seja o localhost (ver cabeçalho)."""
    if anfitriao(request.host) not in ANFITRIOES:
        abort(403)


@app.errorhandler(403)
def anfitriao_recusado(_erro):
    return render_template(
        "erro.html",
        codigo=403,
        titulo="Host não permitido",
        mensagem="Host não permitido: este dashboard só responde a %s." % ", ".join(ANFITRIOES),
    ), 403


@app.route("/")
def kanban():
    """Quadro completo. `?q=` filtra por ID ou título (AC-8).

    `?vivo=0` desliga o auto-refresh: útil para ler a tela com calma
    enquanto uma execução está rodando.
    """
    termo = (request.args.get("q") or "").strip()
    projecao = _projetar()
    tel = _telemetria(projecao)
    # Recarrega sozinho só quando há o que mudar. Tela parada não recarrega:
    # é meta-refresh, não push — SSE está fora do escopo.
    auto = tel["ao_vivo"] > 0 and request.args.get("vivo") != "0"
    return render_template(
        "kanban.html",
        projecao=projecao,
        quadro=leitor.quadro(projecao, app.config["ESQUEMA"], termo),
        termo=termo,
        tel=tel,
        limiar=telemetria.LIMIAR_LIVE_S,
        auto_refresh=SEGUNDOS_AUTO_REFRESH if auto else 0,
    )


@app.route("/faber-task/<nome>")
def demanda(nome):
    """Detalhe: transições, gates, cópias (AC-4) e o histórico de output (AC-2).

    `?pagina=N` pagina o histórico, do mais recente para o mais antigo — sem
    JavaScript, mesmo padrão da busca. É o que impede que uma execução de
    milhares de mensagens trave a tela.
    """
    projecao = _projetar()
    achada = next((d for d in projecao["demandas"] if d["nome"] == nome), None)
    if achada is None:
        abort(404)
    tel = _telemetria(projecao, com_mensagens=False)
    minha = tel["por_demanda"].get(nome)

    demandas = {d["nome"] for d in projecao["demandas"]}
    historico = []
    for caminho in (minha or {}).get("transcripts", []):
        historico += telemetria.historico_do_arquivo(caminho, nome, demandas)
    historico.sort(key=lambda m: m.em, reverse=True)

    try:
        pagina = max(1, int(request.args.get("pagina") or 1))
    except ValueError:
        pagina = 1
    paginas = max(1, -(-len(historico) // MENSAGENS_POR_PAGINA))
    pagina = min(pagina, paginas)
    inicio = (pagina - 1) * MENSAGENS_POR_PAGINA
    return render_template(
        "demanda.html",
        projecao=projecao,
        d=achada,
        tel=tel,
        minha=minha,
        historico=historico[inicio:inicio + MENSAGENS_POR_PAGINA],
        total_historico=len(historico),
        pagina=pagina,
        paginas=paginas,
        limiar=telemetria.LIMIAR_LIVE_S,
    )


@app.errorhandler(404)
def nao_encontrada(_erro):
    return render_template("erro.html", mensagem="Demanda não encontrada."), 404


def main(argv=None):
    p = argparse.ArgumentParser(description="Dashboard local da fábrica (somente leitura).")
    p.add_argument("--porta", type=int, default=PORTA_PADRAO, help="porta TCP (padrão: %d)" % PORTA_PADRAO)
    args = p.parse_args(argv)
    print("dashboard da fábrica em http://%s:%d  (somente leitura, Ctrl+C encerra)" % (HOST, args.porta))
    # debug=False é deliberado: o debugger do Werkzeug executa código a partir
    # do navegador — inaceitável mesmo em localhost.
    app.run(host=HOST, port=args.porta, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
