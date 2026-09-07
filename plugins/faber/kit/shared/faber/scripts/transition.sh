#!/bin/bash
# =============================================================================
# transition.sh — executa uma transição de estado completa (zero LLM).
# ARQUITETURA §6.2: toda transição = gate-check OK + state.yaml atualizado e
# COMMITADO + comentário-padrão na issue + board movido — tudo num só script.
#
# Uso: transition.sh <TASK-XXX> <estado-destino> [--motivo "..."] [--por <quem>]
#                   [--pr <numero|url>]
#   --motivo  obrigatório p/ regressão, blocked e cancelled (gate-check exige)
#   --por     quem executa a transição (default: cto)
#   --pr      número/URL da PR — usado na transição para pr-open (gate-check
#             exige campo `pr` preenchido; se já estiver no state, é opcional)
#
# Exit: 0 ok · 1 bloqueada pelo gate-check ou uso incorreto · 2 falha git.
# (Falha de board/issue = aviso, não bloqueia — R4.)
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Guarda estrita: sem faber/config/faber.env a fabrica nao foi instalada nesta
# arvore, e operar com defaults produziria gates contra a configuracao errada.
[ "${FABER_SKIP_INSTALL_CHECK:-0}" = "1" ] || [ -f "$DIR/../config/faber.env" ] || {
  echo "ERRO: Faber nao esta instalado nesta arvore (falta faber/config/faber.env)." >&2
  echo "      instale com:  /faber:install   (plugin do Claude Code)" >&2
  exit 1; }
GC="$DIR/gate-check.sh"
BOARD="$DIR/board.sh"
TASKS="$DIR/../tasks"

uso() { echo "uso: transition.sh <TASK-XXX> <estado-destino> [--motivo \"...\"] [--por <quem>] [--pr <url>]"; exit 1; }
[ $# -ge 2 ] || uso
TASK="$1"; DESTINO="$2"; shift 2
MOTIVO=""; POR="cto"; PR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --motivo) MOTIVO="${2:?--motivo exige texto}"; shift 2 ;;
    --por)    POR="${2:?--por exige valor}"; shift 2 ;;
    --pr)     PR="${2:?--pr exige numero/url}"; shift 2 ;;
    *) uso ;;
  esac
done

PASTA="$TASKS/$TASK"
STATE="$PASTA/state.yaml"
[ -f "$STATE" ] || { echo "ERRO: $STATE não existe"; exit 1; }
N="${TASK##TASK-}"
ATUAL=$(python3 -c "import yaml,sys;print(yaml.safe_load(open(sys.argv[1]))['state'])" "$STATE")

# blocked: bloqueio precisa estar gravado ANTES do gate-check (que o valida)
if [ "$DESTINO" = "blocked" ]; then
  [ -n "$MOTIVO" ] || { echo "ERRO: blocked exige --motivo (§6.2)"; exit 1; }
  python3 - "$STATE" "$MOTIVO" "$ATUAL" <<'PY'
import sys, yaml
from datetime import datetime
d = yaml.safe_load(open(sys.argv[1]))
d["blocking"] = {"reason": sys.argv[2],
                 "since": datetime.now().astimezone().isoformat(timespec="seconds"),
                 "previous_state": sys.argv[3]}
yaml.safe_dump(d, open(sys.argv[1], "w"), allow_unicode=True, sort_keys=False)
PY
fi

# pr-open: grava o campo `pr` como rascunho ANTES do gate-check, que
# exige `pr` preenchido. Mesmo padrão do bloqueio; mesmo rollback se bloquear.
if [ "$DESTINO" = "pr-open" ] && [ -n "$PR" ]; then
  python3 - "$STATE" "$PR" <<'PY'
import sys, yaml
d = yaml.safe_load(open(sys.argv[1]))
d["pr"] = sys.argv[2]
yaml.safe_dump(d, open(sys.argv[1], "w"), allow_unicode=True, sort_keys=False)
PY
fi

# gate-check: nenhuma transição sem ele (§6.2). Bloqueou → desfaz o rascunho.
if ! "$GC" "$TASK" "$DESTINO" ${MOTIVO:+--motivo "$MOTIVO"}; then
  git checkout -q -- "$STATE" 2>/dev/null || true
  exit 1
fi

# aplica a transição no state.yaml
python3 - "$STATE" "$ATUAL" "$DESTINO" "$POR" "$MOTIVO" <<'PY' || exit 2
import sys, yaml
from datetime import datetime
d = yaml.safe_load(open(sys.argv[1]))
agora = datetime.now().astimezone().isoformat(timespec="seconds")
d["history"] = (d.get("history") or []) + [{
    "from_state": sys.argv[2], "to_state": sys.argv[3], "at": agora,
    "by": sys.argv[4], "reason": sys.argv[5] or None}]
d["state"] = sys.argv[3]
d["updated_at"] = agora
if sys.argv[2] == "blocked" and sys.argv[3] != "blocked":
    d["blocking"] = None          # saiu do bloqueio: origem alcançada
yaml.safe_dump(d, open(sys.argv[1], "w"), allow_unicode=True, sort_keys=False)
PY

git add "$STATE" && git commit -q -m "chore($TASK): transição $ATUAL -> $DESTINO${MOTIVO:+ — $MOTIVO}" \
  || { echo "ERRO: commit da transição falhou"; exit 2; }
echo "state: $ATUAL -> $DESTINO (commit $(git log --oneline -1 | cut -d' ' -f1))"

# projeções issue/board (falha = aviso; reconciliáveis depois — R4)
"$BOARD" mover "$N" "$DESTINO" || echo "AVISO: board não movido (board.sh mover $N $DESTINO)"
"$BOARD" comentar "$N" "🏭 **$TASK**: \`$ATUAL\` → \`$DESTINO\`${MOTIVO:+ — motivo: $MOTIVO} (gate-check: liberada; por: $POR)" \
  || echo "AVISO: comentário não postado"

echo "OK: $TASK agora em '$DESTINO'"