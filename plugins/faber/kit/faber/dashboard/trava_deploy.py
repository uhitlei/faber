#!/usr/bin/env python3
# =============================================================================
# trava_deploy.py — trava verificada contra o vazamento do dashboard interno
# para o site público.
#
# Por que existe: o repositório do produto pode PUBLICAR um artefato de build
# (ex.: `dist/` de um app web). A decisão de rodar o dashboard só em
# 127.0.0.1 sem autenticação só vale o que valer a garantia de que
# faber/dashboard/ jamais entra num artefato de build. Promessa não é
# controle; isto é uma checagem que FALHA quando deve.
#
# Duas metades:
#   1. artefato — nada em dist/ pode conter o canário nem vir de faber/;
#   2. fonte    — nada em src/, public/ ou index.html pode referenciar
#                 faber/dashboard (é assim que o vazamento começaria).
#
# Limite declarado: no artefato, o conteúdo de binário conhecido
# (EXTENSOES_BINARIAS) e de arquivo acima de LIMITE_BYTES não é lido — o
# main() IMPRIME quais foram pulados. Para esses, sobra a regra de caminho.
#
# Uso: python3 faber/dashboard/trava_deploy.py [--dist dist] [--raiz .]
# Exit: 0 = trava ok · 2 = VIOLAÇÃO (o dashboard vazou) ·
#       1 = não executado (dist ausente — declarado, jamais inferido)
# =============================================================================
"""Trava verificada: o dashboard da fábrica não pode entrar em artefato de build."""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

# Marcador plantado nos arquivos-fonte do dashboard. Procurar por "dashboard"
# geraria falso positivo (o produto pode ter telas com esse nome); o canário não.
CANARIO = "FABER-DASHBOARD-INTERNAL-DO-NOT-PUBLISH"
REFERENCIA_PROIBIDA = "faber/dashboard"

# Banco local de telemetria. Ele não carrega o canário —
# guarda números e caminhos de transcript —, então nenhuma das duas regras
# acima o pegaria. E é o arquivo com o pior conteúdo possível para vazar num
# site público: `sessionId`, branches e o mapa de quem trabalhou em quê.
ARQUIVOS_DE_DADOS = ("telemetria.sqlite", "telemetria.sqlite-wal",
                     "telemetria.sqlite-shm", "telemetria.sqlite-journal")

# Onde o build do produto nasce (ex.: Vite compila src/ e copia public/).
# Ajuste à stack do produto se o layout for outro.
FONTES_DO_BUILD = ("src", "public", "index.html", "vite.config.ts")

# A regra é INVERSA de propósito: uma lista de extensões de TEXTO — lendo só
# elas — deixaria passar um dist/assets/leitor.py COM o canário dentro, e o
# mesmo valeria para .tsx, .yaml e .md. O vazamento real (arquivo ou import
# inteiro) não pede licença pela extensão. Por isso TUDO é lido, menos binário
# conhecido e arquivo maior que o limite.
EXTENSOES_BINARIAS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".mp4", ".webm", ".ogg", ".wav", ".pdf",
    ".zip", ".gz", ".br", ".tar", ".wasm",
}
LIMITE_BYTES = 8 * 1024 * 1024  # acima disso não é lido: limite DECLARADO, ver main()


def _inspecionavel(caminho):
    return caminho.suffix.lower() not in EXTENSOES_BINARIAS and caminho.stat().st_size <= LIMITE_BYTES


def verificar_artefato(dist, ignorados=None):
    """Violações encontradas dentro do artefato de build.

    `ignorados` (opcional) recebe o que NÃO foi lido — binário conhecido ou
    acima do limite. Trava que pula arquivo em silêncio é trava que mente:
    o main() imprime essa lista junto do resultado.
    """
    dist = Path(dist)
    violacoes = []
    for arquivo in sorted(p for p in dist.rglob("*") if p.is_file()):
        relativo = arquivo.relative_to(dist)
        if "faber" in relativo.parts:
            violacoes.append("arquivo de faber/ dentro do artefato: %s" % relativo)
        if arquivo.name in ARQUIVOS_DE_DADOS:
            violacoes.append("banco de telemetria do dashboard dentro do artefato: %s" % relativo)
        if not _inspecionavel(arquivo):
            if ignorados is not None:
                ignorados.append(str(relativo))
            continue
        conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
        if CANARIO in conteudo:
            violacoes.append("canário do dashboard encontrado em %s" % relativo)
        elif REFERENCIA_PROIBIDA in conteudo:
            violacoes.append("referência a %s encontrada em %s" % (REFERENCIA_PROIBIDA, relativo))
    return violacoes


def verificar_fontes(raiz):
    """Violações no que ALIMENTA o build (a origem de um vazamento futuro)."""
    raiz = Path(raiz)
    violacoes = []
    for nome in FONTES_DO_BUILD:
        alvo = raiz / nome
        if not alvo.exists():
            continue
        arquivos = [alvo] if alvo.is_file() else [p for p in alvo.rglob("*") if p.is_file()]
        for arquivo in sorted(arquivos):
            try:
                if arquivo.stat().st_size > LIMITE_BYTES:
                    continue
                conteudo = arquivo.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if REFERENCIA_PROIBIDA in conteudo or CANARIO in conteudo:
                violacoes.append("%s referencia o dashboard interno" % arquivo.relative_to(raiz))
    return violacoes


def main(argv=None):
    p = argparse.ArgumentParser(description="Trava de deploy do dashboard da fábrica.")
    p.add_argument("--raiz", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--dist", default=None, help="artefato de build (padrão: <raiz>/dist)")
    args = p.parse_args(argv)

    raiz = Path(args.raiz)
    dist = Path(args.dist) if args.dist else raiz / "dist"

    violacoes = verificar_fontes(raiz)
    print("trava de deploy — dashboard interno da fábrica")
    print("  raiz:  %s" % raiz)
    print("  dist:  %s" % dist)

    if not dist.is_dir():
        for v in violacoes:
            print("  VIOLAÇÃO (fonte): %s" % v)
        print("  NÃO EXECUTADO: %s não existe — rode o build do produto antes." % dist)
        return 2 if violacoes else 1

    arquivos = sum(1 for x in dist.rglob("*") if x.is_file())
    ignorados = []
    violacoes += verificar_artefato(dist, ignorados)
    print("  arquivos no artefato: %d (conteúdo lido: %d)" % (arquivos, arquivos - len(ignorados)))
    if ignorados:
        # Limite declarado, jamais inferido: binário conhecido e arquivo acima
        # de LIMITE_BYTES não têm o conteúdo lido — a regra de caminho
        # ("faber" no caminho) continua valendo para eles.
        print("  NÃO INSPECIONADOS por conteúdo (binário/limite de %d bytes): %d"
              % (LIMITE_BYTES, len(ignorados)))
        for nome in ignorados[:5]:
            print("    - %s" % nome)
        if len(ignorados) > 5:
            print("    … e mais %d" % (len(ignorados) - 5))
    if violacoes:
        for v in violacoes:
            print("  VIOLAÇÃO: %s" % v)
        print("FALHOU: o dashboard interno vazou para o artefato de build.")
        return 2
    print("OK: nenhum vestígio de faber/dashboard no artefato nem nas fontes do build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
