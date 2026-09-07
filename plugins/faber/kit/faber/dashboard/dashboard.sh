#!/bin/bash
# =============================================================================
# dashboard.sh — sobe o dashboard local da fábrica (módulo opcional, ligado
# por FABER_DASHBOARD=on em faber/config/faber.env).
#
# Bind SEMPRE em 127.0.0.1 (decisão do Owner): o app não tem opção de host.
# Sem daemon, sem autostart — roda sob demanda e morre no Ctrl+C.
#
# O dashboard não escreve nada em disco além do banco local de telemetria em
# dados/, e essa garantia vale mais checada do que prometida: `-B` cobre o
# interpretador que recebemos e o `export PYTHONDONTWRITEBYTECODE=1` cobre
# TODO subprocesso lançado daqui. Só `-B` não bastava — basta uma sonda com
# outro interpretador para aparecer __pycache__/ dentro de faber/dashboard/.
#
# Uso: faber/dashboard/dashboard.sh [porta]      (padrão: 8099)
#      faber/dashboard/dashboard.sh --testes     (suíte portátil)
#      faber/dashboard/dashboard.sh --testes --faber-real
#                                                  (observações desta máquina)
# Exit: 0 = ok · 1 = ambiente incompleto (venv/dependências)
# =============================================================================
set -u
export PYTHONDONTWRITEBYTECODE=1   # herdada por pip, python e qualquer sonda

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
PY="$VENV/bin/python"

if [ ! -x "$PY" ]; then
  echo "venv ausente — criando em $VENV"
  python3 -m venv "$VENV" || { echo "ERRO: não foi possível criar o venv"; exit 1; }
  "$VENV/bin/pip" install -q -r "$DIR/requirements.txt" \
    || { echo "ERRO: falha ao instalar $DIR/requirements.txt"; exit 1; }
fi

"$PY" -c 'import flask, yaml' 2>/dev/null || {
  echo "dependências ausentes — instalando $DIR/requirements.txt"
  "$VENV/bin/pip" install -q -r "$DIR/requirements.txt" || exit 1
}

if [ "${1:-}" = "--testes" ]; then
  exec "$PY" -B "$DIR/testes/rodar.py" "${@:2}"
fi

exec "$PY" -B "$DIR/app.py" --porta "${1:-8099}"
