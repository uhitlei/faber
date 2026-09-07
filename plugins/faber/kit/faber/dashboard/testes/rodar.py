#!/usr/bin/env python3
# =============================================================================
# rodar.py — runner dos testes do dashboard (unittest da stdlib, sem pytest —
# mesmo precedente do monitor.py da fábrica).
#
# Uso: python3 faber/dashboard/testes/rodar.py [-v] [--faber-real]
#      (de dentro do venv — veja faber/dashboard/README.md)
# Exit: 0 = tudo passou · 1 = falha ou dependência ausente.
#
# Dependência ausente NÃO vira teste pulado silencioso: a suíte falha alto,
# porque "verde por não ter rodado" é exatamente a evidência falsa que a
# fábrica proíbe.
#
# A suíte padrão (`teste_*.py`) é PORTÁTIL: passa em qualquer clone. O que
# depende do estado desta máquina está em `faber_real.py`, fora do discover,
# e só roda com --faber-real.
# =============================================================================
"""Roda todos os testes do dashboard da fábrica."""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
sys.path.insert(0, str(AQUI))  # para carregar faber_real por nome


def exigir(modulo, dica):
    try:
        __import__(modulo)
    except ImportError:
        print("ERRO: dependência ausente: %s\n  %s" % (modulo, dica), file=sys.stderr)
        raise SystemExit(1)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    exigir("yaml", "pip install -r faber/dashboard/requirements.txt")
    exigir("flask", "pip install -r faber/dashboard/requirements.txt")

    verbosidade = 2 if "-v" in argv else 1
    if "--faber-real" in argv:
        print("alvo --faber-real: OBSERVAÇÕES sobre o repositório desta máquina.\n"
              "Falha aqui num clone limpo é esperada — não é regressão (ver faber_real.py).")
        testes = unittest.defaultTestLoader.loadTestsFromName("faber_real")
    else:
        testes = unittest.defaultTestLoader.discover(str(AQUI), pattern="teste_*.py",
                                                     top_level_dir=str(AQUI))
    resultado = unittest.TextTestRunner(verbosity=verbosidade).run(testes)
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
