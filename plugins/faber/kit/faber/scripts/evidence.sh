#!/bin/bash
# =============================================================================
# evidence.sh — executa o comando REAL e grava a evidência (zero LLM).
# ARQUITETURA §11 (Skill evidence), §15 ("falsa alegação de execução":
# gates verificam o arquivo, não a narrativa), R6 (limite 2 MB por arquivo).
#
# Uso: evidence.sh <TASK-XXX | pasta-da-demanda> <slug> -- <comando> [args...]
#   <slug>   [a-z0-9-]+ — vira evidence/NN-<slug>.log (NN auto-incrementa)
#   Pipelines/redirecionamentos: passe via bash -c:
#     evidence.sh TASK-52 lint -- bash -c "npm run lint 2>&1 | tail -50"
#
# O exit code do COMANDO é propagado (permite encadear com &&).
# Log > 2 MB: aviso para NÃO commitar (referenciar no handoff — R6/P3).
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Guarda estrita: sem faber/config/faber.env a fabrica nao foi instalada nesta
# arvore, e operar com defaults produziria gates contra a configuracao errada.
[ "${FABER_SKIP_INSTALL_CHECK:-0}" = "1" ] || [ -f "$DIR/../config/faber.env" ] || {
  echo "ERRO: Faber nao esta instalado nesta arvore (falta faber/config/faber.env)." >&2
  echo "      instale com:  /faber:install   (plugin do Claude Code)" >&2
  exit 1; }
TASKS="$DIR/../tasks"

uso() { echo "uso: evidence.sh <TASK-XXX|pasta> <slug> -- <comando> [args...]"; exit 1; }
[ $# -ge 4 ] || uso
ALVO="$1"; SLUG="$2"; SEP="$3"; shift 3
[ "$SEP" = "--" ] || uso
printf '%s' "$SLUG" | grep -qE '^[a-z0-9][a-z0-9-]*$' \
  || { echo "ERRO: slug '$SLUG' inválido (use [a-z0-9-], começando por letra/número)"; exit 1; }

if [ -d "$ALVO" ]; then PASTA="$ALVO"
elif [ -d "$TASKS/$ALVO" ]; then PASTA="$TASKS/$ALVO"
else echo "ERRO: pasta da demanda não encontrada ($ALVO)"; exit 1; fi
EV="$PASTA/evidence"; mkdir -p "$EV"

# NN = maior prefixo numérico existente + 1
NN=$(ls "$EV" 2>/dev/null | sed -n 's/^\([0-9][0-9]*\)-.*/\1/p' | sort -n | tail -1)
NN=$(printf '%02d' $(( 10#${NN:-0} + 1 )))
LOG="$EV/$NN-$SLUG.log"

INICIO=$(date +%Y-%m-%dT%H:%M:%S%z)
T0=$SECONDS
TMP=$(mktemp) || exit 1
trap 'rm -f "$TMP"' EXIT

# Executa o comando real; stdout+stderr capturados juntos, na ordem
"$@" > "$TMP" 2>&1
EXIT=$?
FIM=$(date +%Y-%m-%dT%H:%M:%S%z)
DUR=$(( SECONDS - T0 ))

{
  echo "# ── evidência executada por evidence.sh — NUNCA editar à mão ──"
  echo "# demanda/pasta: $PASTA"
  echo "# comando:       $*"
  echo "# início:        $INICIO"
  echo "# fim:           $FIM (duração: ${DUR}s)"
  echo "# exit code:     $EXIT"
  echo "# ────────────────────────────────────────────────────────────────"
  cat "$TMP"
} > "$LOG"

TAM=$(wc -c < "$LOG" | tr -d ' ')
echo "evidência: $LOG (exit=$EXIT, ${DUR}s, ${TAM} bytes)"
if [ "$TAM" -gt 2097152 ]; then
  echo "AVISO R6: log > 2 MB — NÃO commitar; referencie o caminho no handoff" >&2
fi
LINHAS=$(wc -l < "$TMP" | tr -d ' ')
if [ "$LINHAS" -gt 6 ]; then
  head -3 "$TMP" | sed 's/^/  │ /'; echo "  │ … ($LINHAS linhas)"; tail -3 "$TMP" | sed 's/^/  │ /'
else
  sed 's/^/  │ /' "$TMP"
fi

exit "$EXIT"
