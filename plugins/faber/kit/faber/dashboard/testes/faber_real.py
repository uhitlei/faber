#!/usr/bin/env python3
# =============================================================================
# faber_real.py — OBSERVAÇÕES sobre o estado atual desta máquina.
#
# Isto NÃO é a suíte: o nome está fora do padrão `teste_*.py` de propósito,
# para o discover do rodar.py não pegar. O que está aqui assere propriedades
# do repositório de trabalho AGORA — quantos checkouts vivos existem, se há
# divergência real entre cópias — e por isso falha, com razão, num clone
# limpo. Suíte que só passa numa máquina é suíte que impede CI e faz a
# segunda máquina ler vermelho sem nada quebrado.
#
# O valor destas observações é real (são a prova viva da AC-1/RN-13 contra a
# fábrica de verdade), então elas continuam existindo — só que como alvo
# explícito, e cada uma diz o que mediu antes de assertar.
#
# Uso: faber/dashboard/dashboard.sh --testes --faber-real
#      (ou: .venv/bin/python -B testes/rodar.py --faber-real)
# =============================================================================
"""Observações sobre a fábrica real desta máquina (fora da suíte portátil)."""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import leitor  # noqa: E402

ESQUEMA = leitor.carregar_esquema()


class TesteEstadoDestaMaquina(unittest.TestCase):
    """Não roda no discover: depende do repositório de trabalho de agora."""

    @classmethod
    def setUpClass(cls):
        cls.projecao = leitor.projetar(esquema=ESQUEMA)
        cls.por_fonte = {}
        for d in cls.projecao["demandas"]:
            for c in d["copias"]:
                cls.por_fonte.setdefault(c["fonte"], set()).add(c["nome"])

    def test_uniao_ve_mais_do_que_a_melhor_fonte_isolada(self):
        """A prova de que ler um diretório só entregaria quadro incompleto."""
        melhor = max(len(v) for v in self.por_fonte.values())
        print("\n  união: %d demandas · melhor fonte isolada: %d · fontes: %d"
              % (len(self.projecao["demandas"]), melhor, len(self.por_fonte)))
        self.assertGreater(
            len(self.projecao["demandas"]), melhor,
            "clone recém-feito tem uma fonte só — este alvo é sobre a máquina de trabalho")

    def test_ha_divergencia_real_entre_copias(self):
        """Se um dia isto falhar aqui, a fábrica parou de divergir — ótimo notar."""
        divergentes = [d["nome"] for d in self.projecao["demandas"] if d["estados_divergentes"]]
        print("\n  demandas com cópias divergentes: %s" % (divergentes or "nenhuma"))
        self.assertTrue(divergentes, "nenhuma divergência: confira se a varredura de refs quebrou")

    def test_leitura_da_faber_real_nao_esta_degradada(self):
        """Se alguma fonte falhou aqui, o número acima está incompleto."""
        print("\n  falhas de fonte: %s" % (self.projecao["falhas"] or "nenhuma"))
        self.assertEqual(self.projecao["falhas"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
