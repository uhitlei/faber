#!/bin/bash
# =============================================================================
# workflow-unlock.sh — autoriza (ou revoga) a edição de .github/workflows/* na
# demanda, gravando `workflow_unlock` no state.yaml (zero LLM).
# O H2 LIBERA a edição de workflow quando workflow_unlock.autorizado=true pelo
# owner (_schema.owner); senão pede confirmação manual (ask, §2/§19).
#
# Uso: workflow-unlock.sh <TASK-XXX> --por <owner> [--motivo "..."] [--revogar]
# Exit: 0 ok · 1 uso/validação · 2 falha git.
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Guarda estrita: sem faber/config/faber.env a fabrica nao foi instalada nesta
# arvore, e operar com defaults produziria gates contra a configuracao errada.
[ "${FABER_SKIP_INSTALL_CHECK:-0}" = "1" ] || [ -f "$DIR/../config/faber.env" ] || {
  echo "ERRO: Faber nao esta instalado nesta arvore (falta faber/config/faber.env)." >&2
  echo "      instale com:  /faber:install   (plugin do Claude Code)" >&2
  exit 1; }
TEMPLATE="$DIR/../templates/state.template.yaml"
BOARD="$DIR/board.sh"
TASKS="$DIR/../tasks"

uso() { echo "uso: workflow-unlock.sh <TASK-XXX> --por <owner> [--motivo \"...\"] [--revogar]"; exit 1; }
[ $# -ge 1 ] || uso
TASK="$1"; shift
POR=""; MOTIVO=""; ACAO="autorizar"
while [ $# -gt 0 ]; do
  case "$1" in
    --por)     POR="${2:?}"; shift 2 ;;
    --motivo)  MOTIVO="${2:?}"; shift 2 ;;
    --revogar) ACAO="revogar"; shift ;;
    *) uso ;;
  esac
done
[ -n "$POR" ] || { echo "ERRO: --por <aprovador> é obrigatório"; exit 1; }

STATE="$TASKS/$TASK/state.yaml"
[ -f "$STATE" ] || { echo "ERRO: $STATE não existe"; exit 1; }
N="${TASK##TASK-}"

python3 - "$TEMPLATE" "$STATE" "$POR" "$MOTIVO" "$ACAO" <<'PY' || exit 1
import sys, yaml
from datetime import datetime
owner = (yaml.safe_load(open(sys.argv[1]))["_schema"].get("owner")) or "owner"
state, por, motivo, acao = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
if por != owner:
    print(f"ERRO: workflow_unlock só é autorizado por '{owner}' (§19), não '{por}'"); sys.exit(1)
d = yaml.safe_load(open(state))
agora = datetime.now().astimezone().isoformat(timespec="seconds")
d["workflow_unlock"] = {
    "authorized": (acao == "autorizar"),
    "by": por,
    "at": agora,
    "reason": (motivo or None),
}
d["updated_at"] = agora
yaml.safe_dump(d, open(state, "w"), allow_unicode=True, sort_keys=False)
print(f"workflow_unlock: {'authorized' if acao=='autorizar' else 'REVOGADO'} por {por}")
PY
RC=$?; [ $RC -eq 0 ] || exit $RC

git add "$STATE" && git commit -q -m "chore($TASK): workflow_unlock $ACAO por $POR" \
  || { echo "ERRO: commit falhou"; exit 2; }
"$BOARD" comentar "$N" "🏭 **$TASK**: workflow_unlock **$ACAO** (por: $POR${MOTIVO:+; motivo: $MOTIVO})" \
  || echo "AVISO: comentário não postado"
echo "OK: workflow_unlock $ACAO registrado e commitado"
