#!/bin/bash
# =============================================================================
# worktree.sh — mecânica de worktrees do /faber-resume (zero LLM). ARQUITETURA §5/§6.
# Isola cada demanda num git worktree próprio (concorrência entre instâncias) e
# garante que todo resume parte do trunk atual (FABER_TRUNK).
#
# Uso:
#   worktree.sh abrir  <TASK-XXX|XXX>   cria/reusa o worktree e mescla o trunk
#   worktree.sh fechar <TASK-XXX|XXX>   remove o worktree (guarda anti-perda)
#   worktree.sh limpar <TASK-XXX|XXX>   pós-merge: fecha o worktree E APAGA a
#                                         branch (local + remota) — só se ela já
#                                         estiver mergeada no trunk
#   worktree.sh listar                    lista os worktrees de demanda ativos
#
# limpar é o passo de faxina do G9/done (§6 estado 13, §18-G9): uma demanda
# concluída não deixa branch para trás. A guarda é fail-closed — se a branch
# NÃO for ancestral de <remote>/<trunk>, o comando recusa e não apaga nada; o
# merge é sempre do Owner (G8), então "não mergeada" = "ainda tem trabalho vivo".
# Idempotente: branch já apagada = nada a fazer.
#
# abrir resolve a branch nesta ordem: 1) feature/TASK-XXX local · 2)
# <remote>/feature/TASK-XXX (puxa a pasta commitada) · 3) não existe → erro
# "abra com /faber-task". Depois mescla <remote>/<trunk> na branch. Conflito NÃO é
# auto-resolvido: para, deixa o worktree em conflito e escala (§6.2).
#
# Worktrees vivem em .claude/worktrees/ (gitignored). Branch e commits
# sobrevivem ao `fechar` — só o checkout descartável é removido.
#
# Exit: 0 ok · 1 erro de uso/demanda inexistente/worktree sujo · 2 branch não
#       mergeada (limpar recusa) · 3 conflito de merge.
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
. "$DIR/lib/config.sh"
faber_require_install

GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null) || { echo "ERRO: fora de um repositório git"; exit 1; }
MAIN_ROOT=$(cd "$(dirname "$GIT_COMMON")" && pwd)
WT_BASE="$MAIN_ROOT/.claude/worktrees"

uso() { echo "uso: worktree.sh {abrir|fechar|limpar|listar} [TASK-XXX]"; exit 1; }

TRUNK="${FABER_TRUNK}"; REMOTE="${FABER_REMOTE}"
OWNER_NOME="${FABER_OWNER_NAME}"

resolve_tarefa() {
  local arg="${1:-}"; [ -n "$arg" ] || { echo "ERRO: informe a demanda (ex.: TASK-83 ou 83)"; exit 1; }
  local n="${arg##*-}"
  case "$n" in ''|*[!0-9]*) echo "ERRO: demanda inválida: '$arg'"; exit 1 ;; esac
  TASK="TASK-$n"; BRANCH="feature/$TASK"; WT="$WT_BASE/$TASK"
}

# ref do trunk a mesclar: remoto se existir, senão local
trunk_ref() {
  if git show-ref --verify --quiet "refs/remotes/$REMOTE/$TRUNK"; then echo "$REMOTE/$TRUNK"
  elif git show-ref --verify --quiet "refs/heads/$TRUNK"; then echo "$TRUNK"
  else echo ""; fi
}

cmd="${1:-}"; shift || true
case "$cmd" in

  abrir)
    resolve_tarefa "${1:-}"
    mkdir -p "$WT_BASE"
    echo "→ fetch do trunk ($TRUNK) e da branch da demanda…"
    git fetch -q "$REMOTE" "$TRUNK" 2>/dev/null || echo "AVISO: fetch de $REMOTE/$TRUNK falhou (seguindo com a cópia local)"
    git fetch -q "$REMOTE" "$BRANCH" 2>/dev/null || true

    if git worktree list --porcelain | grep -qx "worktree $WT"; then
      echo "→ reusando worktree existente: $WT"
    elif git show-ref --verify --quiet "refs/heads/$BRANCH"; then
      git worktree add "$WT" "$BRANCH" || { echo "ERRO: git worktree add falhou (branch já em uso por outro worktree?)"; exit 1; }
    elif git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH"; then
      echo "→ pasta ausente local; puxando a branch do git ($REMOTE/$BRANCH)…"
      git worktree add "$WT" -b "$BRANCH" "$REMOTE/$BRANCH" || { echo "ERRO: git worktree add -b falhou"; exit 1; }
    else
      echo "ERRO: demanda $TASK não existe em disco nem no git (sem branch $BRANCH)."
      echo "      Ela nunca foi aberta como demanda — abra com /faber-task."
      exit 1
    fi

    TREF=$(trunk_ref)
    if [ -n "$TREF" ]; then
      echo "→ mesclando $TREF (parte do trunk atual)…"
      if ! ( cd "$WT" && git merge --no-edit "$TREF" ); then
        echo "ERRO: CONFLITO ao mesclar $TREF em $BRANCH."
        echo "      Worktree em conflito: $WT"
        echo "      Resolva + commite lá, ou 'git -C \"$WT\" merge --abort'. Não avance com o conflito aberto (§6.2)."
        exit 3
      fi
      behind=$(git -C "$WT" rev-list --count "$BRANCH..$TREF" 2>/dev/null || echo "?")
      ahead=$(git -C "$WT" rev-list --count "$TREF..$BRANCH" 2>/dev/null || echo "?")
      echo "OK: worktree pronto — branch $BRANCH em cima do trunk atual (ahead:$ahead behind:$behind)"
    else
      echo "AVISO: trunk '$TRUNK' não encontrado (local nem remoto) — worktree aberto sem merge"
    fi
    echo "WORKTREE=$WT"
    ;;

  fechar)
    resolve_tarefa "${1:-}"
    if ! git worktree list --porcelain | grep -qx "worktree $WT"; then
      echo "OK: nenhum worktree ativo para $TASK (nada a fazer)"; exit 0
    fi
    if [ -n "$(cd "$WT" && git status --porcelain)" ]; then
      echo "ERRO: worktree $WT tem mudanças não-commitadas."
      echo "      O trabalho vive na branch: commite antes de fechar (ou descarte deliberadamente)."
      exit 1
    fi
    git worktree remove "$WT" || { echo "ERRO: git worktree remove falhou"; exit 1; }
    git worktree prune
    echo "OK: worktree removido — $WT (branch $BRANCH e commits preservados no git)"
    ;;

  limpar)
    resolve_tarefa "${1:-}"
    echo "→ fetch do trunk e da branch da demanda…"
    git fetch -q -p "$REMOTE" "$TRUNK" 2>/dev/null || echo "AVISO: fetch de $REMOTE/$TRUNK falhou — usando a cópia local do trunk"
    TREF=$(trunk_ref)
    [ -n "$TREF" ] || { echo "ERRO: trunk '$TRUNK' não existe — sem isso não dá para provar que a branch foi mergeada"; exit 1; }

    tem_local=0;  git show-ref --verify --quiet "refs/heads/$BRANCH" && tem_local=1
    tem_remota=0; git show-ref --verify --quiet "refs/remotes/$REMOTE/$BRANCH" && tem_remota=1
    if [ "$tem_local" -eq 0 ] && [ "$tem_remota" -eq 0 ]; then
      echo "OK: branch $BRANCH não existe mais (local nem remota) — nada a fazer"; exit 0
    fi

    ref_check="refs/heads/$BRANCH"; [ "$tem_remota" -eq 1 ] && ref_check="refs/remotes/$REMOTE/$BRANCH"
    if ! git merge-base --is-ancestor "$ref_check" "$TREF"; then
      echo "ERRO: $BRANCH NÃO está mergeada em $TREF — recuso apagar."
      echo "      Commits ainda fora do trunk:"
      git log --oneline "$TREF..$ref_check" | head -5 | sed 's/^/        /'
      echo "      O merge é de $OWNER_NOME (G8). Se a demanda foi cancelada, apague à mão, deliberadamente."
      exit 2
    fi

    if git worktree list --porcelain | grep -qx "worktree $WT"; then
      if [ -n "$(cd "$WT" && git status --porcelain)" ]; then
        echo "ERRO: worktree $WT tem mudanças não-commitadas — commite ou descarte antes de limpar"; exit 1
      fi
      git worktree remove "$WT" || { echo "ERRO: git worktree remove falhou"; exit 1; }
      git worktree prune
      echo "worktree removido: $WT"
    fi

    if [ "$tem_local" -eq 1 ]; then
      # -D de propósito: `-d` valida contra o HEAD do checkout principal, não
      # contra o trunk; quem autoriza é a guarda --is-ancestor acima.
      git branch -D "$BRANCH" >/dev/null || { echo "ERRO: git branch -D falhou"; exit 1; }
      echo "branch local apagada: $BRANCH"
    fi
    if [ "$tem_remota" -eq 1 ]; then
      git push -q "$REMOTE" --delete "$BRANCH" || { echo "AVISO: falha ao apagar a branch remota (o GitHub pode já tê-la apagado no merge)"; }
      echo "branch remota apagada: $REMOTE/$BRANCH"
    fi

    echo "OK: $TASK limpa — worktree e branch removidos (histórico preservado no trunk)"
    ;;

  listar)
    out=$(git worktree list | grep "/.claude/worktrees/TASK-" || true)
    if [ -n "$out" ]; then echo "$out"; else echo "(nenhum worktree de demanda ativo)"; fi
    ;;

  *) uso ;;
esac
