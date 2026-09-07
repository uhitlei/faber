#!/bin/bash
# =============================================================================
# board.sh — sincronização issue/labels/board Projects v2 da fábrica (zero LLM)
# ARQUITETURA §6 (board = projeção do estado), §11 (board-sync), §21-R4
# (idempotente; falha de board NÃO bloqueia o fluxo — exit 3 = aviso).
#
# Configuração (faber/config/faber.env):
#   FABER_GH=off     → tudo vira no-op silencioso (exit 0): sem GitHub, a
#                        fonte de verdade é só o state.yaml.
#   FABER_BOARD=off  → labels e comentários na issue continuam; o Projects v2
#                        não é tocado (mover só troca a label estado:*).
#   FABER_GH_REPO    → owner/repo (vazio = descoberto do remote).
#   FABER_GH_PROJECT_TITLE → título exato do Project v2 (FABER_BOARD=on).
#
# Subcomandos:
#   repo                     imprime owner/repo resolvido
#   ids                      (re)descobre os IDs do Project e grava board-ids.env
#   bootstrap-labels         cria/atualiza as labels 'faber' + 'estado:*'
#   add <issue#>             adiciona a issue ao board (no-op se já está)
#   mover <issue#> <estado>  move para a coluna do estado (§6.1, lendo
#                            _schema.colunas_board) + troca a label estado:<fino>
#   label <issue#> <estado>  só troca a label estado:<fino>
#   comentar <issue#> <msg>  comenta na issue
#   comentar-arquivo <issue#> <path>  comenta na issue com o corpo de um arquivo
#   status <issue#>          mostra coluna do board + labels atuais
#
# Exit: 0 ok · 1 uso incorreto/estado inválido · 3 falha de board/gh (não-bloqueante).
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
. "$DIR/lib/config.sh"
faber_require_install
ENV_FILE="$DIR/board-ids.env"
TEMPLATE="$DIR/../templates/state.template.yaml"

aviso() { echo "AVISO board.sh: $*" >&2; }
falha_board() { aviso "$*"; exit 3; }

cmd="${1:-}"
if [ "$FABER_GH" != "on" ]; then
  case "$cmd" in
    repo) echo "(FABER_GH=off)"; exit 0 ;;
    *) echo "board.sh $cmd: FABER_GH=off — sem GitHub, nada a sincronizar (state.yaml é a fonte de verdade)"; exit 0 ;;
  esac
fi
command -v gh >/dev/null 2>&1 || falha_board "gh CLI ausente"
REPO=$(faber_gh_repo) || falha_board "não descobri owner/repo (defina FABER_GH_REPO)"
OWNER_GH="${REPO%%/*}"
TITULO_PROJETO="$FABER_GH_PROJECT_TITLE"

yaml_to_json() {
  if python3 -c "import yaml" >/dev/null 2>&1; then
    python3 -c "import json,sys,yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))" "$1"
  elif command -v ruby >/dev/null 2>&1; then
    ruby -ryaml -rjson -e 'puts YAML.load_file(ARGV[0]).to_json' "$1"
  else
    aviso "nem python3+PyYAML nem ruby disponíveis para ler YAML (pip3 install pyyaml)"
    return 1
  fi
}

norm() {
  python3 -c "
import sys, unicodedata, re
s = unicodedata.normalize('NFKD', sys.argv[1]).encode('ascii','ignore').decode()
print(re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_').upper())
" "$1"
}

coluna_do_estado() {
  yaml_to_json "$TEMPLATE" | python3 -c "
import json, sys
estado = sys.argv[1]
schema = json.load(sys.stdin)['_schema']
if estado not in schema['states']:
    print('ESTADO_INVALIDO'); sys.exit(0)
for coluna, estados in schema['board_columns'].items():
    if estado in estados:
        print(coluna); sys.exit(0)
print('SEM_COLUNA')
" "$1"
}

carrega_ids() {
  if [ ! -f "$ENV_FILE" ]; then
    aviso "board-ids.env não existe — rodando 'ids' primeiro"
    cmd_ids || exit 3
  fi
  # shellcheck source=/dev/null
  . "$ENV_FILE"
}

item_da_issue() {
  local issue="$1" tmp
  tmp=$(mktemp) || falha_board "mktemp falhou"
  if ! gh project item-list "$BOARD_PROJECT_NUMBER" --owner "$OWNER_GH" \
       --format json --limit 500 > "$tmp" 2>/dev/null; then
    rm -f "$tmp"; falha_board "gh project item-list falhou"
  fi
  python3 -c "
import json, sys
n = int(sys.argv[2])
for it in json.load(open(sys.argv[1]))['items']:
    if (it.get('content') or {}).get('number') == n:
        print(f\"{it['id']}\t{it.get('status') or ''}\"); break
" "$tmp" "$issue"
  rm -f "$tmp"
}

cmd_ids() {
  [ -n "$TITULO_PROJETO" ] || falha_board "FABER_GH_PROJECT_TITLE vazio (FABER_BOARD=on exige o título do Project v2)"
  local tmp num pid
  tmp=$(mktemp) || falha_board "mktemp falhou"
  gh project list --owner "$OWNER_GH" --format json --limit 20 > "$tmp" 2>/dev/null \
    || falha_board "gh project list falhou (escopo 'project' concedido? gh auth refresh -s project)"
  read -r num pid < <(python3 -c "
import json, sys
for p in json.load(open(sys.argv[1]))['projects']:
    if p['title'] == sys.argv[2]:
        print(p['number'], p['id']); break
" "$tmp" "$TITULO_PROJETO")
  [ -n "${num:-}" ] || falha_board "Project '$TITULO_PROJETO' não encontrado"

  gh project field-list "$num" --owner "$OWNER_GH" --format json > "$tmp" 2>/dev/null \
    || falha_board "gh project field-list falhou"
  {
    echo "# Gerado por board.sh ids em $(date -u +%Y-%m-%dT%H:%M:%SZ) — não editar à mão"
    echo "BOARD_PROJECT_NUMBER=$num"
    echo "BOARD_PROJECT_ID=$pid"
    python3 -c "
import json, sys, unicodedata, re
def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_').upper()
for f in json.load(open(sys.argv[1]))['fields']:
    if f['name'] == 'Status':
        print(f\"BOARD_STATUS_FIELD_ID={f['id']}\")
        for o in f['options']:
            print(f\"BOARD_OPT_{norm(o['name'])}={o['id']}\")
" "$tmp"
  } > "$ENV_FILE"
  rm -f "$tmp"
  echo "IDs descobertos e gravados em $ENV_FILE:"
  cat "$ENV_FILE"
}

cmd_bootstrap_labels() {
  gh label create "faber" --repo "$REPO" --color "1D76DB" \
    --description "Gerenciada pela fábrica de software" --force >/dev/null \
    || falha_board "label faber"
  local e
  for e in intake clarification specifying refinement ready-for-dev \
           in-development developed code-review validation minha-avaliacao \
           ready-for-pr pr-open 'done' blocked cancelled; do
    gh label create "state:$e" --repo "$REPO" --color "6E7781" \
      --description "Estado fino da demanda (§6.2)" --force >/dev/null \
      || falha_board "label estado:$e"
  done
  echo "bootstrap-labels: faber + 15 estado:* ok (idempotente via --force)"
}

cmd_add() {
  local issue="$1" existente
  [ "$FABER_BOARD" = "on" ] || { echo "add: FABER_BOARD=off (só labels)"; return 0; }
  carrega_ids
  existente=$(item_da_issue "$issue")
  if [ -n "$existente" ]; then
    echo "add: issue #$issue já está no board (idempotente, nada a fazer)"
    return 0
  fi
  gh project item-add "$BOARD_PROJECT_NUMBER" --owner "$OWNER_GH" \
    --url "https://github.com/$REPO/issues/$issue" >/dev/null \
    || falha_board "item-add falhou para #$issue"
  echo "add: issue #$issue adicionada ao board"
}

cmd_label() {
  local issue="$1" estado="$2" atuais remover flags=()
  atuais=$(gh issue view "$issue" --repo "$REPO" --json labels \
    --jq '.labels[].name' 2>/dev/null) || falha_board "issue view falhou para #$issue"
  remover=$(printf '%s\n' "$atuais" | grep '^state:' | grep -v "^state:$estado$" || true)
  while IFS= read -r l; do [ -n "$l" ] && flags+=(--remove-label "$l"); done <<< "$remover"
  if printf '%s\n' "$atuais" | grep -q "^state:$estado$" && [ ${#flags[@]} -eq 0 ]; then
    echo "label: #$issue já tem estado:$estado (idempotente, nada a fazer)"
    return 0
  fi
  gh issue edit "$issue" --repo "$REPO" --add-label "state:$estado" \
    ${flags[@]+"${flags[@]}"} >/dev/null \
    || falha_board "issue edit (labels) falhou para #$issue — labels existem? (board.sh bootstrap-labels)"
  echo "label: #$issue -> estado:$estado"
}

cmd_mover() {
  local issue="$1" estado="$2" coluna chave opt linha item_id status_atual
  coluna=$(coluna_do_estado "$estado")
  [ -n "$coluna" ] || falha_board "não foi possível ler _schema.colunas_board (python3+PyYAML ou ruby necessários)"
  case "$coluna" in
    ESTADO_INVALIDO) echo "ERRO: estado '$estado' não existe no _schema (§6.2)"; exit 1 ;;
    SEM_COLUNA) echo "mover: estado '$estado' não tem coluna (issue é fechada; §6.2)"; cmd_label "$issue" "$estado"; return 0 ;;
  esac
  if [ "$FABER_BOARD" != "on" ]; then
    cmd_label "$issue" "$estado"; return 0
  fi
  carrega_ids
  chave="BOARD_OPT_$(norm "$coluna")"
  opt="${!chave:-}"
  [ -n "$opt" ] || falha_board "option id ausente para coluna '$coluna' — o campo Status do Project precisa ter essa opção; rode 'board.sh ids'"

  linha=$(item_da_issue "$issue")
  if [ -z "$linha" ]; then
    cmd_add "$issue"
    linha=$(item_da_issue "$issue")
    [ -n "$linha" ] || falha_board "issue #$issue não apareceu no board após add"
  fi
  item_id="${linha%%$'\t'*}"
  status_atual="${linha#*$'\t'}"

  if [ "$status_atual" = "$coluna" ]; then
    echo "mover: #$issue já está em '$coluna' (idempotente, nada a fazer)"
  else
    gh project item-edit --id "$item_id" --project-id "$BOARD_PROJECT_ID" \
      --field-id "$BOARD_STATUS_FIELD_ID" --single-select-option-id "$opt" >/dev/null \
      || falha_board "item-edit falhou para #$issue"
    echo "mover: #$issue '${status_atual:-—}' -> '$coluna' (estado: $estado)"
  fi
  cmd_label "$issue" "$estado"
}

cmd_comentar() {
  local issue="$1"; shift
  gh issue comment "$issue" --repo "$REPO" --body "$*" >/dev/null \
    || falha_board "comentário falhou para #$issue"
  echo "comentar: #$issue ok"
}

cmd_comentar_arquivo() {
  local issue="$1" arquivo="$2"
  [ -s "$arquivo" ] || falha_board "arquivo '$arquivo' inexistente ou vazio"
  gh issue comment "$issue" --repo "$REPO" --body-file "$arquivo" >/dev/null \
    || falha_board "comentário (arquivo) falhou para #$issue"
  echo "comentar-arquivo: #$issue ok ($arquivo)"
}

cmd_status() {
  local issue="$1" linha st
  echo "issue: #$issue"
  if [ "$FABER_BOARD" = "on" ]; then
    carrega_ids
    linha=$(item_da_issue "$issue")
    if [ -z "$linha" ]; then echo "board: fora do board"
    else st="${linha#*$'\t'}"; echo "board: ${st:-(sem status)}"; fi
  else
    echo "board: (FABER_BOARD=off)"
  fi
  echo "labels: $(gh issue view "$issue" --repo "$REPO" --json labels --jq '[.labels[].name] | join(", ")' 2>/dev/null)"
}

case "$cmd" in
  repo)             echo "$REPO" ;;
  ids)              cmd_ids ;;
  bootstrap-labels) cmd_bootstrap_labels ;;
  add)      [ $# -ge 2 ] || { echo "uso: board.sh add <issue#>"; exit 1; }; cmd_add "$2" ;;
  mover)    [ $# -ge 3 ] || { echo "uso: board.sh mover <issue#> <estado>"; exit 1; }; cmd_mover "$2" "$3" ;;
  label)    [ $# -ge 3 ] || { echo "uso: board.sh label <issue#> <estado>"; exit 1; }; cmd_label "$2" "$3" ;;
  comentar) [ $# -ge 3 ] || { echo "uso: board.sh comentar <issue#> <msg>"; exit 1; }; issue="$2"; shift 2; cmd_comentar "$issue" "$@" ;;
  comentar-arquivo) [ $# -ge 3 ] || { echo "uso: board.sh comentar-arquivo <issue#> <path>"; exit 1; }; cmd_comentar_arquivo "$2" "$3" ;;
  status)   [ $# -ge 2 ] || { echo "uso: board.sh status <issue#>"; exit 1; }; cmd_status "$2" ;;
  *) echo "uso: board.sh {repo|ids|bootstrap-labels|add|mover|label|comentar|comentar-arquivo|status} ..."; exit 1 ;;
esac
