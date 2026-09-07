#!/usr/bin/env python3
# =============================================================================
# banco.py — persistência local da telemetria.
# CANÁRIO-TRAVA-DEPLOY: FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH
#
# ÚNICO módulo do dashboard que importa `sqlite3`. É aqui que mora a
# LISTA BRANCA de campos persistíveis (RN-2) — em um lugar só, para ser
# auditável de uma olhada e travada por teste estático e pelo canário (AC-3).
# Conteúdo de mensagem NUNCA entra: o `Evento` que chega de `telemetria.py`
# não tem sequer onde guardá-lo.
#
# Duas tabelas e NENHUM agregado materializado. O total sai de `SUM`
# sobre linhas deduplicadas por `UPSERT ... MAX()`. Isso não é elegância: é o
# que torna a RN-9/AC-15 uma propriedade do esquema em vez de um algoritmo.
# Um acumulador (`agregado += novo − antigo`) infla em silêncio — e para
# sempre — quando um arquivo some por um tick (medido: 100 → 200). Aqui:
#   - reprocessar a mesma linha não infla nada  (MAX é idempotente)
#   - arquivo que some é MARCADO, não apagado    (o total não desconta)
#   - arquivo que volta é reprocessado do zero   (e converge para as mesmas linhas)
#
# Retenção (decisão do Owner): o total de tokens é **registro durável do que
# foi medido**. O Claude Code limpa transcripts antigos (~30 dias); se o
# desconto valesse, o custo de uma demanda encolheria sozinho com o tempo —
# número que muda sem nada ter acontecido. Retemos a linha e marcamos o
# arquivo (`removido_em`). A garantia anti-inflação NÃO depende do desconto:
# ela vem de não haver acumulador — o bug 100→200 nascia de recontagem sobre
# acumulador, não de retenção. O que degrada para "sem dados" é o CONTEÚDO,
# que nunca esteve aqui (RN-2) e só existe enquanto o JSONL existir.
#
# O banco é CACHE de fonte durável (os JSONL), nunca fonte. Por isso a
# migração é "apagar e reconstruir": custa ~1 s medido e não perde nada que
# exista em disco.
# =============================================================================
"""Persistência da telemetria em SQLite local: esquema, escrita e consultas."""

import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import telemetria  # noqa: E402

# Erro exposto para quem chama (app.py NÃO importa sqlite3): banco
# ausente, corrompido ou travado degrada a telemetria, nunca o Kanban.
ErroTelemetria = sqlite3.Error

VERSAO_ESQUEMA = 2  # 2: `arquivo.removido_em` (retenção em vez de desconto)
BANCO_PADRAO = Path(__file__).resolve().parent / "dados" / "telemetria.sqlite"

# ── LISTA BRANCA (RN-2) ──────────────────────────────────────────────────────
# Tudo que pode ser gravado: os cinco campos de telemetria da linha do
# transcript + os metadados operacionais avalizados pelo Owner no G1. Nenhum é
# conteúdo de mensagem. O teste estático confere que as colunas do DDL abaixo
# são exatamente estas — acrescentar coluna sem passar por aqui quebra a suíte.
CAMPOS_PERSISTIVEIS = frozenset({
    # da linha do transcript (telemetria.Evento)
    "request_id", "session_id", "git_branch", "demanda", "agente", "modelo",
    "provedor", "entrada", "saida", "cache_criacao", "cache_leitura", "ultimo_em",
    # do índice de leitura incremental (metadados do arquivo, não do conteúdo)
    "caminho", "origem", "inode", "tamanho", "deslocamento", "visto_em",
    "removido_em",
})

ESQUEMA = """
CREATE TABLE IF NOT EXISTS arquivo (
  caminho      TEXT PRIMARY KEY,
  provedor     TEXT NOT NULL,
  origem       TEXT NOT NULL,
  inode        INTEGER NOT NULL DEFAULT 0,
  tamanho      INTEGER NOT NULL DEFAULT 0,
  deslocamento INTEGER NOT NULL DEFAULT 0,
  visto_em     TEXT NOT NULL DEFAULT '',
  -- quando o transcript sai do disco. As linhas de `requisicao` ficam
  -- (o total não desconta); é só o CONTEÚDO que passa a não ter fonte.
  removido_em  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS requisicao (
  caminho       TEXT NOT NULL,
  request_id    TEXT NOT NULL,
  demanda       TEXT,
  git_branch    TEXT,
  session_id    TEXT,
  agente        TEXT,
  modelo        TEXT,
  provedor      TEXT NOT NULL,
  entrada       INTEGER NOT NULL DEFAULT 0,
  saida         INTEGER NOT NULL DEFAULT 0,
  cache_criacao INTEGER NOT NULL DEFAULT 0,
  cache_leitura INTEGER NOT NULL DEFAULT 0,
  ultimo_em     TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (caminho, request_id)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS ix_requisicao_demanda ON requisicao (demanda, ultimo_em);
"""

# `MAX` por campo dentro do mesmo requestId (RN-4/AC-4). Somar as linhas de um
# mesmo `requestId` inflaria o consumo — medido em transcripts reais: 1,77× no
# `output`, 3,06× no `input`, 2,63× no `cache_creation`.
# `ultimo_em` usa MAX lexicográfico: ISO-8601 com o mesmo fuso ordena como
# texto, e o vazio ('' = sem timestamp) perde de qualquer data — por isso a
# coluna é NOT NULL DEFAULT '' em vez de NULL (MAX com NULL devolve NULL).
GRAVAR = """
INSERT INTO requisicao
  (caminho, request_id, demanda, git_branch, session_id, agente, modelo,
   provedor, entrada, saida, cache_criacao, cache_leitura, ultimo_em)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (caminho, request_id) DO UPDATE SET
  entrada       = MAX(requisicao.entrada,       excluded.entrada),
  saida         = MAX(requisicao.saida,         excluded.saida),
  cache_criacao = MAX(requisicao.cache_criacao, excluded.cache_criacao),
  cache_leitura = MAX(requisicao.cache_leitura, excluded.cache_leitura),
  ultimo_em     = MAX(requisicao.ultimo_em,     excluded.ultimo_em),
  demanda       = COALESCE(excluded.demanda, requisicao.demanda),
  agente        = COALESCE(excluded.agente, requisicao.agente),
  modelo        = COALESCE(excluded.modelo, requisicao.modelo),
  git_branch    = COALESCE(excluded.git_branch, requisicao.git_branch),
  session_id    = COALESCE(excluded.session_id, requisicao.session_id)
"""


# ── Abertura e esquema ───────────────────────────────────────────────────────


def _apagar(caminho):
    """Remove o banco e seus arquivos auxiliares (WAL/SHM andam juntos)."""
    for sufixo in ("", "-wal", "-shm", "-journal"):
        try:
            Path(str(caminho) + sufixo).unlink()
        except OSError:
            pass


def abrir(caminho=None):
    """Abre (ou cria) o banco de telemetria e garante o esquema.

    Migração = **apagar e reconstruir**: `user_version` diferente do
    esperado joga o arquivo fora e refaz. É a migração mais barata possível e
    aqui é segura, porque nada aqui é fonte de verdade — a varredura completa
    reconstrói tudo dos JSONL em ~1 s medido.

    Banco corrompido levanta `ErroTelemetria` para quem chamou: a tela degrada
    para "telemetria indisponível" e o Kanban continua.
    """
    caminho = Path(caminho or BANCO_PADRAO)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(caminho))
    try:
        versao = con.execute("PRAGMA user_version").fetchone()[0]
        if versao and versao != VERSAO_ESQUEMA:
            con.close()
            _apagar(caminho)
            con = sqlite3.connect(str(caminho))
            versao = 0
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=3000")
        con.executescript(ESQUEMA)
        if versao != VERSAO_ESQUEMA:
            con.execute("PRAGMA user_version=%d" % VERSAO_ESQUEMA)
        con.commit()
    except Exception:
        # Banco corrompido levanta no meio da abertura. Sem isto, cada request
        # com o banco quebrado vazava um descritor — o dashboard degradaria e
        # ainda por cima acumularia conexões abertas.
        con.close()
        raise
    return con


def tabelas(con):
    """Tabelas que existem no banco, perguntadas AO BANCO.

    Antes isto era a tupla literal `("arquivo", "requisicao")` — o que fazia a
    "lista fechada" da RN-2 depender de alguém lembrar de atualizá-la. Uma
    tabela nova (`cache_de_saida(texto)`, digamos) passaria pela conferência
    sem ser vista. Perguntando ao `sqlite_master`, qualquer objeto novo entra
    na trava por construção, que é o que a RN-2 promete.
    """
    return [l[0] for l in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]


def colunas(con):
    """Colunas realmente existentes no banco — o teste estático compara com a
    lista branca. Coluna (ou tabela) nova fora da RN-2 quebra a suíte."""
    achadas = set()
    for tabela in tabelas(con):
        for linha in con.execute('PRAGMA table_info("%s")' % tabela.replace('"', '""')):
            achadas.add(linha[1])
    return achadas


# ── Varredura incremental: sob demanda, sem daemon ───────────────────────────


def marcar_removido(con, caminho, quando):
    """Marca um transcript que saiu do disco, RETENDO suas linhas.

    O que era `DELETE` até a decisão do Owner. O total não desconta: os
    tokens são registro durável do que foi medido, e o Claude Code limpa
    transcripts antigos sozinho — descontar faria o custo de uma demanda
    encolher com o tempo, sem nada ter acontecido.

    A linha do arquivo fica no índice justamente para que o reaparecimento
    seja detectável (e o offset, zerado).
    """
    con.execute("UPDATE arquivo SET removido_em = ? WHERE caminho = ? AND removido_em = ''",
                (quando, str(caminho)))


def removidos(con):
    """Transcripts marcados como fora do disco — o conteúdo deles é "sem dados"."""
    return {l[0] for l in con.execute("SELECT caminho FROM arquivo WHERE removido_em <> ''")}


def sincronizar(con, raiz_repo, demandas_conhecidas, raiz_projetos=None):
    """Põe o banco em dia com os transcripts em disco. Devolve o resumo.

    Roda no início de cada request. Custo medido: 0,87 ms sem novidade,
    19,6 ms com 4 KB novos por arquivo, ~1 s na primeira varredura (banco
    vazio) — contra 660–740 ms que a projeção do Kanban já gasta no mesmo
    request. Gatilho para promover a thread: passar de ~150 ms em regime.

    O resumo não é enfeite: o canário (AC-3) usa `eventos` para provar que a
    fixture foi de fato processada — sem essa prova, "zero ocorrências da
    isca" é inconclusivo, não "passou".
    """
    inicio = time.perf_counter()
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    achados = telemetria.transcripts(raiz_repo, raiz_projetos)
    conhecidos = {c[0]: c for c in con.execute(
        "SELECT caminho, inode, tamanho, deslocamento, removido_em FROM arquivo")}

    vistos, eventos_novos, voltaram = set(), 0, 0
    for caminho, origem in achados:
        chave = str(caminho)
        try:
            st = caminho.stat()
        except OSError:
            # Sumiu entre o glob e o stat. NÃO entra em `vistos`: se entrasse,
            # escaparia da marcação de removido e ainda inflaria a contagem de
            # arquivos do rodapé por uma rodada.
            continue
        vistos.add(chave)
        anterior = conhecidos.get(chave)
        deslocamento = 0
        if anterior is not None:
            _c, inode_antigo, _t, deslocamento_antigo, removido_antes = anterior
            if removido_antes:
                # Reapareceu: limpa a marcação e relê do offset 0. Não
                # apaga nada — o UPSERT MAX é idempotente, então reprocessar
                # converge para as mesmas linhas em vez de duplicá-las.
                con.execute("UPDATE arquivo SET removido_em = '' WHERE caminho = ?", (chave,))
                voltaram += 1
            elif inode_antigo and inode_antigo != st.st_ino:
                deslocamento = 0  # mesmo nome, arquivo outro: relê inteiro
            else:
                deslocamento = deslocamento_antigo

        linhas, novo_deslocamento = telemetria.ler_incremental(caminho, deslocamento)
        for evento in telemetria.eventos_de(linhas, demandas_conhecidas):
            con.execute(GRAVAR, (
                chave, evento.request_id, evento.demanda, evento.git_branch,
                evento.session_id, evento.agente, evento.modelo, evento.provedor,
                evento.entrada, evento.saida, evento.cache_criacao,
                evento.cache_leitura, evento.em or "",
            ))
            eventos_novos += 1
        con.execute(
            "INSERT INTO arquivo (caminho, provedor, origem, inode, tamanho, deslocamento, visto_em)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (caminho) DO UPDATE SET tamanho=excluded.tamanho,"
            " deslocamento=excluded.deslocamento, inode=excluded.inode, visto_em=excluded.visto_em",
            (chave, telemetria.PROVEDOR_PADRAO, origem, st.st_ino, st.st_size,
             novo_deslocamento, agora))

    # O que sumiu é marcado, não apagado — o total não desconta.
    sumiram = [c for c, dados in conhecidos.items() if c not in vistos and not dados[4]]
    for chave in sumiram:
        marcar_removido(con, chave, agora)

    reatribuidas = reatribuir_orfas(con, demandas_conhecidas)
    con.commit()
    return {
        "arquivos": len(vistos),
        "eventos": eventos_novos,
        "removidos": len(sumiram),
        "voltaram": voltaram,
        "reatribuidas": reatribuidas,
        "ms": round((time.perf_counter() - inicio) * 1000, 1),
    }


def reatribuir_orfas(con, demandas_conhecidas):
    """Dá dono às linhas que ficaram órfãs por a demanda não existir AINDA.

    O buraco que isto fecha: `demanda_da_branch` exige que a demanda exista na
    projeção do Kanban. Se a varredura acontece antes disso — demanda
    recém-criada, ou um `state.yaml` ilegível no instante da leitura, que é
    modo de falha **conhecido** da fábrica (escrita não atômica) —, a linha
    entra com `demanda = NULL`, o offset avança e ela nunca mais é relida. O
    consumo ficaria para sempre no KPI "fora de demanda" e o card daquela
    demanda subcontaria tokens **em silêncio**.

    Sem isto, a promessa do AC-15 valeria só para o mesmo estado do disco E o
    mesmo conjunto de demandas conhecidas: um `rm -rf dados/` seguido de
    reconstrução podia devolver número MAIOR que o incremental. Com a
    reatribuição, incremental e reconstrução do zero convergem — que é o que a
    regra sempre quis dizer.

    Barato: uma consulta pelas branches órfãs DISTINTAS (não por linha) e um
    `UPDATE` só para as que passaram a mapear.
    """
    orfas = [l[0] for l in con.execute(
        "SELECT DISTINCT git_branch FROM requisicao"
        " WHERE demanda IS NULL AND git_branch IS NOT NULL AND git_branch <> ''")]
    total = 0
    for branch in orfas:
        nome = telemetria.demanda_da_branch(branch, demandas_conhecidas)
        if not nome:
            continue  # segue sem demanda: é consumo fora de demanda mesmo
        cursor = con.execute(
            "UPDATE requisicao SET demanda = ? WHERE demanda IS NULL AND git_branch = ?",
            (nome, branch))
        total += cursor.rowcount or 0
    return total


# ── Consultas (RN-10: os quatro campos separados, nunca um "total") ──────────


def tokens_por_demanda(con):
    """{demanda: {saida, entrada, cache_criacao, cache_leitura, requisicoes}}.

    `saida` é a métrica principal (RN-10). Os quatro campos são devolvidos
    separados de propósito: somá-los num número só não tem significado de
    negócio — `cache_read` tem ordem de grandeza muito maior e custo por token
    muito menor — e ninguém converte nada em R$.
    """
    consulta = (
        "SELECT demanda, SUM(saida), SUM(entrada), SUM(cache_criacao), SUM(cache_leitura),"
        " COUNT(*), MAX(ultimo_em) FROM requisicao WHERE demanda IS NOT NULL GROUP BY demanda")
    return {
        linha[0]: {
            "saida": linha[1] or 0, "entrada": linha[2] or 0,
            "cache_criacao": linha[3] or 0, "cache_leitura": linha[4] or 0,
            "requisicoes": linha[5] or 0, "ultimo_em": linha[6] or "",
        }
        for linha in con.execute(consulta)
    }


def fora_de_demanda(con):
    """KPI do consumo sem demanda: observado, nunca rateado nem escondido.

    São as linhas de `develop`, `release/…`, branches de manutenção — uma
    fatia relevante dos requests. Distribuí-las entre as demandas seria número
    inferido; omiti-las seria buraco silencioso.
    """
    linha = con.execute(
        "SELECT SUM(saida), COUNT(*) FROM requisicao WHERE demanda IS NULL").fetchone()
    return {"saida": (linha[0] or 0), "requisicoes": (linha[1] or 0)}


def agentes_da_demanda(con, demanda):
    """[(agente, ultimo_em), ...] do mais recente para o mais antigo."""
    return [(l[0] or telemetria.AGENTE_SESSAO_PRINCIPAL, l[1] or "") for l in con.execute(
        "SELECT agente, MAX(ultimo_em) FROM requisicao WHERE demanda = ?"
        " GROUP BY agente ORDER BY 2 DESC", (demanda,))]


def modelo_da_demanda(con, demanda):
    """Modelo da execução mais recente, ou None ⇒ "sem dados" (AC-13)."""
    linha = con.execute(
        "SELECT modelo FROM requisicao WHERE demanda = ? AND modelo IS NOT NULL"
        " ORDER BY ultimo_em DESC LIMIT 1", (demanda,)).fetchone()
    return linha[0] if linha else None


def transcripts_da_demanda(con, demanda):
    """Transcripts que têm consumo desta demanda, do mais recente ao mais antigo.

    É o **ponteiro** que substitui guardar conteúdo: o card e o detalhe
    releem daqui, do JSONL em disco. Se o arquivo tiver sido removido, a
    leitura devolve vazio e a tela mostra "sem dados" — enquanto os tokens,
    esses sim persistidos, continuam aparecendo (AC-11).
    """
    return [l[0] for l in con.execute(
        "SELECT caminho, MAX(ultimo_em) FROM requisicao WHERE demanda = ?"
        " GROUP BY caminho ORDER BY 2 DESC", (demanda,))]


def resumo(con):
    """Números do próprio banco, para o rodapé e a CLI de diagnóstico."""
    arquivos = con.execute("SELECT COUNT(*) FROM arquivo").fetchone()[0]
    requisicoes = con.execute("SELECT COUNT(*) FROM requisicao").fetchone()[0]
    visto = con.execute("SELECT MAX(visto_em) FROM arquivo").fetchone()[0] or ""
    fora = con.execute("SELECT COUNT(*) FROM arquivo WHERE removido_em <> ''").fetchone()[0]
    return {"arquivos": arquivos, "requisicoes": requisicoes, "visto_em": visto,
            "removidos": fora}


def main(argv=None):
    """CLI de diagnóstico: varre e imprime o consumo por demanda (evidências).

    Exit: 0 = ok. Sem `--banco`, usa um banco temporário para não tocar no do
    dashboard.
    """
    import argparse
    import leitor

    p = argparse.ArgumentParser(description="Varredura de telemetria (diagnóstico).")
    p.add_argument("--banco", default=None, help="caminho do SQLite (padrão: temporário)")
    args = p.parse_args(argv)

    projecao = leitor.projetar()
    demandas = {d["nome"] for d in projecao["demandas"]}
    caminho = args.banco or (Path(__import__("tempfile").mkdtemp()) / "diagnostico.sqlite")
    con = abrir(caminho)
    resultado = sincronizar(con, projecao["raiz"], demandas)
    print("banco:     %s" % caminho)
    print("varredura: %(arquivos)d arquivo(s), %(eventos)d evento(s) novo(s), "
          "%(removidos)d removido(s), %(ms).1f ms" % resultado)
    print("acervo:    %(arquivos)d arquivo(s) indexado(s), %(requisicoes)d requisição(ões), "
          "%(removidos)d fora do disco (retido)" % resumo(con))
    print("")
    print("%-14s %12s %12s %10s  %s" % ("DEMANDA", "OUTPUT", "CACHE_READ", "REQS", "ÚLTIMA ATIVIDADE"))
    for nome, t in sorted(tokens_por_demanda(con).items()):
        print("%-14s %12d %12d %10d  %s" % (nome, t["saida"], t["cache_leitura"],
                                            t["requisicoes"], t["ultimo_em"] or "—"))
    fora = fora_de_demanda(con)
    print("\nfora de demanda (nunca rateado): %d output em %d requisição(ões)"
          % (fora["saida"], fora["requisicoes"]))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
