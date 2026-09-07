#!/bin/bash
# =============================================================================
# new-task.sh — mecânica do /faber-task (zero LLM). ARQUITETURA §12, §16, D5.
# Demandas nascem em WORKTREE próprio por padrão (CLAUDE.md §4).
# Cria: issue (label faber; ou número do contador local se FABER_GH=off)
# → TASK-<N> → branch feature/TASK-N num worktree próprio
# (.claude/worktrees/TASK-N; a raiz não é tocada) → pasta da demanda com
# state.yaml instanciado do template (SEM o bloco _schema) → commit inicial →
# board (add + coluna Backlog/intake, se FABER_BOARD=on).
#
# Uso: new-task.sh <tipo> "<título>" [--base <ref>] [--dirty-ok] [--issue <N>] [--noworktrees]
#   <tipo>  um de _schema.tipos (feature|bug|incidente|debito-tecnico|
#           seguranca|infra|banco|documentacao|spike|design)
#   --base  ref de origem da branch (default: <remote>/<trunk>, com fetch;
#           a base precisa conter a fábrica)
#   --issue <N>  adota uma issue já existente em vez de criar uma nova
#   --noworktrees  modo raiz (exceção, só a pedido do Owner): checkout da
#           branch no working tree atual; exige tree limpo. Sem a flag, a
#           demanda nasce em worktree e o script termina imprimindo
#           WORKTREE=<path> (mesmo contrato do worktree.sh, que REUSA esse
#           worktree no /faber-resume).
#   --dirty-ok  (só relevante com --noworktrees) permite tree sujo
#
# Exit: 0 ok · 1 erro de uso/validação · 2 falha git/gh.
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
. "$DIR/lib/config.sh"
faber_require_install
TEMPLATE="$DIR/../templates/state.template.yaml"
BOARD="$DIR/board.sh"

uso() { echo "uso: new-task.sh <tipo> \"<título>\" [--base <ref>] [--dirty-ok] [--issue <N>] [--noworktrees]"; exit 1; }
[ $# -ge 2 ] || uso
TIPO="$1"; TITULO="$2"; shift 2
BASE_PADRAO="$FABER_REMOTE/$FABER_TRUNK"
BASE="$BASE_PADRAO"; DIRTY_OK=0; ADOPT_ISSUE=""; NOWT=0
[ "$FABER_WORKTREES" = "on" ] || NOWT=1
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="${2:?--base exige ref}"; shift 2 ;;
    --dirty-ok) DIRTY_OK=1; shift ;;
    --issue) ADOPT_ISSUE="${2:?--issue exige número}"; shift 2 ;;
    --noworktrees) NOWT=1; shift ;;
    *) uso ;;
  esac
done

# 1. valida tipo contra o _schema (fonte única)
python3 - "$TEMPLATE" "$TIPO" <<'PY' || exit 1
import sys, yaml
tipos = yaml.safe_load(open(sys.argv[1]))["_schema"]["types"]
if sys.argv[2] not in tipos:
    print(f"ERRO: tipo '{sys.argv[2]}' inválido. Válidos: {', '.join(tipos)}")
    sys.exit(1)
PY

# 2. working tree limpo — só no modo raiz
if [ "$NOWT" -eq 1 ] && [ "$DIRTY_OK" -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
  echo "ERRO: working tree sujo — commit/stash antes, ou use --dirty-ok"; exit 1
fi

# 3. template em tmp ANTES do checkout (a base pode não conter a fábrica)
TPL_TMP=$(mktemp); trap 'rm -f "$TPL_TMP"' EXIT
cp "$TEMPLATE" "$TPL_TMP"

# 4. número da demanda = número da issue (D5) — ou contador local sem GitHub
if [ "$BASE" = "$BASE_PADRAO" ]; then git fetch -q "$FABER_REMOTE" "$FABER_TRUNK" 2>/dev/null || true; fi
if git rev-parse --verify --quiet "$BASE" >/dev/null; then :; else
  # sem remoto/trunk remoto: cai para a branch local do trunk, se existir
  if git rev-parse --verify --quiet "$FABER_TRUNK" >/dev/null; then BASE="$FABER_TRUNK"
  else echo "ERRO: base '$BASE' não existe (crie a branch $FABER_TRUNK ou passe --base)"; exit 1; fi
fi
# a base precisa conter a fábrica (senão o worktree nasce sem scripts/hooks)
if ! git cat-file -e "$BASE:faber/scripts/gate-check.sh" 2>/dev/null; then
  echo "ERRO: a base '$BASE' não contém a fábrica (faber/scripts/gate-check.sh)."
  echo "      Mescle a PR de fundação (faber/bootstrap) em $FABER_TRUNK antes de abrir demandas — ou passe --base <ref que já a contenha>."
  exit 1
fi

URL=""
if [ "$FABER_GH" = "on" ]; then
  REPO=$(faber_gh_repo) || { echo "ERRO: não descobri owner/repo (defina FABER_GH_REPO ou o remote $FABER_REMOTE)"; exit 2; }
  command -v gh >/dev/null 2>&1 || { echo "ERRO: gh CLI ausente (FABER_GH=on exige gh autenticado; ou use FABER_GH=off)"; exit 2; }
  if [ -n "$ADOPT_ISSUE" ]; then
    N="$ADOPT_ISSUE"
    case "$N" in ''|*[!0-9]*) echo "ERRO: --issue exige número (recebi '$N')"; exit 1 ;; esac
    gh issue view "$N" --repo "$REPO" --json number >/dev/null 2>&1 \
      || { echo "ERRO: issue #$N não existe em $REPO"; exit 2; }
    gh issue edit "$N" --repo "$REPO" --add-label faber >/dev/null 2>&1 || true
    URL="https://github.com/$REPO/issues/$N"
    echo "issue adotada: #$N ($URL)"
  else
    URL=$(gh issue create --repo "$REPO" --title "$TITULO" --label faber \
      --body "Demanda criada pela fábrica de software (tipo: $TIPO).

Artefatos: \`faber/tasks/TASK-<este número>/\` na branch \`feature/TASK-<este número>\`.
Fluxo e gates: \`faber/ARCHITECTURE.md\` §5/§6/§18.") || { echo "ERRO: gh issue create falhou (label 'faber' existe? rode board.sh bootstrap-labels)"; exit 2; }
    N="${URL##*/}"
    echo "issue: #$N ($URL)"
  fi
else
  # contador local: maior TASK-N conhecida (pastas + branches) + 1
  if [ -n "$ADOPT_ISSUE" ]; then N="$ADOPT_ISSUE"; else
    MAX=$( { ls -1 "$DIR/../tasks" 2>/dev/null | sed -n 's/^TASK-\([0-9]*\)$/\1/p';
            git for-each-ref --format='%(refname:short)' 'refs/heads/feature/TASK-*' 'refs/remotes/*/feature/TASK-*' 2>/dev/null | sed -n 's/.*TASK-\([0-9]*\)$/\1/p';
            cat "$DIR/../tasks/.contador" 2>/dev/null; } | sort -n | tail -1)
    N=$(( ${MAX:-0} + 1 ))
  fi
  echo "$N" > "$DIR/../tasks/.contador"
  echo "demanda #$N (contador local — FABER_GH=off)"
fi
TASK="TASK-$N"
BRANCH="feature/$TASK"

# 4b. não clobrar uma demanda já existente (branch local ou remota)
if git show-ref --verify --quiet "refs/heads/$BRANCH" \
   || git show-ref --verify --quiet "refs/remotes/$FABER_REMOTE/$BRANCH"; then
  echo "ERRO: branch $BRANCH já existe — #$N já é uma demanda (use /faber-resume)"; exit 1
fi

# 5. branch a partir da base — num worktree próprio (padrão) ou na raiz
if [ "$NOWT" -eq 1 ]; then
  git checkout -b "$BRANCH" "$BASE" || { echo "ERRO: checkout -b $BRANCH $BASE falhou (issue #$N já criada — trate manualmente)"; exit 2; }
  ARVORE="."
else
  GIT_COMMON=$(git rev-parse --git-common-dir) || { echo "ERRO: fora de um repositório git"; exit 2; }
  MAIN_ROOT=$(cd "$(dirname "$GIT_COMMON")" && pwd)
  WT="$MAIN_ROOT/.claude/worktrees/$TASK"
  if [ -e "$WT" ]; then
    echo "ERRO: $WT já existe — reconcilie antes (worktree.sh list). Issue #$N já criada — trate manualmente."; exit 2
  fi
  mkdir -p "$MAIN_ROOT/.claude/worktrees"
  git worktree add "$WT" -b "$BRANCH" "$BASE" \
    || { echo "ERRO: git worktree add falhou (issue #$N já criada — trate manualmente)"; exit 2; }
  ARVORE="$WT"
fi

# 6. pasta + state.yaml instanciado (remove _schema; preenche identificação)
PASTA="faber/tasks/$TASK"
mkdir -p "$ARVORE/$PASTA/handoffs" "$ARVORE/$PASTA/evidence"
touch "$ARVORE/$PASTA/handoffs/.gitkeep" "$ARVORE/$PASTA/evidence/.gitkeep"
python3 - "$TPL_TMP" "$ARVORE/$PASTA/state.yaml" "$TASK" "$N" "$TITULO" "$TIPO" "$BRANCH" <<'PY' || exit 2
import sys, yaml
from datetime import datetime
tpl = yaml.safe_load(open(sys.argv[1]))
del tpl["_schema"]                      # nunca vaza para a instância
agora = datetime.now().astimezone().isoformat(timespec="seconds")
tpl.update(demanda=sys.argv[3], issue=int(sys.argv[4]), titulo=sys.argv[5],
           tipo=sys.argv[6], branch=sys.argv[7], criada_em=agora, atualizada_em=agora)
yaml.safe_dump(tpl, open(sys.argv[2], "w"), allow_unicode=True, sort_keys=False)
print(f"state.yaml: {sys.argv[2]}")
PY

# 7. commit inicial da demanda na própria branch (P3/D6)
git -C "$ARVORE" add "$PASTA" && git -C "$ARVORE" commit -q -m "chore($TASK): abre demanda — $TITULO [intake]" \
  || { echo "ERRO: commit inicial falhou"; exit 2; }
echo "commit: $(git -C "$ARVORE" log --oneline -1)"

# 8. board/labels (R4: falha não bloqueia — state.yaml é a fonte de verdade)
if [ -x "$BOARD" ]; then
  "$BOARD" mover "$N" intake || echo "AVISO: board/labels falharam (reconcilie depois com board.sh move $N intake)"
fi

echo "OK: $TASK criada — branch $BRANCH, pasta $PASTA${URL:+, issue $URL}"
if [ "$NOWT" -eq 0 ]; then echo "WORKTREE=$WT"; fi
