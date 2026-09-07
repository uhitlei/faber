#!/bin/bash
# =============================================================================
# gate-set.sh — registra o resultado de um gate no state.yaml (zero LLM).
# ARQUITETURA §18. A validade fina (aprovador por gate, evidência de G3/G5)
# é imposta pelo gate-check.sh na transição; aqui vai a defesa de primeira
# linha: gates humanos (G1/G6/G8) só aceitam --por <owner> (_schema.owner).
#
# Uso: gate-set.sh <TASK-XXX> <G1..G9> <aprovado|reprovado|nao-aplicavel|pendente>
#                  --por <aprovador> [--evidencia <path|url>] [--obs "..."]
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

uso() { echo "uso: gate-set.sh <TASK-XXX> <G1..G9> <status> --por <aprovador> [--evidencia x] [--obs \"...\"]"; exit 1; }
[ $# -ge 3 ] || uso
TASK="$1"; GATE="$2"; STATUS="$3"; shift 3
POR=""; EVIDENCIA=""; OBS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --por)       POR="${2:?}"; shift 2 ;;
    --evidencia) EVIDENCIA="${2:?}"; shift 2 ;;
    --obs)       OBS="${2:?}"; shift 2 ;;
    *) uso ;;
  esac
done
[ -n "$POR" ] || { echo "ERRO: --por <aprovador> é obrigatório"; exit 1; }

STATE="$TASKS/$TASK/state.yaml"
[ -f "$STATE" ] || { echo "ERRO: $STATE não existe"; exit 1; }
N="${TASK##TASK-}"

python3 - "$TEMPLATE" "$STATE" "$GATE" "$STATUS" "$POR" "$EVIDENCIA" "$OBS" "$DIR" <<'PY' || exit 1
import sys, yaml
from datetime import datetime
schema = yaml.safe_load(open(sys.argv[1]))["_schema"]
owner = schema.get("owner") or "owner"
gate, status, por = sys.argv[3], sys.argv[4], sys.argv[5]
if gate not in schema["gates"]:
    print(f"ERRO: gate '{gate}' inválido ({schema['gates']})"); sys.exit(1)
if status not in schema["gate_status"]:
    print(f"ERRO: status '{status}' inválido ({schema['gate_status']})"); sys.exit(1)
if gate in schema["gates_humanos"] and status == "aprovado" and por != owner:
    print(f"ERRO: {gate} é gate humano — só '{owner}' aprova (§15), não '{por}'"); sys.exit(1)
d = yaml.safe_load(open(sys.argv[2]))
g = d["gates"][gate]
if gate == "G1":
    from pathlib import Path
    folder = Path(sys.argv[2]).parent
    cfg = d.get("discovery")
    if cfg is not None and (not isinstance(cfg, dict) or type(cfg.get("required")) is not bool):
        print("ERRO: discovery.required deve ser booleano"); sys.exit(1)
    if (folder / "requirements").exists() or (cfg and cfg["required"]):
        if status == "aprovado":
            try:
                sys.path.insert(0, str(Path(sys.argv[8]) / "lib"))
                from requirements import delivery_hash
                g["requirements_hash"] = delivery_hash(folder)
            except Exception as exc:
                print(f"ERRO: discovery: {exc}"); sys.exit(1)
        else:
            g.pop("requirements_hash", None)
g.update(status=status, aprovador=(por if status != "pendente" else None),
         em=datetime.now().astimezone().isoformat(timespec="seconds"),
         evidencia=(sys.argv[6] or g.get("evidencia")), obs=(sys.argv[7] or g.get("obs")))
d["atualizada_em"] = g["em"]
yaml.safe_dump(d, open(sys.argv[2], "w"), allow_unicode=True, sort_keys=False)
print(f"{gate} ({g['nome']}): {status} por {por}")
PY
RC=$?; [ $RC -eq 0 ] || exit $RC

git add "$STATE" && git commit -q -m "chore($TASK): $GATE $STATUS por $POR" \
  || { echo "ERRO: commit falhou"; exit 2; }
"$BOARD" comentar "$N" "🏭 **$TASK**: gate **$GATE** → \`$STATUS\` (por: $POR${EVIDENCIA:+; evidência: $EVIDENCIA})" \
  || echo "AVISO: comentário não postado"
echo "OK: $GATE=$STATUS registrado e commitado"
