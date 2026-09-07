#!/bin/bash
# =============================================================================
# install.sh — instala a Fábrica de Software com Agentes num repositório.
#
# O instalador NÃO usa LLM. Ele: (1) detecta o contexto do repositório-alvo
# (código existente · specs no formato Spec Kit · PRD/BRD · brainstorm · empty),
# (2) pergunta o essencial (nome, aprovador humano, branches e — sempre — o
# modo de interação: só nos gates de validação ou passo a passo), (3) copia a
# fábrica (CLAUDE.md, .claude/, faber/, specs/ skeleton), (4) renderiza os
# placeholders @@FABER_*@@ e grava faber/config/faber.env, (5) escreve
# faber/bootstrap/CONTEXT.md com o modo detectado e (6) deixa a branch
# faber/bootstrap pronta para o comando /faber-init concluir o bootstrap
# dentro do Claude Code.
#
# Uso:
#   ./install.sh [<dir-do-repo>] [opções]
#     --mode <existing-repo|spec-kit|prd|brainstorm|discovery|empty>   força o modo
#     --interaction <gates|step-by-step>   pula a pergunta do modo de interação
#     --lang <en|pt-BR>   idioma dos prompts (agentes/comandos/skills) e de
#                         FABER_LANG; o contrato de máquina é inglês nos dois
#     --project "<nome>"  --owner <slug>  --owner-name "<Nome>"
#     --trunk <branch>    --main <branch>  --specs-dir <dir>
#     --gh <on|off>  --board <on|off>  --dashboard <on|off>
#     --profile <generic|node-web|node-supabase|python|/caminho.env>
#     --prd-guide <arquivo.md>   seu guia de PRD/BRD (vira faber/templates/prd-brd-guide.md)
#     --labels                  cria as labels 'faber' e 'state:*' no GitHub (gh)
#     --yes                     aceita todos os defaults sem perguntar (exceto o
#                               que vier por flag); exige --interaction
#     --dry-run                 só mostra o plano
#     --force                  sobrescreve arquivos da fábrica já existentes
#
# Requisitos: bash ≥ 3.2 · git · python3 (PyYAML recomendado) · gh (se --gh on).
# Exit: 0 ok · 1 uso/pré-requisito · 2 falha ao escrever/git.
# =============================================================================
set -u

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIT_SRC="$KIT_DIR/kit"
VERSAO="$(cat "$KIT_DIR/VERSION" 2>/dev/null || echo dev)"

ALVO=""; MODE=""; INTERACAO=""; LANG_PACK=""; PROJETO=""; OWNER=""; OWNER_NOME=""; TRUNK=""; MAIN=""
SPECS_DIR=""; GH=""; BOARD=""; DASHBOARD=""; PERFIL=""; GUIA_PRD=""; LABELS=0; SIM=0; DRY=0; FORCAR=0

uso() { sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
erro() { echo "ERRO: $*" >&2; exit "${2:-1}"; }
info() { echo "→ $*"; }
ok()   { echo "✔ $*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)       MODE="${2:?}"; shift 2 ;;
    --interaction)  INTERACAO="${2:?}"; shift 2 ;;
    --lang)       LANG_PACK="${2:?}"; shift 2 ;;
    --project)    PROJETO="${2:?}"; shift 2 ;;
    --owner)      OWNER="${2:?}"; shift 2 ;;
    --owner-name) OWNER_NOME="${2:?}"; shift 2 ;;
    --trunk)      TRUNK="${2:?}"; shift 2 ;;
    --main)       MAIN="${2:?}"; shift 2 ;;
    --specs-dir)  SPECS_DIR="${2:?}"; shift 2 ;;
    --gh)         GH="${2:?}"; shift 2 ;;
    --board)      BOARD="${2:?}"; shift 2 ;;
    --dashboard)  DASHBOARD="${2:?}"; shift 2 ;;
    --profile)     PERFIL="${2:?}"; shift 2 ;;
    --prd-guide)   GUIA_PRD="${2:?}"; shift 2 ;;
    --labels)     LABELS=1; shift ;;
    --yes|--sim)  SIM=1; shift ;;
    --dry-run)    DRY=1; shift ;;
    --force)     FORCAR=1; shift ;;
    -h|--help)    uso ;;
    -*)           echo "opção desconhecida: $1"; uso ;;
    *)            [ -z "$ALVO" ] || uso; ALVO="$1"; shift ;;
  esac
done
ALVO="${ALVO:-$(pwd)}"
[ -d "$KIT_SRC/shared" ] || erro "kit/shared não encontrado ao lado de install.sh ($KIT_SRC)"
mkdir -p "$ALVO" 2>/dev/null || erro "não consegui criar/acessar $ALVO"
ALVO="$(cd "$ALVO" && pwd)"

# ── 0. pré-requisitos ──────────────────────────────────────────────────────
command -v git >/dev/null 2>&1 || erro "git ausente"
command -v python3 >/dev/null 2>&1 || erro "python3 ausente (os scripts e hooks da fábrica dependem dele)"
PYYAML=1; python3 -c "import yaml" >/dev/null 2>&1 || PYYAML=0
TEM_GH=1; command -v gh >/dev/null 2>&1 || TEM_GH=0

echo "🏭 Fábrica de Software com Agentes — instalador v$VERSAO"
echo "   alvo: $ALVO"
[ "$PYYAML" -eq 1 ] || echo "   AVISO: PyYAML ausente — instale com: pip3 install pyyaml (gate-check/board/hooks precisam dele)"
[ "$TEM_GH" -eq 1 ] || echo "   AVISO: gh CLI ausente — sem GitHub, use --gh off (IDs de demanda por contador local)"

# ── 1. estado do repositório ───────────────────────────────────────────────
cd "$ALVO" || exit 2
E_GIT=0; git rev-parse --is-inside-work-tree >/dev/null 2>&1 && E_GIT=1
N_COMMITS=0; [ "$E_GIT" -eq 1 ] && N_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo 0)
BRANCH_ATUAL=""; [ "$E_GIT" -eq 1 ] && BRANCH_ATUAL=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
TREE_SUJO=0; [ "$E_GIT" -eq 1 ] && [ -n "$(git status --porcelain 2>/dev/null)" ] && TREE_SUJO=1
JA_INSTALADA=0; [ -f "faber/config/faber.env" ] && JA_INSTALADA=1

# ── 2. detecção de contexto ────────────────────────────────────────────────
PRUNE='-name node_modules -o -name .git -o -name dist -o -name build -o -name vendor -o -name .venv -o -name venv -o -name target -o -name .claude -o -name faber -o -name __pycache__ -o -name coverage'
conta_codigo() {
  # shellcheck disable=SC2086
  find . \( $PRUNE \) -prune -o -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.php' -o -name '*.cs' -o -name '*.swift' -o -name '*.dart' -o -name '*.c' -o -name '*.cpp' -o -name '*.sql' -o -name '*.vue' -o -name '*.svelte' \) -print 2>/dev/null | wc -l | tr -d ' '
}
N_CODIGO=$(conta_codigo)
MANIFESTOS=$(ls -1 package.json pyproject.toml requirements.txt go.mod Cargo.toml pom.xml build.gradle composer.json Gemfile Makefile 2>/dev/null | tr '\n' ' ')
ls -1 -- *.csproj *.sln >/dev/null 2>&1 && MANIFESTOS="$MANIFESTOS $(ls -1 -- *.csproj *.sln 2>/dev/null | tr '\n' ' ')"

SK_SINAIS=""
[ -d ".specify" ] && SK_SINAIS="$SK_SINAIS .specify/"
[ -f "memory/constitution.md" ] && SK_SINAIS="$SK_SINAIS memory/constitution.md"
[ -f ".specify/memory/constitution.md" ] && SK_SINAIS="$SK_SINAIS .specify/memory/constitution.md"
SK_SPECS=$(ls -1d specs/*/spec.md 2>/dev/null | tr '\n' ' ')
[ -n "$SK_SPECS" ] && SK_SINAIS="$SK_SINAIS $SK_SPECS"

acha_docs() {  # acha_docs <padrões find -iname separados por |>
  local pats="$1" p out=""
  IFS='|' read -r -a arr <<< "$pats"
  for p in "${arr[@]}"; do
    out="$out $(find . -maxdepth 2 \( -path ./node_modules -o -path ./.git -o -path ./faber \) -prune -o -type f -iname "$p" -print 2>/dev/null | tr '\n' ' ')"
  done
  echo "$out" | tr -s ' '
}
PRD_DOCS=$(acha_docs 'PRD*.md|BRD*.md|prd.md|brd.md|requisitos*.md|requirements*.md')
BRAIN_DOCS=$(acha_docs '*brainstorm*.md|ideias.md|ideas.md|braindump.md|brain-dump.md|notas.md|notes.md')

if [ -z "$MODE" ]; then
  if [ "$N_CODIGO" -ge 10 ] && { [ -n "$MANIFESTOS" ] || [ "$N_COMMITS" -ge 3 ]; }; then MODE="existing-repo"
  elif [ -n "$SK_SINAIS" ]; then MODE="spec-kit"
  elif [ -n "$(echo "$PRD_DOCS" | tr -d ' ')" ]; then MODE="prd"
  elif [ -n "$(echo "$BRAIN_DOCS" | tr -d ' ')" ]; then MODE="brainstorm"
  else MODE="empty"; fi
fi
case "$MODE" in existing-repo|spec-kit|prd|brainstorm|discovery|empty) ;; *) erro "--mode inválido: $MODE" ;; esac

echo
echo "── Contexto detectado ──────────────────────────────────────────────"
echo "   git: $([ "$E_GIT" -eq 1 ] && echo "sim ($N_COMMITS commits, branch ${BRANCH_ATUAL:-detached})" || echo "não (será inicializado)")"
echo "   arquivos de código: $N_CODIGO · manifestos: ${MANIFESTOS:-nenhum}"
echo "   spec-kit: ${SK_SINAIS:-não}"
echo "   PRD/BRD: $( [ -n "$(echo "$PRD_DOCS" | tr -d ' ')" ] && echo "$PRD_DOCS" || echo "não")"
echo "   brainstorm: $( [ -n "$(echo "$BRAIN_DOCS" | tr -d ' ')" ] && echo "$BRAIN_DOCS" || echo "não")"
echo "   ⇒ modo de bootstrap: $MODE"
[ "$JA_INSTALADA" -eq 1 ] && echo "   AVISO: faber/config/faber.env já existe — a fábrica já foi instalada aqui (use --force para sobrescrever os arquivos do kit; o faber.env atual é preservado)"
echo

# ── 3. defaults inteligentes ───────────────────────────────────────────────
slug() { python3 -c "import re,sys,unicodedata; s=unicodedata.normalize('NFKD',sys.argv[1]).encode('ascii','ignore').decode().lower(); print(re.sub(r'[^a-z0-9]+','-',s).strip('-') or 'owner')" "$1"; }
D_PROJETO="$(basename "$ALVO")"
D_OWNER_NOME="$(git config user.name 2>/dev/null || echo "")"; D_OWNER_NOME="${D_OWNER_NOME:-Owner}"
D_MAIN="main"; D_TRUNK="develop"
if [ "$E_GIT" -eq 1 ]; then
  for b in main master; do git show-ref --verify --quiet "refs/heads/$b" && { D_MAIN="$b"; break; }; done
  ACHOU=0
  for b in develop Develop dev development staging; do git show-ref --verify --quiet "refs/heads/$b" && { D_TRUNK="$b"; ACHOU=1; break; }; done
  [ "$ACHOU" -eq 0 ] && [ "$N_COMMITS" -gt 0 ] && D_TRUNK="$D_MAIN"   # repo sem branch de integração: trunk único
fi
D_GH="on"; [ "$TEM_GH" -eq 1 ] || D_GH="off"
D_SPECS="specs"
if [ -d "specs" ] && [ -n "$SK_SPECS" ]; then D_SPECS="docs/specs"; fi   # não misturar com o Spec Kit
# comandos de validação a partir do manifesto
D_LINT="make lint"; D_BUILD="make build"; D_TEST="make test"
if [ -f package.json ]; then
  PM="npm"; [ -f pnpm-lock.yaml ] && PM="pnpm"; [ -f yarn.lock ] && PM="yarn"; [ -f bun.lockb ] || [ -f bun.lock ] && PM="bun"
  tem_script() { python3 -c "import json,sys; print('1' if sys.argv[1] in (json.load(open('package.json')).get('scripts') or {}) else '0')" "$1" 2>/dev/null || echo 0; }
  [ "$(tem_script lint)" = "1" ] && D_LINT="$PM run lint" || D_LINT="$PM run lint  # (script não encontrado — ajuste)"
  [ "$(tem_script build)" = "1" ] && D_BUILD="$PM run build" || D_BUILD="$PM run build  # (script não encontrado — ajuste)"
  if [ "$(tem_script test:run)" = "1" ]; then D_TEST="$PM run test:run"; elif [ "$(tem_script test)" = "1" ]; then D_TEST="$PM test"; else D_TEST="$PM test  # (script não encontrado — ajuste)"; fi
elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  D_LINT="ruff check ."; D_BUILD="python -m compileall -q ."; D_TEST="pytest -q"
elif [ -f go.mod ]; then D_LINT="go vet ./..."; D_BUILD="go build ./..."; D_TEST="go test ./..."
elif [ -f Cargo.toml ]; then D_LINT="cargo clippy -- -D warnings"; D_BUILD="cargo build"; D_TEST="cargo test"
fi
D_E2E="off"; D_CMD_E2E="npx playwright test --workers=1"
{ [ -f playwright.config.ts ] || [ -f playwright.config.js ]; } && D_E2E="on"
{ [ -f cypress.config.ts ] || [ -f cypress.config.js ]; } && { D_E2E="on"; D_CMD_E2E="npx cypress run"; }
D_MIG=""; for d in supabase/migrations db/migrations migrations prisma/migrations database/migrations alembic/versions; do [ -d "$d" ] && { D_MIG="$d"; break; }; done
D_MIG_CHECKS=""; [ "$D_MIG" = "supabase/migrations" ] && D_MIG_CHECKS="grant ,enable row level security,create policy,set search_path"
D_SECRETS=".env,.env.local"; ls -1 .env.* >/dev/null 2>&1 && D_SECRETS="$(printf '.env,.env.local'; for f in .env.*; do case "$f" in *.example|*.sample|*.template) ;; .env.local) ;; *) printf ',%s' "$f" ;; esac; done)"

# ── 4. perguntas ───────────────────────────────────────────────────────────
pergunta() {  # pergunta <var> <texto> <default>
  local var="$1" texto="$2" def="$3" resp
  if [ "$SIM" -eq 1 ] || [ ! -t 0 ]; then eval "$var=\"\$def\""; return; fi
  printf '%s [%s]: ' "$texto" "$def"
  # shellcheck disable=SC2034  # resp e lido indiretamente pelo eval abaixo
  read -r resp
  eval "$var=\"\${resp:-\$def}\""
}
[ -n "$PROJETO" ]    || pergunta PROJETO "Nome do projeto" "$D_PROJETO"
[ -n "$OWNER_NOME" ] || pergunta OWNER_NOME "Nome do aprovador humano (gates G1/G6/G8)" "$D_OWNER_NOME"
[ -n "$OWNER" ]      || pergunta OWNER "Slug do aprovador (minúsculas, sem espaço — usado em --by <slug>)" "$(slug "$OWNER_NOME")"
OWNER="$(slug "$OWNER")"
[ -n "$MAIN" ]       || pergunta MAIN "Branch de produção" "$D_MAIN"
[ -n "$TRUNK" ]      || pergunta TRUNK "Branch de integração (PRs das demandas apontam para ela; pode ser igual à de produção)" "$D_TRUNK"
if [ -z "$INTERACAO" ]; then
  if [ "$SIM" -eq 1 ] || [ ! -t 0 ]; then
    erro "o modo de interação é obrigatório: passe --interaction gates|step-by-step (com --yes não há prompt)"
  fi
  echo
  echo "Como você quer interagir com a fábrica?"
  echo "  1) Só nos gates de validação — o CTO encadeia o fluxo sozinho e para apenas em"
  echo "     G1 (Ready for Dev), G6 (sua avaliação), G8 (merge) e dúvidas críticas. [recomendado]"
  echo "  2) Passo a passo — o CTO para ao fim de cada comando/fase e pede ok."
  printf 'Escolha [1]: '; read -r R; case "${R:-1}" in 2) INTERACAO="step-by-step" ;; *) INTERACAO="gates" ;; esac
fi
case "$INTERACAO" in gates|step-by-step) ;; *) erro "--interaction inválido: $INTERACAO (gates|step-by-step)" ;; esac
if [ -z "$LANG_PACK" ]; then
  if [ "$SIM" -eq 1 ] || [ ! -t 0 ]; then
    LANG_PACK="en"
  else
    echo
    echo "Em que idioma os agentes devem trabalhar / In which language should the agents work?"
    echo "  1) English  — prompts, specs, issues and handoffs in English"
    echo "  2) Português — prompts, specs, issues e handoffs em português"
    echo "  (o state.yaml e os nomes de comando são inglês nos dois casos)"
    printf 'Escolha / Choose [1]: '; read -r R; case "${R:-1}" in 2) LANG_PACK="pt-BR" ;; *) LANG_PACK="en" ;; esac
  fi
fi
case "$LANG_PACK" in en|pt-BR) ;; *) erro "--lang inválido: $LANG_PACK (en|pt-BR)" ;; esac
[ -d "$KIT_SRC/lang/$LANG_PACK" ] || erro "pacote de idioma ausente: kit/lang/$LANG_PACK"
[ -n "$GH" ]        || pergunta GH "Usar GitHub Issues (ID da demanda = número da issue)? on/off" "$D_GH"
[ "$GH" = "on" ] && [ "$TEM_GH" -eq 0 ] && { echo "   AVISO: gh ausente — FABER_GH ficará on, mas new-task.sh vai falhar até você instalar/autenticar o gh"; }
if [ "$GH" = "on" ]; then [ -n "$BOARD" ] || pergunta BOARD "Sincronizar board GitHub Projects v2? on/off" "off"; else BOARD="off"; fi
PROJ_TITULO=""; [ "$BOARD" = "on" ] && pergunta PROJ_TITULO "Título exato do Project v2" "$PROJETO"
[ -n "$DASHBOARD" ] || pergunta DASHBOARD "Instalar o dashboard local (Kanban Flask, opcional)? on/off" "off"
[ -n "$SPECS_DIR" ] || pergunta SPECS_DIR "Pasta canônica de specs" "$D_SPECS"
SPECS_DIR="${SPECS_DIR%/}"
if [ -z "$PERFIL" ] && [ "$SIM" -eq 0 ] && [ -t 0 ]; then
  pergunta PERFIL "Perfil de configuração (generic|node-web|node-supabase|python|nenhum)" "nenhum"
fi
[ "$PERFIL" = "nenhum" ] && PERFIL=""
GH_REPO=""
if [ "$GH" = "on" ] && [ "$E_GIT" -eq 1 ]; then
  url=$(git remote get-url origin 2>/dev/null || true); url="${url%.git}"
  case "$url" in git@*:*) GH_REPO="${url#*:}" ;; http*://*) GH_REPO=$(echo "$url" | sed -E 's#^https?://[^/]+/##') ;; esac
fi

echo
echo "── Plano ────────────────────────────────────────────────────────────"
echo "   projeto=$PROJETO · owner=$OWNER_NOME ($OWNER) · trunk=$TRUNK · main=$MAIN"
echo "   idioma=$LANG_PACK · interação=$INTERACAO · gh=$GH${GH_REPO:+ ($GH_REPO)} · board=$BOARD · dashboard=$DASHBOARD · specs=$SPECS_DIR/"
echo "   lint='$D_LINT' · build='$D_BUILD' · test='$D_TEST' · e2e=$D_E2E · migrations='${D_MIG:-—}' · perfil=${PERFIL:-—}"
echo "   modo de bootstrap=$MODE → depois: claude → /faber-init"
[ "$DRY" -eq 1 ] && { echo "(dry-run: nada foi escrito)"; exit 0; }
echo

# ── 5. cópia dos arquivos ──────────────────────────────────────────────────
copia() {  # copia <origem-relativa-ao-kit> <destino-relativo-ao-alvo>
  local src="$KIT_SRC/$1" dst="$ALVO/$2"
  if [ -e "$dst" ] && [ "$FORCAR" -eq 0 ]; then
    if ! cmp -s "$src" "$dst"; then echo "   mantido (já existe, difere do kit — use --force): $2"; fi
    return 0
  fi
  mkdir -p "$(dirname "$dst")" && cp "$src" "$dst" || erro "falha ao copiar $2" 2
}
info "copiando a fábrica"
# Duas camadas: shared/ (código e contrato de máquina, uma cópia só) e
# lang/<pack>/ (a prosa). O contrato é idêntico nos dois idiomas de propósito —
# um state.yaml por idioma faria scripts, board e dashboard falarem dois dialetos.
for BASE in shared "lang/$LANG_PACK"; do
  ( cd "$KIT_SRC/$BASE" && find .claude faber -type f ! -path './faber/dashboard/*' ! -name '.DS_Store' ! -path '*/__pycache__/*' ! -name '*.pyc' 2>/dev/null ) | while IFS= read -r f; do
    f="${f#./}"; copia "$BASE/$f" "$f"
  done
done
if [ "$DASHBOARD" = "on" ]; then
  ( cd "$KIT_SRC/shared" && find faber/dashboard -type f ! -name '.DS_Store' ! -path '*/__pycache__/*' ! -name '*.pyc' ) | while IFS= read -r f; do copia "shared/$f" "$f"; done
fi
mkdir -p "$ALVO/faber/tasks" "$ALVO/faber/bootstrap/evidence"; touch "$ALVO/faber/tasks/.gitkeep" "$ALVO/faber/bootstrap/evidence/.gitkeep"
chmod +x "$ALVO"/faber/scripts/*.sh "$ALVO"/faber/scripts/lib/*.sh "$ALVO"/.claude/hooks/*.sh 2>/dev/null
[ -f "$ALVO/faber/dashboard/dashboard.sh" ] && chmod +x "$ALVO/faber/dashboard/dashboard.sh"

# CLAUDE.md: preserva regras do projeto, se já houver
if [ -f "$ALVO/CLAUDE.md" ] && ! grep -q "Constituição do CTO" "$ALVO/CLAUDE.md"; then
  cp "$ALVO/CLAUDE.md" "$ALVO/CLAUDE.md.bak-faber"
  { cat "$KIT_SRC/lang/$LANG_PACK/CLAUDE.md"; echo; echo "## 9. Regras herdadas do CLAUDE.md anterior (preservadas na instalação)"; echo; cat "$ALVO/CLAUDE.md.bak-faber"; } > "$ALVO/CLAUDE.md"
  ok "CLAUDE.md anterior preservado como seção 9 (backup em CLAUDE.md.bak-faber)"
elif [ ! -f "$ALVO/CLAUDE.md" ] || [ "$FORCAR" -eq 1 ]; then
  cp "$KIT_SRC/lang/$LANG_PACK/CLAUDE.md" "$ALVO/CLAUDE.md"
fi

# settings.json: mescla permissões e hooks se já existir um
if [ -f "$ALVO/.claude/settings.json" ] && ! cmp -s "$KIT_SRC/shared/.claude/settings.json" "$ALVO/.claude/settings.json"; then
  python3 - "$KIT_SRC/shared/.claude/settings.json" "$ALVO/.claude/settings.json" <<'PY' || erro "falha ao mesclar .claude/settings.json" 2
import json, sys
kit = json.load(open(sys.argv[1])); cur = json.load(open(sys.argv[2]))
perm = cur.setdefault("permissions", {})
for k in ("allow", "deny"):
    have = perm.setdefault(k, [])
    for item in kit["permissions"].get(k, []):
        if item not in have: have.append(item)
hooks = cur.setdefault("hooks", {})
for ev, lst in kit["hooks"].items():
    have = hooks.setdefault(ev, [])
    for h in lst:
        if h not in have: have.append(h)
json.dump(cur, open(sys.argv[2], "w"), indent=2, ensure_ascii=False); open(sys.argv[2], "a").write("\n")
PY
  ok ".claude/settings.json mesclado (permissões e hooks da fábrica adicionados)"
fi

# perfil
PERFIL_ARQ=""
if [ -n "$PERFIL" ]; then
  if [ -f "$PERFIL" ]; then PERFIL_ARQ="$PERFIL"; elif [ -f "$KIT_DIR/profiles/$PERFIL.env" ]; then PERFIL_ARQ="$KIT_DIR/profiles/$PERFIL.env"; else erro "perfil não encontrado: $PERFIL"; fi
fi

# ── 6. faber.env ─────────────────────────────────────────────────────────
ENV_OUT="$ALVO/faber/config/faber.env"
if [ -f "$ENV_OUT" ] && [ "$FORCAR" -eq 0 ]; then
  echo "   mantido: faber/config/faber.env (já existia)"
else
  info "gravando faber/config/faber.env"
  python3 - "$KIT_SRC/shared/faber/config/faber.env.example" "$ENV_OUT" "$PERFIL_ARQ" <<PY || erro "falha ao gerar faber.env" 2
import re, sys
tpl = open(sys.argv[1], encoding="utf-8").read()
valores = {
 "FABER_PROJECT": """$PROJETO""", "FABER_OWNER": "$OWNER", "FABER_OWNER_NAME": """$OWNER_NOME""",
 "FABER_TRUNK": "$TRUNK", "FABER_MAIN": "$MAIN", "FABER_INTERACTION": "$INTERACAO",
 "FABER_GH": "$GH", "FABER_GH_REPO": "$GH_REPO", "FABER_BOARD": "$BOARD", "FABER_GH_PROJECT_TITLE": """$PROJ_TITULO""",
 "FABER_SPECS_DIR": "$SPECS_DIR", "FABER_LANG": "$LANG_PACK", "FABER_CMD_LINT": """$D_LINT""", "FABER_CMD_BUILD": """$D_BUILD""", "FABER_CMD_TEST": """$D_TEST""",
 "FABER_E2E": "$D_E2E", "FABER_CMD_E2E": """$D_CMD_E2E""", "FABER_MIGRATIONS_DIR": "$D_MIG", "FABER_MIGRATION_CHECKS": """$D_MIG_CHECKS""",
 "FABER_SECRET_FILES": "$D_SECRETS", "FABER_DASHBOARD": "$DASHBOARD",
}
# perfil por cima dos defaults detectados (flags/perguntas já estão em 'valores'
# e prevalecem sobre o perfil apenas nas chaves de identidade/branches/interação)
identidade = {"FABER_PROJECT","FABER_OWNER","FABER_OWNER_NAME","FABER_TRUNK","FABER_MAIN","FABER_INTERACTION","FABER_GH","FABER_GH_REPO","FABER_BOARD","FABER_GH_PROJECT_TITLE","FABER_SPECS_DIR","FABER_DASHBOARD","FABER_LANG"}
if sys.argv[3]:
    for linha in open(sys.argv[3], encoding="utf-8"):
        m = re.match(r'^\s*([A-Z0-9_]+)\s*=\s*"(.*)"\s*(#.*)?$', linha.rstrip("\n"))
        if m and m.group(1) not in identidade:
            valores[m.group(1)] = m.group(2)
out = []
for linha in tpl.splitlines():
    m = re.match(r'^([A-Z0-9_]+)="(.*?)"(\s*#.*)?$', linha)
    if m and m.group(1) in valores:
        v = valores[m.group(1)].replace('"', '\\\\"')
        out.append('%s="%s"%s' % (m.group(1), v, m.group(3) or ""))
    else:
        out.append(linha)
open(sys.argv[2], "w", encoding="utf-8").write("\n".join(out) + "\n")
PY
fi

# guia de PRD/BRD do usuário
if [ -n "$GUIA_PRD" ]; then
  [ -f "$GUIA_PRD" ] || erro "--prd-guide: arquivo não encontrado: $GUIA_PRD"
  cp "$GUIA_PRD" "$ALVO/faber/templates/prd-brd-guide.md" && ok "guia de PRD/BRD instalado em faber/templates/prd-brd-guide.md"
fi

# ── 7. specs/ skeleton (só se não existir) ─────────────────────────────────
if [ ! -d "$ALVO/$SPECS_DIR/global" ]; then
  info "criando $SPECS_DIR/ (README + globais 00–08 como esqueleto)"
  mkdir -p "$ALVO/$SPECS_DIR/global" "$ALVO/$SPECS_DIR/features" "$ALVO/$SPECS_DIR/assets/diagrams"
  for f in "$KIT_SRC/lang/$LANG_PACK"/faber/templates/specs-global/*.md; do
    b="$(basename "$f")"
    if [ "$b" = "README.md" ]; then [ -e "$ALVO/$SPECS_DIR/README.md" ] || cp "$f" "$ALVO/$SPECS_DIR/README.md"
    else cp "$f" "$ALVO/$SPECS_DIR/global/$b"; fi
  done
  touch "$ALVO/$SPECS_DIR/features/.gitkeep" "$ALVO/$SPECS_DIR/assets/diagrams/.gitkeep"
else
  echo "   mantido: $SPECS_DIR/global já existe (o /faber-init consolida sobre o que houver)"
fi

# ── 8. renderização dos placeholders ───────────────────────────────────────
info "renderizando placeholders @@FABER_*@@"
python3 - "$ALVO" "$SPECS_DIR" <<PY || erro "falha na renderização" 2
import os, re, sys
alvo, specs = sys.argv[1], sys.argv[2]
val = {
 "FABER_PROJECT": """$PROJETO""", "FABER_OWNER": "$OWNER", "FABER_OWNER_NAME": """$OWNER_NOME""",
 "FABER_TRUNK": "$TRUNK", "FABER_MAIN": "$MAIN", "FABER_INTERACTION": "$INTERACAO", "FABER_SPECS_DIR": specs,
 "FABER_CMD_LINT": """$D_LINT""".split("  #")[0].strip(), "FABER_CMD_BUILD": """$D_BUILD""".split("  #")[0].strip(),
 "FABER_CMD_TEST": """$D_TEST""".split("  #")[0].strip(), "FABER_CMD_E2E": """$D_CMD_E2E""",
 "FABER_MIGRATIONS_DIR": "$D_MIG" or "<migrations>", "FABER_GH_REPO": "$GH_REPO",
}
rx = re.compile(r"@@(FABER_[A-Z0-9_]+)@@")
raizes = [os.path.join(alvo, "CLAUDE.md"), os.path.join(alvo, ".claude"), os.path.join(alvo, "faber"), os.path.join(alvo, specs)]
n = 0
for raiz in raizes:
    paths = [raiz] if os.path.isfile(raiz) else [os.path.join(dp, f) for dp, _, fs in os.walk(raiz) for f in fs]
    for p in paths:
        if not p.endswith((".md", ".yaml", ".yml", ".json")) or "/tasks/" in p or "/dashboard/" in p:
            continue
        try: t = open(p, encoding="utf-8").read()
        except Exception: continue
        if "@@FABER_" not in t: continue
        novo = rx.sub(lambda m: val.get(m.group(1), m.group(0)), t)
        if novo != t:
            open(p, "w", encoding="utf-8").write(novo); n += 1
print("   arquivos renderizados:", n)
PY

# ── 9. .gitignore ──────────────────────────────────────────────────────────
GI="$ALVO/.gitignore"; touch "$GI"
add_gi() { grep -qxF "$1" "$GI" || echo "$1" >> "$GI"; }
grep -q "Fábrica:" "$GI" || printf '\n# Fábrica: worktrees de demanda (checkouts descartáveis do /faber-resume)\n' >> "$GI"
add_gi ".claude/worktrees/"
add_gi "faber/dashboard/.venv/"
add_gi "faber/dashboard/dados/"
add_gi ".scannerwork/"
add_gi "__pycache__/"
grep -qxF "*.log" "$GI" && add_gi "!faber/tasks/**/evidence/*.log"
grep -qxF "*.log" "$GI" && add_gi "!faber/bootstrap/evidence/*.log"

# ── 10. CONTEXT.md do bootstrap ───────────────────────────────────────────
info "gravando faber/bootstrap/CONTEXT.md (modo: $MODE)"
cat > "$ALVO/faber/bootstrap/CONTEXT.md" <<EOF
# Contexto do bootstrap — escrito por install.sh em $(date +%Y-%m-%dT%H:%M:%S%z)

\`\`\`yaml
status: pending             # /faber-init muda para 'done'
modo: $MODE
interacao: $INTERACAO
kit_versao: $VERSAO
projeto: "$PROJETO"
owner: $OWNER
trunk: $TRUNK
main: $MAIN
specs_dir: $SPECS_DIR
sinais:
  codigo_arquivos: $N_CODIGO
  manifestos: "${MANIFESTOS:-}"
  git_commits: $N_COMMITS
  spec_kit: "${SK_SINAIS:-}"
  prd_brd: "$(echo "$PRD_DOCS" | tr -s ' ' | sed 's/^ //;s/ $//')"
  brainstorm: "$(echo "$BRAIN_DOCS" | tr -s ' ' | sed 's/^ //;s/ $//')"
arquivos_de_entrada:
$( for f in $SK_SINAIS $PRD_DOCS $BRAIN_DOCS; do echo "  - $f"; done )
guia_prd_brd: faber/templates/prd-brd-guide.md$( [ -n "$GUIA_PRD" ] && echo "   # fornecido pelo Owner" || echo "   # padrão do kit (substitua pelo seu)" )
\`\`\`

Próximo passo: abrir o Claude Code neste repositório e rodar **\`/faber-init\`**.
O playbook do modo está em \`faber/bootstrap/modes/$MODE.md\`.
EOF

# ── 11. git: branch faber/bootstrap ──────────────────────────────────────
if [ "$E_GIT" -eq 0 ]; then
  info "inicializando repositório git (branch $MAIN)"
  git init -q -b "$MAIN" 2>/dev/null || { git init -q && git checkout -q -b "$MAIN" 2>/dev/null; }
  E_GIT=1; N_COMMITS=0; TREE_SUJO=0
fi
if [ "$N_COMMITS" -eq 0 ]; then
  git add -A && git commit -q -m "chore(faber): instala a fábrica de software com agentes (kit v$VERSAO)" \
    && ok "commit inicial em $MAIN" || erro "commit inicial falhou (configure git user.name/user.email)" 2
  if [ "$TRUNK" != "$MAIN" ] && ! git show-ref --verify --quiet "refs/heads/$TRUNK"; then
    git branch "$TRUNK" && ok "branch de integração criada: $TRUNK"
  fi
  git checkout -q -b faber/bootstrap "$TRUNK" && ok "branch faber/bootstrap criada a partir de $TRUNK"
else
  if [ "$TRUNK" != "$MAIN" ] && ! git show-ref --verify --quiet "refs/heads/$TRUNK"; then
    echo "   AVISO: branch de integração '$TRUNK' não existe localmente — crie-a (git branch $TRUNK) ou use --trunk $MAIN"
  fi
  if [ "$TREE_SUJO" -eq 1 ]; then
    echo "   AVISO: working tree estava sujo antes da instalação — nada foi commitado. Revise e commite:"
    echo "          git checkout -b faber/bootstrap && git add CLAUDE.md .claude faber $SPECS_DIR .gitignore && git commit -m 'chore(faber): instala a fábrica'"
  else
    if git show-ref --verify --quiet refs/heads/faber/bootstrap; then git checkout -q faber/bootstrap; else git checkout -q -b faber/bootstrap; fi
    git add -A && git commit -q -m "chore(faber): instala a fábrica de software com agentes (kit v$VERSAO)" \
      && ok "instalação commitada na branch faber/bootstrap" || echo "   AVISO: nada a commitar"
  fi
fi

# ── 12. labels do GitHub (opcional) ────────────────────────────────────────
if [ "$GH" = "on" ] && [ "$TEM_GH" -eq 1 ]; then
  FAZ=0
  if [ "$LABELS" -eq 1 ]; then FAZ=1
  elif [ "$SIM" -eq 0 ] && [ -t 0 ]; then printf 'Criar as labels faber/state:* no GitHub agora (gh label create)? [s/N]: '; read -r R; case "$R" in s|S|y|Y) FAZ=1 ;; esac; fi
  if [ "$FAZ" -eq 1 ]; then
    ( cd "$ALVO" && bash faber/scripts/board.sh bootstrap-labels ) || echo "   AVISO: labels não criadas (gh autenticado? repo correto?) — rode depois: faber/scripts/board.sh bootstrap-labels"
  fi
fi

# ── 13. verificação e próximos passos ──────────────────────────────────────
SOBRAS=$(grep -rl --include='*.md' --include='*.yaml' --include='*.json' "@@FABER_" "$ALVO/CLAUDE.md" "$ALVO/.claude" "$ALVO/faber" 2>/dev/null | grep -v '/templates/' || true)
[ -z "$SOBRAS" ] || echo "   AVISO: placeholders não renderizados em: $SOBRAS"
( cd "$ALVO" && bash -n faber/scripts/gate-check.sh && bash -n .claude/hooks/h1-bash-guard.sh ) || echo "   AVISO: erro de sintaxe em scripts copiados"

echo
echo "── Pronto ───────────────────────────────────────────────────────────"
echo "   Fábrica instalada em $ALVO (branch $(git symbolic-ref --short HEAD 2>/dev/null || echo '?'))."
echo "   Próximos passos:"
echo "     1. cd \"$ALVO\" && claude"
echo "     2. /faber-init            ← bootstrap no modo '$MODE' (gera specs, config e backlog)"
echo "     3. merge da PR faber/bootstrap → $TRUNK (gate de fundação, seu)"
echo "     4. /faber-task <sua primeira demanda>"
[ "$MODE" = "brainstorm" ] && echo "   Modo brainstorm: o PRD/BRD seguirá faber/templates/prd-brd-guide.md — substitua pelo seu guia antes do /faber-init (ou reinstale com --prd-guide)."
[ "$PYYAML" -eq 1 ] || echo "   Antes de tudo: pip3 install pyyaml"
echo "   Testes do kit (evidência de que os guarda-vidas funcionam nesta máquina):"
echo "     bash .claude/hooks/test-h1-h2.sh && bash faber/scripts/test-gate-check.sh"
exit 0
