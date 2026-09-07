#!/usr/bin/env python3
# =============================================================================
# telemetria.py — leitura dos transcripts JSONL do Claude Code: descoberta,
# leitura incremental, extração e atribuição por linha.
# CANÁRIO-TRAVA-DEPLOY: FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH
#
# Este módulo é SOMENTE LEITURA sobre `~/.claude/projects` e **não importa
# sqlite3**: quem persiste é `banco.py`, e só ele. A separação existe
# para que a lista branca de campos persistíveis (RN-2) more num lugar só
# e seja auditável — aqui, o `Evento` simplesmente NÃO TEM campo de conteúdo,
# então vazar conteúdo para o banco exigiria mudar a estrutura de dados, não
# esquecer um `del`.
#
# As cinco armadilhas medidas em transcripts reais, e onde cada uma é tratada:
#   RN-4 dedup MAX por requestId .... `banco.py` (UPSERT MAX); aqui os eventos
#                                     saem crus, um por linha
#   RN-5 subagents/*.jsonl .......... `transcripts()` — mais da metade dos
#                                     requests costuma estar nesses arquivos
#   RN-6 worktree ................... atribuição por LINHA (`gitBranch`), ver
#                                     `demanda_da_branch`
#   RN-7 filtro exato de repo ....... `pastas_de_projeto()` — nome exato OU
#                                     prefixo `<slug>--claude-worktrees-`
#   RN-8 linha parcial .............. `ler_incremental()` corta no último \n
#
# Por que atribuir por LINHA e nunca por arquivo: uma parcela relevante dos
# transcripts contém mais de uma `gitBranch`. O transcript é da SESSÃO, e a
# sessão troca de demanda ao longo do dia. Atribuir por arquivo/pasta soma o
# gasto de uma demanda em outra, em silêncio.
# =============================================================================
"""Leitura dos transcripts JSONL: descoberta, incremental, extração, atribuição."""

import json
import re
import sys
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

PROVEDOR_PADRAO = "claude-code"
RAIZ_PROJETOS_PADRAO = Path.home() / ".claude" / "projects"

# Limiar do indicador "ao vivo". NÃO é chute: medido sobre milhares de
# intervalos assistant→assistant (tempo de MÁQUINA trabalhando, sem espera por
# humano), o p99 ficou em ~64 s — 90 s ≈ 1,4× o p99, o que deixa <1% de
# piscada falsa. A 60 s a piscada quase dobra; a 120 s compra pouco e cobra
# 30 s a mais de "morto parecendo vivo".
LIMIAR_LIVE_S = 90

MENSAGENS_NO_CARD = 5      # RN-1/AC-1: mostra até 5, e o que houver se for menos
LIMITE_TEXTO = 200         # p50 do bloco `text` é ~130 chars — a maioria cabe inteira
JANELA_TAIL = 256 * 1024   # tail lido para achar as últimas mensagens do card

# Ordem de leitura do `input` de um `tool_use` para o resumo de uma linha.
# É o que o Owner veria no terminal; a chave que existir primeiro ganha.
CHAVES_FERRAMENTA = ("command", "file_path", "pattern", "path", "url", "query",
                     "description", "prompt", "notebook_path")

# Sessão principal (CTO): linha com `usage` e sem `attributionAgent`.
# Nunca deixar vazio — campo em branco vira "não sei" na tela, e aqui se sabe.
AGENTE_SESSAO_PRINCIPAL = "cto"

_TAREFA = re.compile(r"TASK-(\d+)")


# `Evento` é deliberadamente fechado: todo campo aqui é da lista branca da
# RN-2. Não existe campo de conteúdo — é a trava estrutural que o
# canário (AC-3) confere depois, em bytes.
Evento = namedtuple("Evento", (
    "request_id", "session_id", "git_branch", "demanda", "agente", "modelo",
    "provedor", "entrada", "saida", "cache_criacao", "cache_leitura", "em",
))

# Mensagem EXIBIDA (RN-1). Nunca persistida: nasce no request e morre nele.
Mensagem = namedtuple("Mensagem", ("em", "agente", "tipo", "texto"))


# ── Descoberta (RN-5 / RN-7) ─────────────────────────────────────────────────


def slug_de(caminho):
    """Nome da pasta que o Claude Code cria para um diretório de lançamento.

    A regra é literal: todo caractere fora de [A-Za-z0-9] vira `-`. Por isso
    `.claude` vira `-claude` e a worktree aparece como
    `<slug>--claude-worktrees-TASK-XXX` (dois traços: um da `/`, um do `.`).
    """
    return re.sub(r"[^A-Za-z0-9]", "-", str(caminho))


def pastas_de_projeto(raiz_repo, raiz_projetos=None):
    """Pastas de `~/.claude/projects` que pertencem a ESTE repositório (RN-7).

    Nome **exato** do slug, ou prefixo `<slug>--claude-worktrees-`. Um
    `startswith(slug + "-")` puro casaria `<slug>-backup`, `-2`, `-old`:
    clones do mesmo repo, com as mesmas branches `feature/TASK-*`, cujo
    consumo entraria na conta da demanda sem nenhum sinal.
    """
    raiz = Path(raiz_projetos or RAIZ_PROJETOS_PADRAO)
    alvo = slug_de(Path(raiz_repo))
    prefixo = alvo + "--claude-worktrees-"
    try:
        candidatas = sorted(raiz.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        return []  # nunca houve execução aqui: ausência de dado, não falha
    # Qualquer outro OSError (permissão negada, volume desmontado) SOBE: quem
    # chama transforma em "telemetria indisponível". Engolir
    # devolveria tudo zerado, indistinguível de "nunca houve execução" — é o
    # "ler zero como custou zero" que o aviso da própria tela existe para
    # evitar. Ferramenta indisponível é declarada, nunca inferida.
    return [p for p in candidatas
            if p.is_dir() and (p.name == alvo or p.name.startswith(prefixo))]


def transcripts(raiz_repo, raiz_projetos=None):
    """Todos os transcripts do repositório: [(caminho, origem), ...].

    Inclui `<sessão>/subagents/*.jsonl` (RN-5). Os subagentes costumam ser a
    maioria dos ARQUIVOS e mais da metade dos REQUESTS; um glob `*.jsonl`
    ingênuo perde mais da metade do consumo real.
    """
    achados = []
    for pasta in pastas_de_projeto(raiz_repo, raiz_projetos):
        for f in sorted(pasta.glob("*.jsonl")):
            achados.append((f, "sessao"))
        for f in sorted(pasta.glob("*/subagents/*.jsonl")):
            achados.append((f, "subagente"))
    return achados


# ── Leitura incremental (RN-8 / AC-12) ───────────────────────────────────────


def ler_incremental(caminho, deslocamento=0):
    """Lê de `deslocamento` até o ÚLTIMO `\\n` completo.

    Devolve `(linhas, novo_deslocamento)`. O transcript vivo é escrito por
    *append*: parar no último `\\n` é o que impede meia linha de virar evento
    (RN-8). O deslocamento só avança sobre bytes efetivamente terminados, então
    a linha incompleta é relida inteira na próxima varredura — e reprocessar é
    inofensivo porque o agregado é `MAX`, não soma (RN-4/RN-9).

    Arquivo menor que o deslocamento = truncado ou recriado: relê do zero, sob
    pena de casar offset velho com conteúdo novo.
    """
    caminho = Path(caminho)
    try:
        tamanho = caminho.stat().st_size
    except OSError:
        return [], deslocamento
    inicio = 0 if tamanho < deslocamento else deslocamento
    if tamanho == inicio:
        return [], inicio
    try:
        with caminho.open("rb") as fh:
            fh.seek(inicio)
            bruto = fh.read()
    except OSError:
        return [], deslocamento
    corte = bruto.rfind(b"\n")
    if corte < 0:
        return [], inicio  # nem uma linha completa ainda: não avança nada
    completo = bruto[:corte + 1]
    return [l for l in completo.split(b"\n") if l.strip()], inicio + len(completo)


# ── Atribuição por linha (RN-6) ──────────────────────────────────────────────


def demanda_da_branch(branch, demandas_conhecidas):
    """`feature/TASK-123` → `TASK-123`. Sem mapeamento → None.

    Duas regras:

    1. `TASK-(\\d+)` em QUALQUER posição do nome. A fábrica trabalha uma
       demanda em `docs/TASK-XX-specs` e `fix/TASK-XX-...` também — um
       `done` commitado numa branch `docs/` conta para a demanda do número.
    2. A demanda precisa EXISTIR na projeção do Kanban. Sem isso, uma branch
       com número datilografado errado criaria uma demanda fantasma no banco.

    Branch sem demanda (develop, `release/…`, branches de manutenção) devolve
    None. Esses requests não são rateados nem escondidos — viram o KPI "fora
    de demanda", porque ratear seria número inferido e sumir com eles seria
    buraco silencioso.
    """
    if not isinstance(branch, str) or not branch:
        return None
    achado = _TAREFA.search(branch)
    if not achado:
        return None
    nome = "TASK-%s" % achado.group(1)
    return nome if nome in (demandas_conhecidas or ()) else None


# ── Extração: só a lista branca sai daqui (RN-2) ─────────────────────────────


def _inteiro(valor):
    return valor if isinstance(valor, int) and valor >= 0 else 0


def _dt(valor):
    """ISO-8601 → datetime aware; None quando ausente/ilegível.

    Mesma disciplina do `leitor.py`: timestamp ruim derruba o evento, nunca
    a tela.
    """
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        d = datetime.fromisoformat(valor.strip().replace("Z", "+00:00"))
    except (ValueError, OverflowError, OSError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def evento_da_linha(bruto, demandas_conhecidas, provedor=PROVEDOR_PADRAO):
    """Uma linha JSONL → `Evento`, ou None se a linha não é telemetria.

    Exige `message.usage` **e** `requestId`: é a regra de produção. Contar
    por regex gera falsos positivos e leva à conclusão errada de que
    sessão-pai e subagente duplicam requests (medido: nenhum `requestId`
    aparece em mais de um arquivo).

    Nenhum campo de `message.content` é copiado para o retorno — o `Evento`
    nem tem onde guardar.
    """
    try:
        dados = json.loads(bruto)
    except (ValueError, TypeError):
        return None  # linha parcial que escapou, JSON quebrado: ignora em silêncio
    if not isinstance(dados, dict):
        return None
    mensagem = dados.get("message")
    if not isinstance(mensagem, dict):
        return None
    uso = mensagem.get("usage")
    request_id = dados.get("requestId")
    if not isinstance(uso, dict) or not isinstance(request_id, str) or not request_id:
        return None

    branch = dados.get("gitBranch") if isinstance(dados.get("gitBranch"), str) else None
    agente = dados.get("attributionAgent") or dados.get("agentId")
    if not isinstance(agente, str) or not agente:
        agente = AGENTE_SESSAO_PRINCIPAL  # ausência é informação, não vazio
    modelo = mensagem.get("model")
    return Evento(
        request_id=request_id,
        session_id=dados.get("sessionId") if isinstance(dados.get("sessionId"), str) else None,
        git_branch=branch,
        demanda=demanda_da_branch(branch, demandas_conhecidas),
        agente=agente,
        modelo=modelo if isinstance(modelo, str) and modelo else None,  # None ⇒ "sem dados" (AC-13)
        provedor=provedor,
        entrada=_inteiro(uso.get("input_tokens")),
        saida=_inteiro(uso.get("output_tokens")),
        cache_criacao=_inteiro(uso.get("cache_creation_input_tokens")),
        cache_leitura=_inteiro(uso.get("cache_read_input_tokens")),
        em=dados.get("timestamp") if isinstance(dados.get("timestamp"), str) else None,
    )


def eventos_de(linhas, demandas_conhecidas, provedor=PROVEDOR_PADRAO):
    """Aplica `evento_da_linha` a uma lista de linhas, descartando o que não é."""
    saida = []
    for linha in linhas:
        evento = evento_da_linha(linha, demandas_conhecidas, provedor)
        if evento is not None:
            saida.append(evento)
    return saida


# ── Mensagens exibidas: lidas no request, nunca persistidas (RN-1) ───────────


def _resumo_ferramenta(bloco):
    """`tool_use` → uma linha, no formato que aparece no terminal."""
    nome = bloco.get("name")
    nome = nome if isinstance(nome, str) and nome else "ferramenta"
    entrada = bloco.get("input")
    if isinstance(entrada, dict):
        for chave in CHAVES_FERRAMENTA:
            valor = entrada.get(chave)
            if isinstance(valor, str) and valor.strip():
                return "%s: %s" % (nome, _truncar(valor.strip()))
    return nome


def _truncar(texto, limite=LIMITE_TEXTO):
    texto = " ".join(str(texto).split())  # quebra de linha no card vira ruído
    return texto if len(texto) <= limite else texto[:limite].rstrip() + "…"


def _carregar(bruto):
    """Linha JSONL → dict, ou None. Um `json.loads` por linha, e só um.

    Existe para que o painel de detalhe não desserialize a mesma linha duas
    vezes (uma para a branch, outra para a mensagem): num transcript grande
    isso dobrava o custo do histórico à toa.
    """
    try:
        dados = json.loads(bruto)
    except (ValueError, TypeError):
        return None
    return dados if isinstance(dados, dict) else None


def mensagem_de(dados):
    """Dict de uma linha `type: assistant` → `Mensagem` exibível, ou None.

    - bloco `text` → texto truncado em ~200 caracteres (p50 medido: ~130);
    - bloco `tool_use` → resumo de uma linha (`Bash: npm run build`);
    - bloco `thinking` → **nunca**. É o conteúdo mais sensível que existe e o
      p90 do tamanho é 0 (quase sempre vazio): não exibir custa nada e evita
      tudo. Decisão do Owner.

    Uma linha vira no máximo UMA mensagem: vence o primeiro bloco exibível na
    ordem em que o modelo os emitiu.
    """
    if not isinstance(dados, dict) or dados.get("type") != "assistant":
        return None
    mensagem = dados.get("message")
    if not isinstance(mensagem, dict):
        return None
    blocos = mensagem.get("content")
    if isinstance(blocos, str):
        blocos = [{"type": "text", "text": blocos}]
    if not isinstance(blocos, list):
        return None
    agente = dados.get("attributionAgent") or dados.get("agentId")
    if not isinstance(agente, str) or not agente:
        agente = AGENTE_SESSAO_PRINCIPAL
    em = dados.get("timestamp") if isinstance(dados.get("timestamp"), str) else ""
    for bloco in blocos:
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("type")
        if tipo == "text" and isinstance(bloco.get("text"), str) and bloco["text"].strip():
            return Mensagem(em=em, agente=agente, tipo="text", texto=_truncar(bloco["text"]))
        if tipo == "tool_use":
            return Mensagem(em=em, agente=agente, tipo="tool_use", texto=_resumo_ferramenta(bloco))
    return None


def mensagem_da_linha(bruto):
    """`mensagem_de` a partir dos bytes crus (conveniência de teste)."""
    return mensagem_de(_carregar(bruto))


def _e_da_demanda(dados, demanda, demandas_conhecidas):
    """A linha pertence à demanda pedida? (filtro do card e do detalhe)

    Sem isto, o card de uma demanda mostraria o que o agente fez em outra:
    o transcript é da SESSÃO, e muitos atravessam mais de uma branch. De
    quebra, conteúdo de linha sem demanda (develop) não chega a tela nenhuma.
    """
    if demanda is None:
        return True
    branch = dados.get("gitBranch") if isinstance(dados, dict) else None
    return demanda_da_branch(branch if isinstance(branch, str) else None,
                             demandas_conhecidas) == demanda


def mensagens_do_arquivo(caminho, demanda, demandas_conhecidas, limite=MENSAGENS_NO_CARD,
                         janela=JANELA_TAIL):
    """Últimas mensagens exibíveis de UM transcript, já filtradas pela demanda.

    Lê só o fim do arquivo (`janela` bytes): medido, tail de 128 KB + parse das
    últimas linhas de 6 transcripts custa 4 ms, contra 660–740 ms que a
    projeção do Kanban já gasta no mesmo request.

    O filtro por demanda não é zelo: como o transcript é da sessão e a sessão
    troca de branch, sem ele o card de uma demanda mostraria o que o agente
    fez em outra. De quebra, conteúdo de linha sem demanda (develop) não chega
    a tela nenhuma.
    """
    caminho = Path(caminho)
    try:
        tamanho = caminho.stat().st_size
        with caminho.open("rb") as fh:
            fh.seek(max(0, tamanho - janela))
            bruto = fh.read()
    except OSError:
        return []  # transcript removido: "sem dados" (AC-11), nunca erro
    if tamanho > janela:
        corte = bruto.find(b"\n")  # a 1ª linha da janela quase certamente está cortada
        bruto = bruto[corte + 1:] if corte >= 0 else b""
    achadas = []
    for linha in reversed([l for l in bruto.split(b"\n") if l.strip()]):
        dados = _carregar(linha)
        if dados is None or not _e_da_demanda(dados, demanda, demandas_conhecidas):
            continue
        mensagem = mensagem_de(dados)
        if mensagem is not None:
            achadas.append(mensagem)
            if len(achadas) >= limite:
                break
    return list(reversed(achadas))


def historico_do_arquivo(caminho, demanda, demandas_conhecidas):
    """TODAS as mensagens exibíveis de um transcript, para o painel de detalhe.

    Lê o arquivo inteiro (um transcript de 7 MB custa ~5 ms). O que
    protege a tela de "milhares de mensagens" é a paginação em `app.py`, não
    uma leitura parcial que perderia histórico.
    """
    try:
        bruto = Path(caminho).read_bytes()
    except OSError:
        return []
    achadas = []
    for linha in bruto.split(b"\n"):
        if not linha.strip():
            continue
        dados = _carregar(linha)
        if dados is None or not _e_da_demanda(dados, demanda, demandas_conhecidas):
            continue
        mensagem = mensagem_de(dados)
        if mensagem is not None:
            achadas.append(mensagem)
    return achadas


# ── Atividade "ao vivo" (RN-13) ──────────────────────────────────────────────


def esta_ao_vivo(ultimo_em, agora=None, limiar=LIMIAR_LIVE_S):
    """Houve atividade nos últimos `limiar` segundos? (AC-9/AC-10)

    `agora` é injetável: o cenário de borda (89 s = LIVE, 91 s = sem LIVE) tem
    que ser determinístico, e `time.sleep` em teste é lentidão comprada com
    intermitência.
    """
    quando = _dt(ultimo_em)
    if quando is None:
        return False
    referencia = agora or datetime.now(timezone.utc)
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    idade = (referencia - quando).total_seconds()
    # Janela do PASSADO. Era simétrica, e um timestamp no
    # futuro (skew de relógio, fuso trocado na origem) acendia o LIVE por até
    # 90 s e depois apagava — dado errado indistinguível de "parado". Os ACs
    # falam de atividade RECENTE: futuro não é recente, é relógio quebrado.
    return 0 <= idade <= limiar


def idade_em_segundos(ultimo_em, agora=None):
    """Segundos desde a última atividade, ou None. Vai cru para a tela.

    É o antídoto honesto para a piscada falsa: uma ferramenta longa
    (`npm run build`) deixa o transcript mudo e o LIVE apaga; mostrar
    "última atividade há 96 s" ao lado explica sozinho, sem inventar estado.
    """
    quando = _dt(ultimo_em)
    if quando is None:
        return None
    referencia = agora or datetime.now(timezone.utc)
    if referencia.tzinfo is None:
        referencia = referencia.replace(tzinfo=timezone.utc)
    return max(0, int((referencia - quando).total_seconds()))
