#!/usr/bin/env python3
# =============================================================================
# monitor.py — monitor CLI da fábrica em tempo real (zero LLM, somente leitura)
# ARQUITETURA §4 (o disco é a fonte de verdade), §6 (estados/gates),
# §18 (gates), §20 (batching da fila do Owner).
#
# Lê apenas arquivos locais das demandas (state.yaml, log.md) — sem rede, sem
# `gh`, sem escrever nada em disco. Redesenha só quando algum arquivo
# observado muda (assinatura mtime_ns + size); Ctrl+C encerra limpo.
#
# A regra da "fila do Owner" é por ESTADO e é a mesma de
# `.claude/commands/faber-status.md` (linhas 15-17): ready-for-dev→G1,
# minha-avaliacao→G6, pr-open→G8, sempre com o gate correspondente
# `pendente`. Se a regra mudar lá, replicar aqui (decisions.md D-1).
#
# Uso: monitor.py [--interval SEGUNDOS] [--once] [--tasks-dir PATH]
#   --interval N       intervalo do polling em segundos (default 2, mínimo 0.5)
#   --once             imprime um snapshot único e sai (sem loop, sem ANSI)
#   --tasks-dir P   pasta que contém as TASK-*/ (default: ../tasks
#                      relativo a este script — num worktree, monitora as
#                      demandas daquele worktree)
#
# Tokens: não disponível nesta versão (não há telemetria de tokens persistida
# em disco — inferir seria evidência inventada).
#
# Exit: 0 = ok (inclusive Ctrl+C) · 1 = erro de uso/ambiente (PyYAML ausente,
#       pasta de demandas inexistente, --interval fora do mínimo).
# =============================================================================
"""Monitor CLI da fábrica: visão viva das demandas, lida do disco."""

import argparse
import math
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # read-only: não deixa __pycache__ no repo

try:
    import yaml
except ImportError:  # pragma: no cover - depende do ambiente
    yaml = None

# ── Constantes ───────────────────────────────────────────────────────────────

GATES_ORDEM = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"]

# Fila do Owner por ESTADO (fonte: .claude/commands/faber-status.md)
FILA_OWNER = {
    "ready-for-dev": "G1",
    "minha-avaliacao": "G6",
    "pr-open": "G8",
}

ERRO_SEM_STATE = "sem state.yaml"
ERRO_ILEGIVEL = "ilegível — relendo"

INTERVALO_PADRAO = 2.0
INTERVALO_MINIMO = 0.5
LARGURA_PADRAO = 100
LOG_BYTES_LIDOS = 8192  # basta para a última linha; evita ler log.md gigante

_RE_TAREFA = re.compile(r"^TASK-(\d+)$")
# Caracteres de controle (inclui ESC \x1b e CR \x0d) — \n e \t ficam de fora
# porque são trocados por espaço antes. Ver review G4, achado S-1.
_RE_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


# ── Funções puras (sem I/O de terminal) ──────────────────────────────────────


def numero_tarefa(nome):
    """Devolve o número da TASK (int) ou None se o nome não for numérico."""
    m = _RE_TAREFA.match(str(nome))
    return int(m.group(1)) if m else None


def _chave_ordem(nome):
    """Ordena por NÚMERO (TASK-91 antes de TASK-100), não lexicográfico."""
    n = numero_tarefa(nome)
    return (n is None, n if n is not None else 0, str(nome))


def descobrir_demandas(tasks_dir):
    """Lista as pastas TASK-* de `tasks_dir`, ordenadas por número."""
    base = Path(tasks_dir)
    try:
        pastas = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("TASK-")]
    except OSError:
        return []
    return sorted(pastas, key=lambda p: _chave_ordem(p.name))


def _ultima_linha_log(caminho):
    """Última linha não vazia do log.md, sem o '- ' inicial. None se não houver."""
    try:
        tamanho = caminho.stat().st_size
        with open(caminho, "rb") as f:
            if tamanho > LOG_BYTES_LIDOS:
                f.seek(tamanho - LOG_BYTES_LIDOS)
            bruto = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for linha in reversed(bruto.splitlines()):
        linha = linha.strip()
        if linha:
            return linha[2:].strip() if linha.startswith("- ") else linha
    return None


def _ultimo(lista):
    """Último item de uma lista de dicts (tolerante a shape inesperado)."""
    if isinstance(lista, list):
        for item in reversed(lista):
            if isinstance(item, dict):
                return item
    return None


def ler_demanda(pasta):
    """Lê uma pasta TASK-* e devolve o dict da demanda.

    NUNCA levanta exceção: state.yaml ausente ou sendo reescrito no instante
    da leitura (corrida com transition.sh/gate-set.sh) vira o campo `erro`,
    e a demanda aparece marcada na tela sem derrubar o loop.
    """
    pasta = Path(pasta)
    d = {
        "nome": pasta.name,
        "numero": numero_tarefa(pasta.name),
        "pasta": str(pasta),
        "erro": None,
        "demanda": pasta.name,
        "issue": None,
        "titulo": "",
        "tipo": "",
        "estado": "",
        "gates": {},
        "bloqueio": None,
        "ultima_transicao": None,
        "ultima_invocacao": None,
        "ultima_linha_log": None,
    }

    state = pasta / "state.yaml"
    if not state.is_file():
        d["erro"] = ERRO_SEM_STATE
        return d

    try:
        with open(state, encoding="utf-8") as f:
            dados = yaml.safe_load(f)
        if not isinstance(dados, dict):
            raise ValueError("state.yaml não é um mapa YAML")
    except Exception:  # parse parcial, YAML inválido, encoding, permissão...
        d["erro"] = ERRO_ILEGIVEL
        return d

    d["demanda"] = str(dados.get("demanda") or pasta.name)
    d["issue"] = dados.get("issue")
    d["titulo"] = str(dados.get("titulo") or "")
    d["tipo"] = str(dados.get("tipo") or "")
    d["estado"] = str(dados.get("estado") or "")
    gates = dados.get("gates")
    d["gates"] = gates if isinstance(gates, dict) else {}
    bloqueio = dados.get("bloqueio")
    d["bloqueio"] = bloqueio if isinstance(bloqueio, dict) else None
    d["ultima_transicao"] = _ultimo(dados.get("historico"))
    d["ultima_invocacao"] = _ultimo(dados.get("invocacoes"))
    d["ultima_linha_log"] = _ultima_linha_log(pasta / "log.md")
    return d


def status_gate(demanda, gate):
    """Status do gate (ex.: 'pendente') ou None se ausente/malformado."""
    info = (demanda.get("gates") or {}).get(gate)
    return str(info.get("status")) if isinstance(info, dict) and info.get("status") else None


def gate_corrente(demanda):
    """Primeiro gate (G1..G9) ainda `pendente` — o que a demanda persegue."""
    if demanda.get("erro"):
        return None
    for gate in GATES_ORDEM:
        if status_gate(demanda, gate) == "pendente":
            return gate
    return None


def aguarda_owner(demanda):
    """Gate humano que a demanda aguarda (G1/G6/G8) ou None.

    Regra por ESTADO (D-1), igual à do /faber-status: só entra na fila quem está
    em ready-for-dev / minha-avaliacao / pr-open COM o gate correspondente
    `pendente`. blocked/cancelled nunca entram (têm bloco próprio).
    """
    if demanda.get("erro"):
        return None
    gate = FILA_OWNER.get(demanda.get("estado"))
    if not gate:
        return None
    return gate if status_gate(demanda, gate) == "pendente" else None


def _corta(texto, largura):
    """Trunca preservando a largura do terminal (fallback 80 colunas).

    Também remove caracteres de controle: `titulo` vem do título da issue no
    GitHub (não é 100% conteúdo local) e um `\\x1b`/`\\r` cru moveria o cursor,
    apagaria linhas ou forjaria a linha da fila do Owner (review G4, S-1).
    """
    texto = _RE_CONTROLE.sub("", str(texto).replace("\n", " ").replace("\t", " "))
    if largura and len(texto) > largura:
        return texto[: max(1, largura - 1)] + "…"
    return texto


def _ultima_acao(demanda):
    """Última ação registrada: log.md > histórico > invocações > sem registro."""
    partes = []
    if demanda.get("ultima_linha_log"):
        partes.append(demanda["ultima_linha_log"])
    else:
        t = demanda.get("ultima_transicao")
        if t:
            partes.append(
                "%s %s -> %s (por %s)"
                % (t.get("em", "?"), t.get("de", "?"), t.get("para", "?"), t.get("por", "?"))
            )
    inv = demanda.get("ultima_invocacao")
    if inv and inv.get("agente"):
        partes.append("último agente: %s" % inv.get("agente"))
    return " · ".join(partes) if partes else "sem registro"


def renderizar(demandas, largura=LARGURA_PADRAO, tty=False, intervalo=None, agora=None):
    """Monta a tela inteira como string (testável, sem imprimir nada).

    `tty=False` (padrão) garante saída 100% ASCII-safe e sem ANSI, para não
    poluir logs de evidência e saídas redirecionadas.
    """
    largura = int(largura or LARGURA_PADRAO)
    momento = agora or datetime.now()
    linhas = []

    regua = "=" * min(largura, 78)
    linhas.append(regua)
    cabecalho = "FÁBRICA · %d demanda(s) · %s" % (
        len(demandas),
        momento.strftime("%Y-%m-%d %H:%M:%S"),
    )
    if intervalo:
        cabecalho += " · polling %gs (Ctrl+C encerra)" % intervalo
    linhas.append(_corta(cabecalho, largura))
    linhas.append(regua)
    linhas.append("")

    # ── Fila do Owner ──────────────────────────────────────────────────────
    fila = [(d, aguarda_owner(d)) for d in demandas]
    fila = [(d, g) for d, g in fila if g]
    marcador = "🔔 AGUARDANDO OWNER" if tty else ">> AGUARDANDO OWNER"
    if fila:
        linhas.append("%s (%d)" % (marcador, len(fila)))
        for d, gate in fila:
            linhas.append(
                _corta(
                    "   %s [%s] aguarda %s · issue #%s · %s"
                    % (d["demanda"], d["estado"], gate, d.get("issue"), d.get("titulo") or "-"),
                    largura,
                )
            )
    else:
        linhas.append("%s: nenhuma demanda aguardando você" % marcador)
    linhas.append("")

    # ── Bloqueios (fora da fila do Owner — sinal diferente) ────────────────
    bloqueadas = [d for d in demandas if d.get("bloqueio") or d.get("estado") == "blocked"]
    if bloqueadas:
        linhas.append("!! BLOQUEADAS (%d)" % len(bloqueadas))
        for d in bloqueadas:
            b = d.get("bloqueio") or {}
            linhas.append(
                _corta(
                    "   %s · motivo: %s · desde %s · volta para: %s"
                    % (
                        d["demanda"],
                        b.get("motivo") or "(não registrado)",
                        b.get("desde") or "?",
                        b.get("estado_origem") or "?",
                    ),
                    largura,
                )
            )
        linhas.append("")

    # ── Todas as demandas ────────────────────────────────────────────────────
    if not demandas:
        linhas.append("TASKS: nenhuma demanda ativa")
    else:
        linhas.append("TASKS (%d)" % len(demandas))
        for d in demandas:
            rotulo = d["erro"] or d["estado"] or "?"
            gate = gate_corrente(d)
            linhas.append(
                _corta(
                    "   %-11s %-22s %-8s %-15s %s"
                    % (
                        d["demanda"],
                        "[%s]" % rotulo,
                        "gate %s" % gate if gate else "gate -",
                        d.get("tipo") or "-",
                        d.get("titulo") or "-",
                    ),
                    largura,
                )
            )
            if not d["erro"]:
                linhas.append(_corta("        última ação: %s" % _ultima_acao(d), largura))
    linhas.append("")
    linhas.append(
        _corta(
            "tokens: não disponível nesta versão · fonte: state.yaml + log.md (somente leitura)",
            largura,
        )
    )
    return "\n".join(linhas)


# ── I/O: descoberta de mudanças, loop e CLI ──────────────────────────────────


def assinatura(tasks_dir):
    """Assinatura barata do que é observado: (pastas, mtime_ns, size).

    mtime_ns + size cobre FS com mtime de 1s de granularidade; incluir os
    NOMES das pastas faz uma demanda nova aparecer sem esperar outra escrita.
    """
    itens = []
    for pasta in descobrir_demandas(tasks_dir):
        itens.append(pasta.name)
        for arquivo in ("state.yaml", "log.md"):
            try:
                st = (pasta / arquivo).stat()
                itens.append((pasta.name, arquivo, st.st_mtime_ns, st.st_size))
            except OSError:
                itens.append((pasta.name, arquivo, None, None))
    return tuple(itens)


def snapshot(tasks_dir, tty=False, intervalo=None):
    """Lê o disco e devolve a tela pronta (string)."""
    demandas = [ler_demanda(p) for p in descobrir_demandas(tasks_dir)]
    largura = shutil.get_terminal_size(fallback=(80, 24)).columns if tty else LARGURA_PADRAO
    return renderizar(demandas, largura=largura, tty=tty, intervalo=intervalo)


def _imprimir(texto, limpar_tela):
    if limpar_tela:
        sys.stdout.write("\033[H\033[2J")  # ANSI só em TTY
    print(texto, flush=True)


def _loop(tasks_dir, intervalo, tty):
    """Redesenha a cada mudança; nenhuma falha de um tick derruba o loop.

    `ler_demanda` já trata o state.yaml ilegível (AC-6), mas qualquer outra
    exceção do tick (I/O transitório, UnicodeEncodeError ao imprimir num
    terminal não-UTF-8) vira uma linha de erro e segue (spec §3.7, review R-1).
    """
    anterior = None
    while True:
        try:
            atual = assinatura(tasks_dir)
            if atual != anterior:
                _imprimir(snapshot(tasks_dir, tty=tty, intervalo=intervalo), limpar_tela=tty)
                anterior = atual
        except BrokenPipeError:  # stdout fechado: quem trata é o main()
            raise
        except Exception as erro:  # pragma: no cover - rede de segurança
            print("ERRO no tick: %s: %s (seguindo)" % (type(erro).__name__, erro),
                  file=sys.stderr, flush=True)
            anterior = None  # força o redesenho quando a causa passar
        time.sleep(intervalo)


def _parser():
    p = argparse.ArgumentParser(
        prog="monitor.py",
        description="Monitor da fábrica em tempo real: demandas, estados, gates e "
        "fila de gates humanos (G1/G6/G8), lidos do disco.",
        epilog="Somente leitura (nenhuma escrita, nenhuma rede). "
        "Tokens: não disponível nesta versão — não há telemetria de tokens em disco.",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=INTERVALO_PADRAO,
        metavar="SEGUNDOS",
        help="intervalo do polling (default: %(default)s; mínimo " + str(INTERVALO_MINIMO) + ")",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="imprime um snapshot único e sai (uso não-interativo/evidência)",
    )
    p.add_argument(
        "--tasks-dir",
        metavar="PATH",
        default=None,
        help="pasta com as TASK-*/ (default: ../tasks relativo ao script; "
        "num worktree, monitora as demandas daquele worktree)",
    )
    return p


def main(argv=None):
    args = _parser().parse_args(argv)

    if yaml is None:
        print(
            "ERRO: PyYAML não encontrado. Instale com: pip3 install pyyaml",
            file=sys.stderr,
        )
        return 1

    # `not (x >= min)` (em vez de `x < min`) rejeita nan, cuja comparação é
    # sempre falsa; isfinite barra inf, que congelaria o loop (review R-2).
    if not math.isfinite(args.interval) or not (args.interval >= INTERVALO_MINIMO):
        print(
            "ERRO: --interval deve ser um número finito >= %s s "
            "(evita busy-loop de CPU; 'nan'/'inf' são recusados)" % INTERVALO_MINIMO,
            file=sys.stderr,
        )
        return 1

    tasks_dir = Path(args.tasks_dir) if args.tasks_dir else Path(__file__).resolve().parent.parent / "tasks"
    if not tasks_dir.is_dir():
        print("ERRO: pasta de demandas não encontrada: %s" % tasks_dir, file=sys.stderr)
        return 1

    tty = bool(getattr(sys.stdout, "isatty", lambda: False)()) and not args.once

    try:
        if args.once:
            _imprimir(snapshot(tasks_dir, tty=False), limpar_tela=False)
        else:
            _loop(tasks_dir, args.interval, tty)
    except KeyboardInterrupt:  # Ctrl+C encerra limpo, sem traceback
        if tty:
            print()
        return 0
    except BrokenPipeError:  # ex.: monitor.py --once | head
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
