#!/usr/bin/env python3
# =============================================================================
# leitor.py — leitura multi-fonte dos state.yaml e projeção do Kanban.
# CANÁRIO-TRAVA-DEPLOY: FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH
# Somente leitura: este módulo nunca escreve nada em disco (AC-7) e nunca
# levanta exceção por conteúdo de arquivo (AC-10).
#
# Por que multi-fonte (RN-13 / AC-1): não existe "a pasta faber/tasks/".
# A mesma demanda tem cópias em vários checkouts (worktrees do /faber-resume) e em
# várias refs do git, e elas DIVERGEM. Ler um diretório só entrega um Kanban
# errado com cara de certo. A cópia autoritativa é a de maior `atualizada_em`,
# varridas todas as fontes.
#
# Por que validar contra lista fechada (AC-10): os scripts da fábrica
# gravam state.yaml sem tmp+rename, então um arquivo lido no meio da escrita
# PARSEIA COM SUCESSO e devolve `estado: 'refi'`. Estado fora dos 15 do
# state.template.yaml é LEITURA INVÁLIDA, nunca estado.
#
# Fonte que falha é DECLARADA, nunca inferida (regra da fábrica): `projetar`
# devolve `falhas`/`degradada` e a tela avisa. Quadro incompleto que se cala é
# pior que quadro que não carrega — parece "nada a fazer".
#
# A lista de estados, tipos e o mapa estado→coluna NÃO são copiados para cá:
# são lidos de faber/templates/state.template.yaml (_schema), que é a fonte
# única que o board.sh também usa. Copiar seria dívida garantida.
# =============================================================================
"""Leitura multi-fonte dos state.yaml da fábrica e projeção do Kanban."""

import importlib.util
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# Vale para o que este processo importar DAQUI PARA BAIXO — não para este
# próprio arquivo, que já foi compilado pelo interpretador que nos importou.
# A garantia de não deixar __pycache__ no repositório vem do lançador
# (dashboard.sh: `-B` + PYTHONDONTWRITEBYTECODE exportada), e o teste
# `test_nenhum_pycache_versionado` cobra isso.
sys.dont_write_bytecode = True

import yaml  # noqa: E402  (após o dont_write_bytecode, de propósito)

try:  # libyaml: ~9x mais rápido; ausente em algum ambiente, o puro-Python serve
    from yaml import CSafeLoader as _Loader
except ImportError:  # pragma: no cover - depende do build do PyYAML
    from yaml import SafeLoader as _Loader

# ── Reuso do monitor.py ──────────────────────────────────────────────────────
# Importado como módulo, JAMAIS editado: dele vêm a ordem dos gates, a regra da
# fila do Owner, o status de gate e a numeração de TASK. Recriar essas
# regras aqui seria dívida garantida.
_AQUI = Path(__file__).resolve().parent


def _carregar_monitor(caminho):
    """Importa monitor.py por caminho. Ausência vira mensagem útil.

    Sem a checagem, `monitor.py` fora do lugar rebentava num `AttributeError`
    cru de dentro do importlib, sem dizer o que faltava nem onde.
    """
    caminho = Path(caminho)
    spec = importlib.util.spec_from_file_location("monitor", caminho)
    if spec is None or spec.loader is None or not caminho.is_file():
        raise ImportError(
            "o dashboard reusa as regras de gates de monitor.py e não o "
            "encontrou em %s" % caminho
        )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


monitor = _carregar_monitor(_AQUI.parent / "scripts" / "monitor.py")

GATES_ORDEM = monitor.GATES_ORDEM
numero_tarefa = monitor.numero_tarefa
status_gate = monitor.status_gate
aguarda_owner = monitor.aguarda_owner

TEMPLATE_PADRAO = _AQUI.parent / "templates" / "state.template.yaml"
TIMEOUT_GIT = 20  # segundos por chamada de git; nenhuma delas é interativa
ORCAMENTO_GIT = 60  # teto para a SOMA das ~22 chamadas de uma projeção



# ── Esquema (estados, tipos e colunas) lido do template da fábrica ───────────


class Esquema:
    """Lista fechada de estados/tipos e o mapa estado→coluna macro."""

    def __init__(self, estados, tipos, colunas):
        self.estados = tuple(estados)
        self.tipos = tuple(tipos)
        self.colunas = tuple(colunas)  # [(nome_coluna, (estados,)), ...] na ordem
        self._por_estado = {e: nome for nome, ests in colunas for e in ests}

    def coluna_de(self, estado):
        """Coluna macro do estado, ou None (cancelled e desconhecidos)."""
        return self._por_estado.get(estado)

    def estado_valido(self, estado):
        return estado in self.estados

    def tipo_valido(self, tipo):
        return tipo in self.tipos


def carregar_esquema(caminho=TEMPLATE_PADRAO):
    """Lê `_schema` do state.template.yaml. Falha ALTO: sem esquema não há
    lista fechada, e sem lista fechada o dashboard inventaria estado."""
    texto = Path(caminho).read_text(encoding="utf-8")
    dados = yaml.load(texto, Loader=_Loader)
    esquema = (dados or {}).get("_schema") or {}
    estados = esquema.get("states")
    tipos = esquema.get("types")
    colunas = esquema.get("board_columns")
    if not (isinstance(estados, list) and isinstance(tipos, list) and isinstance(colunas, dict)):
        raise ValueError("_schema inválido em %s (states/types/board_columns)" % caminho)
    return Esquema(estados, tipos, [(nome, tuple(ests or [])) for nome, ests in colunas.items()])


# ── Leitura tolerante de um state.yaml (AC-10) ───────────────────────────────

ERRO_VAZIO = "arquivo vazio"
ERRO_PARSE = "YAML ilegível"
ERRO_NAO_MAPA = "topo não é um mapa YAML"
ERRO_ESTADO = "estado fora da lista dos %d estados oficiais"


def _texto(valor):
    return str(valor) if valor is not None else ""


def _dt(valor):
    """ISO-8601 → datetime aware; None se ausente, ilegível ou fora de faixa.

    Comparar string funcionaria só enquanto todo timestamp usar o mesmo
    offset — comparar datetime não depende dessa sorte.

    O `astimezone()` fica DENTRO do try de propósito: um valor naive nos
    extremos da faixa ('9999-12-31T23:59:59', '0001-01-01T00:00:00') parseia
    bem e estoura só na conversão de fuso. Com ele fora do try, esse
    ValueError subia por `ler_state` e derrubava a tela INTEIRA — um
    state.yaml ruim tem que derrubar o card, nunca o dashboard (AC-10).
    """
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        d = datetime.fromisoformat(valor.strip())
        return d if d.tzinfo else d.astimezone()
    except (ValueError, OverflowError, OSError):
        return None


def ler_state(texto, esquema, nome=None, fonte="", origem=""):
    """Interpreta o TEXTO de um state.yaml. Nunca levanta exceção.

    Devolve sempre um dict com `valido` e `erro`: uma cópia inválida não some
    da tela nem inventa coluna — ela é sinalizada como leitura inválida.
    """
    copia = {
        "nome": nome or "",
        "numero": numero_tarefa(nome or ""),
        "fonte": fonte,
        "origem": origem,
        "valido": False,
        "erro": None,
        "demanda": nome or "",
        "issue": None,
        "titulo": "",
        "tipo": "",
        "tipo_valido": False,
        "estado": "",
        "bloqueio": None,
        "gates": {},
        "historico": [],
        "invocacoes": [],
        "atualizada_em": "",
        "atualizada_dt": None,
        "pr": None,
        "relacionada_a": None,
    }

    if not str(texto).strip():
        copia["erro"] = ERRO_VAZIO
        return copia
    try:
        dados = yaml.load(texto, Loader=_Loader)
    except Exception:  # YAML quebrado, encoding, tag insegura recusada...
        copia["erro"] = ERRO_PARSE
        return copia
    if not isinstance(dados, dict):
        copia["erro"] = ERRO_NAO_MAPA
        return copia

    copia["demanda"] = _texto(dados.get("task")) or copia["demanda"]
    copia["issue"] = dados.get("issue")
    copia["titulo"] = _texto(dados.get("title"))
    copia["tipo"] = _texto(dados.get("type"))
    copia["tipo_valido"] = esquema.tipo_valido(copia["tipo"])
    copia["estado"] = _texto(dados.get("state"))
    bloqueio = dados.get("blocking")
    copia["bloqueio"] = bloqueio if isinstance(bloqueio, dict) else None
    gates = dados.get("gates")
    copia["gates"] = gates if isinstance(gates, dict) else {}
    historico = dados.get("history")
    copia["historico"] = [h for h in historico if isinstance(h, dict)] if isinstance(historico, list) else []
    invocacoes = dados.get("invocations")
    copia["invocacoes"] = [i for i in invocacoes if isinstance(i, dict)] if isinstance(invocacoes, list) else []
    copia["atualizada_em"] = _texto(dados.get("updated_at"))
    copia["atualizada_dt"] = _dt(copia["atualizada_em"])
    copia["pr"] = dados.get("pr")
    copia["relacionada_a"] = dados.get("related_to")

    # A validação que separa "estado" de "lixo plausível" (AC-10).
    if not esquema.estado_valido(copia["estado"]):
        copia["erro"] = ERRO_ESTADO % len(esquema.estados)
        return copia

    copia["valido"] = True
    return copia


# ── Resolução da cópia autoritativa (RN-13) ──────────────────────────────────

_EPOCA = datetime.min.replace(tzinfo=timezone.utc)


def chave_resolucao(copia):
    """Ordem de precedência: `atualizada_em` > histórico mais longo > checkout.

    O critério primário é RN-13. Os desempates só existem para tornar o
    resultado determinístico quando duas cópias carimbam o mesmo instante.
    """
    return (
        copia.get("atualizada_dt") or _EPOCA,
        len(copia.get("historico") or []),
        1 if str(copia.get("fonte", "")).startswith("checkout:") else 0,
        str(copia.get("fonte", "")),
    )


def resolver(copias):
    """Cópia autoritativa entre as cópias de UMA demanda.

    Cópia inválida nunca vence de uma válida: uma leitura suja (arquivo sendo
    reescrito) é mais nova, mas não é estado. Se TODAS forem inválidas, vence
    a mais recente entre elas e a demanda aparece como leitura inválida.
    """
    if not copias:
        return None
    validas = [c for c in copias if c.get("valido")]
    return max(validas or copias, key=chave_resolucao)


# ── Estado da coleta: fonte que falha é DECLARADA, jamais inferida ───────────


class Coleta:
    """Falhas declaradas da leitura + orçamento de tempo de uma projeção.

    Sem isto, uma chamada de `git` que falha devolve vazio e cada consumidor
    lê "vazio" como "não há nada aqui": as fontes somem em silêncio e o quadro
    degrada para a leitura de um checkout só — o modo de falha que a AC-1 e a
    RN-13 existem para proibir, e que contraria a regra da fábrica ("ferramenta
    indisponível = não executado, EXPLÍCITO"). Quem não conseguiu ler tem que
    dizer que não conseguiu.

    O orçamento existe porque o timeout é POR CHAMADA e uma projeção faz ~22:
    sem teto, um repositório lento prendia a tela por minutos para no fim
    entregar um quadro incompleto.
    """

    def __init__(self, orcamento=ORCAMENTO_GIT):
        self.falhas = []
        self.limite = time.monotonic() + orcamento

    def restante(self):
        return self.limite - time.monotonic()

    def registrar(self, comando, motivo):
        """Acumula a falha; repetições viram contagem, não ruído."""
        for falha in self.falhas:
            if falha["comando"] == comando and falha["motivo"] == motivo:
                falha["vezes"] += 1
                return
        self.falhas.append({"comando": comando, "motivo": motivo, "vezes": 1})


# ── Fontes ───────────────────────────────────────────────────────────────────


def _primeira_linha(saida):
    linhas = (saida or b"").decode("utf-8", "replace").strip().splitlines()
    return linhas[0][:200] if linhas else "sem stderr"


def _git(raiz, args, entrada=None, coleta=None):
    """Executa git em modo leitura. Devolve bytes; falha vira b"" DECLARADO.

    Exit code diferente de zero, timeout, orçamento esgotado e git ausente são
    registrados na `coleta`. Devolver `stdout` ignorando o exit code é o que
    transformava "não consegui ler esta fonte" em "esta fonte está vazia".
    """
    rotulo = " ".join(["git"] + [a for a in args[:2] if not a.startswith("-")])
    limite = TIMEOUT_GIT
    if coleta is not None:
        limite = min(TIMEOUT_GIT, coleta.restante())
        if limite <= 0:
            coleta.registrar(rotulo, "orçamento de %ds da leitura esgotado" % ORCAMENTO_GIT)
            return b""
    try:
        r = subprocess.run(
            ["git", "-C", str(raiz)] + args,
            input=entrada,
            capture_output=True,
            timeout=limite,
        )
    except subprocess.TimeoutExpired:
        if coleta is not None:
            coleta.registrar(rotulo, "tempo esgotado (%.0fs)" % limite)
        return b""
    except (OSError, subprocess.SubprocessError) as erro:
        if coleta is not None:
            coleta.registrar(rotulo, "%s: %s" % (type(erro).__name__, erro))
        return b""
    if r.returncode != 0:
        if coleta is not None:
            coleta.registrar(rotulo, "exit %d — %s" % (r.returncode, _primeira_linha(r.stderr)))
        return b""
    return r.stdout or b""


def raiz_repo(inicio=None, coleta=None):
    """Raiz do checkout PRINCIPAL (não do worktree corrente, não do CWD).

    `--git-common-dir` é o mesmo padrão já usado pelo worktree.sh: rodando de
    dentro de um worktree, ele devolve o .git compartilhado, e é a partir dele
    que se enxergam todos os checkouts e todas as refs.
    """
    base = Path(inicio or _AQUI)
    saida = _git(base, ["rev-parse", "--git-common-dir"], coleta=coleta).decode("utf-8", "replace").strip()
    if not saida:
        return base
    comum = Path(saida)
    if not comum.is_absolute():
        comum = (base / comum).resolve()
    return comum.parent


def checkouts(raiz, coleta=None):
    """Todos os checkouts vivos (principal + worktrees do /faber-resume)."""
    saida = _git(raiz, ["worktree", "list", "--porcelain"], coleta=coleta).decode("utf-8", "replace")
    achados = [linha[9:].strip() for linha in saida.splitlines() if linha.startswith("worktree ")]
    caminhos = [Path(c) for c in achados] or [Path(raiz)]
    vistos, unicos = set(), []
    for c in caminhos:
        if str(c) not in vistos:
            vistos.add(str(c))
            unicos.append(c)
    return unicos


def coletar_checkouts(raiz, esquema, coleta=None):
    """Cópias vindas do sistema de arquivos (inclui trabalho não commitado)."""
    copias = []
    for checkout in checkouts(raiz, coleta):
        rotulo = "checkout:%s" % (checkout.name or str(checkout))
        base = checkout / "faber" / "tasks"
        try:
            pastas = sorted(p for p in base.iterdir() if p.is_dir() and p.name.startswith("TASK-"))
        except FileNotFoundError:
            continue  # checkout sem pasta de demandas: não é falha, é ausência
        except OSError as erro:  # permissão, volume sumindo: isso É falha
            if coleta is not None:
                coleta.registrar(rotulo, "pasta de demandas ilegível: %s" % erro.strerror)
            continue
        for pasta in pastas:
            arquivo = pasta / "state.yaml"
            try:
                texto = arquivo.read_bytes().decode("utf-8", "replace")
            except OSError as erro:
                if coleta is not None:
                    coleta.registrar(rotulo, "%s/state.yaml ilegível: %s" % (pasta.name, erro.strerror))
                continue
            copias.append(ler_state(texto, esquema, pasta.name, rotulo, str(arquivo)))
    return copias


def _blobs_por_arvore(raiz, coleta=None):
    """Mapeia cada árvore `faber/tasks` distinta às refs que a apontam.

    Refs compartilham árvore (branch antiga = mesma pasta de demandas), então
    deduplicar por SHA de árvore troca ~45 varreduras por ~19.
    """
    linhas = _git(
        raiz, ["for-each-ref", "--format=%(objectname) %(refname)", "refs/heads", "refs/remotes"],
        coleta=coleta,
    ).decode("utf-8", "replace").splitlines()
    refs = [linha.split(None, 1) for linha in linhas if linha.strip()]
    refs = [(p[0], p[1]) for p in refs if len(p) == 2]
    if not refs:
        return {}
    consulta = "".join("%s:faber/tasks\n" % sha for sha, _ in refs).encode()
    saida = _git(raiz, ["cat-file", "--batch-check"], consulta, coleta).decode("utf-8", "replace").splitlines()
    arvores = {}
    for (_, refname), resposta in zip(refs, saida):
        partes = resposta.split()
        if len(partes) == 3 and partes[1] == "tree":
            arvores.setdefault(partes[0], []).append(refname)
    return arvores


def _nome_ref(refs):
    """Rótulo curto e estável da árvore: a ref local mais curta, se houver."""
    locais = [r for r in refs if r.startswith("refs/heads/")]
    escolha = sorted(locais or refs, key=lambda r: (len(r), r))[0]
    return escolha.replace("refs/heads/", "").replace("refs/remotes/", "")


def _parsear_batch(bruto, shas, coleta=None):
    """Saída de `git cat-file --batch` → {sha: texto}, na ordem consultada.

    O formato é `<sha> blob <n>\\n<n bytes>\\n`, MENOS quando o objeto sumiu
    entre o `ls-tree` e o `cat-file` (gc/prune): aí vem `<sha> missing\\n`, que
    ocupa uma linha só. Ressincronizar nessa linha é o que impede que um único
    objeto ausente zere TODOS os blobs seguintes — antes, o `pos` não avançava,
    as demais iterações reliam o mesmo cabeçalho e viravam "arquivo vazio" em
    silêncio, fabricando leitura inválida onde havia state.yaml íntegro.
    """
    conteudo = {}
    pos = 0
    for i, sha in enumerate(shas):
        fim = bruto.find(b"\n", pos)
        if fim < 0:
            if coleta is not None:
                coleta.registrar("git cat-file", "saída truncada: %d blob(s) sem resposta" % (len(shas) - i))
            for restante in shas[i:]:
                conteudo[restante] = ""
            break
        cabecalho = bruto[pos:fim].split()
        pos = fim + 1
        if len(cabecalho) != 3 or cabecalho[1] != b"blob" or not cabecalho[2].isdigit():
            conteudo[sha] = ""
            if coleta is not None:
                coleta.registrar("git cat-file", "resposta inesperada: %s"
                                 % bruto[fim - min(fim, 60):fim].decode("utf-8", "replace"))
            continue
        tamanho = int(cabecalho[2])
        conteudo[sha] = bruto[pos:pos + tamanho].decode("utf-8", "replace")
        pos += tamanho + 1
    return conteudo


def coletar_git(raiz, esquema, coleta=None):
    """Cópias vindas das refs do git (demandas sem checkout vivo)."""
    arvores = _blobs_por_arvore(raiz, coleta)
    if not arvores:
        return []

    conteudo = {}  # sha do blob → texto (um blob idêntico é lido/parseado 1x)
    por_arvore = {}
    for arvore in arvores:
        itens = []
        # `-z`: registros separados por NUL e caminho CRU. Sem ele, o git cita
        # caminho não-ASCII em C-style ("TASK-77-convers\303\243o/...") e a
        # demanda era descartada em silêncio por não começar com "TASK-".
        saida = _git(raiz, ["ls-tree", "-r", "-z", arvore], coleta=coleta).decode("utf-8", "replace")
        for registro in saida.split("\0"):
            if "\t" not in registro:
                continue
            meta, caminho = registro.split("\t", 1)
            partes = meta.split()
            if len(partes) < 3 or not caminho.startswith("TASK-") or not caminho.endswith("/state.yaml"):
                continue
            sha = partes[2]
            itens.append((caminho.split("/")[0], sha))
            conteudo[sha] = None
        por_arvore[arvore] = itens

    shas = list(conteudo)
    if shas:
        bruto = _git(raiz, ["cat-file", "--batch"], ("\n".join(shas) + "\n").encode(), coleta)
        conteudo = _parsear_batch(bruto, shas, coleta)

    cache, copias = {}, []
    for arvore, itens in por_arvore.items():
        rotulo = "git:%s" % _nome_ref(arvores[arvore])
        for nome, sha in itens:
            base = cache.get(sha)
            if base is None:
                base = ler_state(conteudo.get(sha) or "", esquema, nome)
                cache[sha] = base
            copia = dict(base)
            copia["nome"] = nome
            copia["numero"] = numero_tarefa(nome)
            copia["fonte"] = rotulo
            copia["origem"] = "%s:faber/tasks/%s/state.yaml @ %s" % (rotulo[4:], nome, sha[:8])
            copias.append(copia)
    return copias


def coletar(raiz=None, esquema=None, coleta=None):
    """Todas as cópias de todas as fontes, agrupadas por demanda."""
    coleta = coleta if coleta is not None else Coleta()
    raiz = raiz or raiz_repo(coleta=coleta)
    esquema = esquema or carregar_esquema()
    grupos = {}
    for copia in coletar_checkouts(raiz, esquema, coleta) + coletar_git(raiz, esquema, coleta):
        grupos.setdefault(copia["nome"], []).append(copia)
    return grupos


# ── Projeção do Kanban ───────────────────────────────────────────────────────


def _ultimo(lista):
    for item in reversed(lista or []):
        if isinstance(item, dict):
            return item
    return None


def agente_atuante(demanda):
    """Último subagente invocado. Vazio quando não há.

    Nunca preenche com 'Owner' por padrão: campo vazio é informação, chute
    não é.
    """
    inv = _ultimo(demanda.get("invocacoes"))
    return _texto((inv or {}).get("agent"))


def montar_demanda(nome, copias, esquema):
    """Consolida as cópias de uma demanda no card exibido."""
    vencedora = resolver(copias)
    d = dict(vencedora)
    d["nome"] = nome
    d["numero"] = numero_tarefa(nome)
    d["copias"] = sorted(copias, key=chave_resolucao, reverse=True)
    d["total_copias"] = len(copias)
    estados = sorted({c["estado"] for c in copias if c.get("valido")})
    d["estados_divergentes"] = estados if len(estados) > 1 else []
    d["coluna"] = esquema.coluna_de(d["estado"]) if d.get("valido") else None
    d["gate_corrente"] = monitor.gate_corrente(d) if d.get("valido") else None
    d["aguarda_owner"] = aguarda_owner(d) if d.get("valido") else None
    d["agente"] = agente_atuante(d)
    d["destaque"] = d["estado"] if d.get("valido") and d["estado"] in ("clarification", "blocked") else ""
    d["motivo_bloqueio"] = ""
    if d.get("valido") and d["estado"] == "blocked":
        motivo = _texto((d.get("bloqueio") or {}).get("reason")).strip()
        d["motivo_bloqueio"] = motivo or "motivo não registrado"
    d["gates_lista"] = [
        {
            "gate": g,
            "nome": _texto((d["gates"].get(g) or {}).get("name")) if isinstance(d["gates"].get(g), dict) else "",
            "status": status_gate(d, g) or "—",
            "aprovador": _texto((d["gates"].get(g) or {}).get("approver")) if isinstance(d["gates"].get(g), dict) else "",
            "em": _texto((d["gates"].get(g) or {}).get("at")) if isinstance(d["gates"].get(g), dict) else "",
            "evidencia": _texto((d["gates"].get(g) or {}).get("evidence")) if isinstance(d["gates"].get(g), dict) else "",
            "obs": _texto((d["gates"].get(g) or {}).get("note")) if isinstance(d["gates"].get(g), dict) else "",
        }
        for g in GATES_ORDEM
    ]
    return d


def _sem_acento(texto):
    normal = unicodedata.normalize("NFD", str(texto).casefold())
    return "".join(c for c in normal if not unicodedata.combining(c))


def filtrar(demandas, termo):
    """Filtra por ID ou título (AC-8), ignorando caixa e acentos."""
    alvo = _sem_acento(termo).strip()
    if not alvo:
        return list(demandas)
    return [
        d
        for d in demandas
        if alvo in _sem_acento(d.get("nome", ""))
        or alvo in _sem_acento(d.get("titulo", ""))
        or alvo == str(d.get("numero") or "")
    ]


def kpis(demandas):
    """Os números do cabeçalho da tela (AC-6).

    `ativas` responde "o que está EM ANDAMENTO" e por isso exclui
    `done`, `cancelled` e leitura inválida — contar `done` errava por mais de
    100% o número mais visível da tela.
    `blocked` continua dentro: trabalho travado é trabalho em curso.

    A contagem POR COLUNA não sai daqui: quem a exibe é o cabeçalho de cada
    coluna do quadro, que já conta as demandas que está mostrando (e respeita
    a busca). Manter um segundo cálculo aqui era só dois jeitos de contar a
    mesma coisa, esperando divergir.
    """
    ativas = aguardando = invalidas = canceladas = concluidas = 0
    for d in demandas:
        if not d.get("valido"):
            invalidas += 1
            continue
        if d["estado"] == "cancelled":
            canceladas += 1
            continue
        if d["estado"] == "done":
            concluidas += 1
            continue
        ativas += 1
        if d.get("aguarda_owner"):
            aguardando += 1
    return {
        "total": len(demandas),
        "ativas": ativas,
        "concluidas": concluidas,
        "aguardando_owner": aguardando,
        "invalidas": invalidas,
        "canceladas": canceladas,
    }


def projetar(raiz=None, esquema=None):
    """Projeção completa do quadro a partir do disco. Sem cache, sem banco.

    Medido: ~0,5 s a frio para uma dezena de demandas em ~45 refs.
    Enquanto isso couber no tempo de um GET local, cache é otimização por
    antecipação — e cache é a porta de entrada da segunda fonte de verdade
    que a RN-1/RN-3 proíbem.

    `falhas` (e o `degradada` que dele decorre) é parte do resultado, não um
    detalhe: quadro incompleto tem que se anunciar como incompleto.
    """
    inicio = time.perf_counter()
    coleta = Coleta()
    raiz = raiz or raiz_repo(coleta=coleta)
    esquema = esquema or carregar_esquema()
    grupos = coletar(raiz, esquema, coleta)
    demandas = [montar_demanda(nome, copias, esquema) for nome, copias in grupos.items()]
    demandas.sort(key=lambda d: (d["numero"] is None, d["numero"] or 0, d["nome"]))
    return {
        "raiz": str(raiz),
        "demandas": demandas,
        "kpis": kpis(demandas),
        "fontes": sorted({c["fonte"] for copias in grupos.values() for c in copias}),
        "total_copias": sum(len(c) for c in grupos.values()),
        "falhas": coleta.falhas,
        "degradada": bool(coleta.falhas),
        "custo_ms": round((time.perf_counter() - inicio) * 1000, 1),
        "lido_em": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def quadro(projecao, esquema, termo=""):
    """Monta as colunas exibidas (AC-9: `cancelled` fora do quadro ativo)."""
    demandas = filtrar(projecao["demandas"], termo)
    ativas = [d for d in demandas if d.get("valido") and d.get("coluna")]
    colunas = [
        {"nome": nome, "demandas": [d for d in ativas if d["coluna"] == nome]}
        for nome, _ in esquema.colunas
    ]
    return {
        "colunas": colunas,
        "invalidas": [d for d in demandas if not d.get("valido")],
        # `cancelled` só aparece quando explicitamente buscado (AC-9/RN-4).
        "canceladas": [d for d in demandas if d.get("valido") and d["estado"] == "cancelled"] if termo else [],
        "exibidas": len(demandas),
        "termo": termo,
    }


def main(argv=None):
    """CLI de diagnóstico: imprime a projeção resolvida (usado nas evidências).

    Exit: 0 = leitura completa · 3 = leitura DEGRADADA (alguma fonte falhou).
    Sair 0 com o quadro incompleto seria transformar "não consegui ler" em
    "não há nada a fazer".
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    esquema = carregar_esquema()
    p = projetar(esquema=esquema)
    print("raiz:    %s" % p["raiz"])
    print("fontes:  %d (%d cópias de state.yaml)" % (len(p["fontes"]), p["total_copias"]))
    print("custo:   %.1f ms (leitura completa, sem cache)" % p["custo_ms"])
    print("demandas: %d | %s" % (p["kpis"]["total"], p["kpis"]))
    print("")
    print("%-12s %-16s %-20s %-9s %s" % ("DEMANDA", "ESTADO", "COLUNA", "CÓPIAS", "FONTE AUTORITATIVA"))
    for d in p["demandas"]:
        print(
            "%-12s %-16s %-20s %-9s %s%s"
            % (
                d["nome"],
                d["estado"] if d["valido"] else "(inválida)",
                d["coluna"] or "—",
                d["total_copias"],
                d["fonte"],
                "  ⚠ divergentes: %s" % ", ".join(d["estados_divergentes"]) if d["estados_divergentes"] else "",
            )
        )
    if "--fontes" in argv:
        print("\nfontes varridas:")
        for f in p["fontes"]:
            print("  %s" % f)
    if p["degradada"]:
        print("\nLEITURA DEGRADADA — %d falha(s) de fonte; o quadro acima pode estar INCOMPLETO:"
              % len(p["falhas"]))
        for f in p["falhas"]:
            print("  %s: %s%s" % (f["comando"], f["motivo"], " (x%d)" % f["vezes"] if f["vezes"] > 1 else ""))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
