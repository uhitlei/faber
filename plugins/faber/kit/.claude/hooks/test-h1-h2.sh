#!/bin/bash
# test-h1-h2.sh — Evidência executável dos hooks H1/H2 do kit.
# Cria um repo-sandbox descartável COM faber/config/faber.env próprio
# (owner=owner, trunk=develop, refs proibidos/confirmar, paths protegidos,
# migrations em db/migrations) e compara a decisão (deny/ask/allow/pass) com
# o esperado. Uso:
#   bash test-h1-h2.sh [/caminho/para/.claude/hooks]
set -u
HOOKS_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
H1="$HOOKS_DIR/h1-bash-guard.sh"
H2="$HOOKS_DIR/h2-write-guard.sh"
[ -f "$H1" ] && [ -f "$H2" ] && [ -f "$HOOKS_DIR/faber_config.py" ] || { echo "hooks/faber_config.py não encontrados em $HOOKS_DIR"; exit 1; }

SB=$(mktemp -d)
trap 'rm -rf "$SB"' EXIT
git -C "$SB" init -q -b "feature/TASK-999"
git -C "$SB" config user.email t@t && git -C "$SB" config user.name t
mkdir -p "$SB/db/migrations" "$SB/src/generated" "$SB/.github/workflows" "$SB/faber/config"
cat > "$SB/faber/config/faber.env" <<'EOF'
FABER_OWNER="owner"
FABER_OWNER_NAME="Owner"
FABER_TRUNK="develop"
FABER_MAIN="main"
FABER_REMOTE="origin"
FABER_MIGRATIONS_DIR="db/migrations"
FABER_PROTECTED_PATHS="src/generated/,schema.prisma"
FABER_SECRET_FILES=".env,.env.local,.env.admin"
FABER_REFS_DENY="prod-ref-abc123"
FABER_REFS_CONFIRM="hml-ref-xyz789"
FABER_CMDS_CONFIRM="\bdb\s+push\b ;; \bdocker\s+push\b"
FABER_CMDS_DENY="\bterraform\s+destroy\b"
EOF
echo "-- antiga" > "$SB/db/migrations/20250101000000_antiga.sql"
git -C "$SB" add -A && git -C "$SB" commit -qm "base"
echo "-- nova, só na feature (não versionada ainda)" > "$SB/db/migrations/20260720120000_nova.sql"

PASS=0; FAIL=0
res() {  # res <h1|h2> <json>
  local hook="$1" json="$2" out dec file
  case "$hook" in h1) file="$H1" ;; h2) file="$H2" ;; *) file="$hook" ;; esac
  out=$(printf '%s' "$json" | bash "$file" 2>/dev/null)
  dec=$(printf '%s' "$out" | python3 -c 'import sys,json
try: print(json.load(sys.stdin)["hookSpecificOutput"]["permissionDecision"])
except Exception: print("pass")' 2>/dev/null)
  printf '%s' "${dec:-pass}"
}
caso() {  # caso <nome> <esperado> <h1|h2> <json>
  local nome="$1" esperado="$2" hook="$3" json="$4" got
  got=$(res "$hook" "$json")
  if [ "$got" = "$esperado" ]; then PASS=$((PASS+1)); st="OK  "; else FAIL=$((FAIL+1)); st="FALHOU"; fi
  printf '%-6s %-58s esperado=%-5s obtido=%s\n' "$st" "$nome" "$esperado" "$got"
}
jbash() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$SB"; }
jedit() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "$SB"; }

echo "== H1 — deny =="
caso "token PROIBIDO (ref de PROD) em qualquer comando" deny h1 "$(jbash 'algum-cli db push --project-ref prod-ref-abc123')"
caso "regex PROIBIDA (terraform destroy)"        deny h1 "$(jbash 'terraform destroy -auto-approve')"
caso "push para o trunk (develop)"               deny h1 "$(jbash 'git push origin develop')"
caso "push HEAD:refs/heads/main"                 deny h1 "$(jbash 'git push origin HEAD:refs/heads/main')"
caso "gh pr merge 12"                            deny h1 "$(jbash 'gh pr merge 12 --squash')"
caso "gh api PUT pulls/5/merge"                  deny h1 "$(jbash 'gh api -X PUT repos/o/r/pulls/5/merge')"
caso "gh api POST implicito (campos) /merges"    deny h1 "$(jbash 'gh api repos/o/r/merges -f base=main -f head=feature/x')"
caso "gh api DELETE refs/heads/develop"          deny h1 "$(jbash 'gh api -X DELETE repos/o/r/git/refs/heads/develop')"
caso "gh api graphql mergePullRequest"           deny h1 "$(jbash "gh api graphql -f query='mutation { mergePullRequest(input:{}) }'")"

echo "== H1 — ask =="
caso "token de CONFIRMAR (ref de HML)"           ask  h1 "$(jbash 'algum-cli db push --project-ref hml-ref-xyz789')"
caso "regex de CONFIRMAR (db push sem ref)"      ask  h1 "$(jbash 'algum-cli db push')"
caso "regex de CONFIRMAR (docker push)"          ask  h1 "$(jbash 'docker push minha-imagem:latest')"
caso "sed -i em workflow (bypass H2)"            ask  h1 "$(jbash 'sed -i s/a/b/ .github/workflows/ci.yml')"
caso "redirecionamento para path protegido"      ask  h1 "$(jbash 'echo x > src/generated/types.ts')"
caso "redirecionamento para migration"           ask  h1 "$(jbash 'echo x > db/migrations/1_x.sql')"
caso "tee em faber.env (config da fábrica)"    ask  h1 "$(jbash 'echo FABER_OWNER=eu | tee faber/config/faber.env')"

echo "== H1 — pass (não pode atrapalhar o trabalho legítimo) =="
caso "push da feature branch"                    pass h1 "$(jbash 'git push -u origin feature/TASK-999')"
caso "commit na feature branch"                  pass h1 "$(jbash 'git commit -m \"feat: x\"')"
caso "merge do trunk NA feature (update)"        pass h1 "$(jbash 'git merge develop')"
caso "checkout de feature/main-menu"             pass h1 "$(jbash 'git checkout feature/main-menu')"
caso "gh api graphql board (ProjectV2)"          pass h1 "$(jbash "gh api graphql -f query='mutation { updateProjectV2ItemFieldValue(input:{}) }'")"
caso "gh api GET pulls/5"                        pass h1 "$(jbash 'gh api repos/o/r/pulls/5')"
caso "docker compose up (local)"                 pass h1 "$(jbash 'docker compose up -d')"
caso "grep em workflow (leitura, sem redir)"     pass h1 "$(jbash 'grep -n on: .github/workflows/ci.yml')"

echo "== H1 — gates humanos via gate-set =="
caso "gate-set G1 aprovado -> ask (aprovacao=Owner)"  ask  h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G1 aprovado --por owner')"
caso "gate-set G6 aprovado (com bash na frente)"      ask  h1 "$(jbash 'bash faber/scripts/gate-set.sh TASK-74 G6 aprovado --por owner')"
caso "gate-set G2 aprovado por cto (gate do CTO)"     pass h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G2 aprovado --por cto')"
caso "gate-set G1 pendente (nao e aprovacao)"         pass h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G1 pendente --por cto')"

echo "== H2 =="
caso "Edit em path protegido (prefixo src/generated/)" deny h2 "$(jedit 'src/generated/types.ts')"
caso "Edit em path protegido (arquivo schema.prisma)"  deny h2 "$(jedit 'schema.prisma')"
caso "Edit em .env.local"                        deny h2 "$(jedit '.env.local')"
caso "Edit em .env"                              deny h2 "$(jedit '.env')"
caso "Edit em .env.admin (configurado)"          deny h2 "$(jedit '.env.admin')"
caso "Edit em workflow (sem unlock -> ask)"      ask  h2 "$(jedit '.github/workflows/ci.yml')"
caso "migration já no histórico"                 deny h2 "$(jedit 'db/migrations/20250101000000_antiga.sql')"
caso "colisão de timestamp com o histórico"      deny h2 "$(jedit 'db/migrations/20250101000000_outra.sql')"
caso "migration nova da feature (editável)"      pass h2 "$(jedit 'db/migrations/20260720120000_nova.sql')"
caso "arquivo comum de src (editável)"           pass h2 "$(jedit 'src/App.tsx')"
caso "Edit em faber.env -> ask"                ask  h2 "$(jedit 'faber/config/faber.env')"

echo "== H2 — workflow auto-unlock via state.yaml =="
DEM="$SB/faber/tasks/TASK-999"; mkdir -p "$DEM"
wu() { printf 'demanda: TASK-999\nworkflow_unlock:\n  autorizado: %s\n  por: %s\n' "$1" "$2" > "$DEM/state.yaml"; }
rm -f "$DEM/state.yaml"
caso "workflow sem state.yaml -> ask"                  ask   h2 "$(jedit '.github/workflows/ci.yml')"
wu true owner;  caso "workflow_unlock pelo owner -> allow"      allow h2 "$(jedit '.github/workflows/ci.yml')"
wu true cto;    caso "workflow_unlock por cto (ignora) -> ask"  ask   h2 "$(jedit '.github/workflows/ci.yml')"
wu false owner; caso "workflow_unlock autorizado:false -> ask"  ask   h2 "$(jedit '.github/workflows/ci.yml')"
rm -f "$DEM/state.yaml"

echo "== H2 — guarda-vidas da fábrica =="
caso "Edit em .claude/settings.json -> ask"           ask  h2 "$(jedit '.claude/settings.json')"
caso "Edit em .claude/hooks/h1-bash-guard.sh -> ask"  ask  h2 "$(jedit '.claude/hooks/h1-bash-guard.sh')"
caso "Edit em .claude/commands/faber-task.md (livre)"    pass h2 "$(jedit '.claude/commands/faber-task.md')"

echo
echo "RESULTADO: $PASS ok, $FAIL falha(s)."
[ "$FAIL" -eq 0 ]
