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
# MODO = permission_mode da sessão no JSON do hook (vazio = campo ausente)
MODO=""
jbash() { python3 -c 'import json,sys; d={"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}; sys.argv[3] and d.update(permission_mode=sys.argv[3]); print(json.dumps(d))' "$1" "$SB" "$MODO"; }
jedit() { python3 -c 'import json,sys; d={"tool_name":"Edit","tool_input":{"file_path":sys.argv[1]},"cwd":sys.argv[2]}; sys.argv[3] and d.update(permission_mode=sys.argv[3]); print(json.dumps(d))' "$1" "$SB" "$MODO"; }

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
caso "grep em hooks com 2>/dev/null (leitura)"   pass h1 "$(jbash 'grep -rn H1 .claude/hooks/ 2>/dev/null')"
caso "cat de .env.example com 2>&1 (leitura)"   pass h1 "$(jbash 'cat .env.example 2>&1 | head')"
caso "redir real mesmo com 2>/dev/null junto"    ask  h1 "$(jbash 'echo x > .env 2>/dev/null')"

echo "== H1 — gates humanos via gate-set =="
caso "gate-set G1 approved -> ask (aprovacao=Owner)"  ask  h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G1 approved --by owner')"
caso "gate-set G6 approved (com bash na frente)"      ask  h1 "$(jbash 'bash faber/scripts/gate-set.sh TASK-74 G6 approved --by owner')"
caso "gate-set G2 approved por cto (gate do CTO)"     pass h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G2 approved --by cto')"
caso "gate-set G1 pending (nao e aprovacao)"         pass h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G1 pending --by cto')"
caso "workflow-unlock -> ask (decisao do Owner)"     ask  h1 "$(jbash 'faber/scripts/workflow-unlock.sh TASK-74 --by owner')"
caso "workflow-unlock --revoke (restringe) livre"    pass h1 "$(jbash 'faber/scripts/workflow-unlock.sh TASK-74 --by owner --revoke')"

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
wu() { printf 'task: TASK-999\nworkflow_unlock:\n  authorized: %s\n  by: %s\n' "$1" "$2" > "$DEM/state.yaml"; }
rm -f "$DEM/state.yaml"
caso "workflow sem state.yaml -> ask"                  ask   h2 "$(jedit '.github/workflows/ci.yml')"
wu true owner;  caso "workflow_unlock pelo owner -> allow"      allow h2 "$(jedit '.github/workflows/ci.yml')"
wu true cto;    caso "workflow_unlock por cto (ignora) -> ask"  ask   h2 "$(jedit '.github/workflows/ci.yml')"
wu false owner; caso "workflow_unlock authorized:false -> ask"  ask   h2 "$(jedit '.github/workflows/ci.yml')"
rm -f "$DEM/state.yaml"

echo "== H2 — guarda-vidas da fábrica =="
caso "Edit em .claude/settings.json -> ask"           ask  h2 "$(jedit '.claude/settings.json')"
caso "Edit em .claude/hooks/h1-bash-guard.sh -> ask"  ask  h2 "$(jedit '.claude/hooks/h1-bash-guard.sh')"
caso "Edit em .claude/commands/faber-task.md (livre)"    pass h2 "$(jedit '.claude/commands/faber-task.md')"

echo "== Modo bypass (permission_mode=bypassPermissions, FABER_BYPASS=on) =="
MODO="bypassPermissions"
caso "bypass: token de CONFIRMAR passa livre"         pass  h1 "$(jbash 'algum-cli db push --project-ref hml-ref-xyz789')"
caso "bypass: regex de CONFIRMAR (docker push) livre" pass  h1 "$(jbash 'docker push minha-imagem:latest')"
caso "bypass: comando comum segue livre"              pass  h1 "$(jbash 'npm run test')"
caso "bypass: token PROIBIDO segue deny"              deny  h1 "$(jbash 'algum-cli db push --project-ref prod-ref-abc123')"
caso "bypass: regex PROIBIDA segue deny"              deny  h1 "$(jbash 'terraform destroy -auto-approve')"
caso "bypass: push para o trunk segue deny"           deny  h1 "$(jbash 'git push origin develop')"
caso "bypass: gh pr merge segue deny"                 deny  h1 "$(jbash 'gh pr merge 12 --squash')"
caso "bypass: gate-set G1 approved SEGUE ask (humano)" ask  h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G1 approved --by owner')"
caso "bypass: gate-set G8 approved SEGUE ask (humano)" ask  h1 "$(jbash 'bash faber/scripts/gate-set.sh TASK-74 G8 approved --by owner')"
caso "bypass: workflow-unlock SEGUE ask (humano)"    ask   h1 "$(jbash 'bash faber/scripts/workflow-unlock.sh TASK-74 --by owner')"
caso "bypass: gate-set G2 do CTO livre"               pass  h1 "$(jbash 'faber/scripts/gate-set.sh TASK-74 G2 approved --by cto')"
caso "bypass: sed -i em workflow -> deny (não ask)"   deny  h1 "$(jbash 'sed -i s/a/b/ .github/workflows/ci.yml')"
caso "bypass: tee em faber.env -> deny"               deny  h1 "$(jbash 'echo FABER_OWNER=eu | tee faber/config/faber.env')"
caso "bypass: redir em path protegido -> deny"        deny  h1 "$(jbash 'echo x > src/generated/types.ts')"
caso "bypass: grep em hooks com 2>/dev/null livre"    pass  h1 "$(jbash 'grep -rn H1 .claude/hooks/ 2>/dev/null')"
caso "bypass: Edit em .env segue deny"                deny  h2 "$(jedit '.env')"
caso "bypass: Edit em path protegido segue deny"      deny  h2 "$(jedit 'src/generated/types.ts')"
caso "bypass: migration no histórico segue deny"      deny  h2 "$(jedit 'db/migrations/20250101000000_antiga.sql')"
caso "bypass: migration nova livre"                   pass  h2 "$(jedit 'db/migrations/20260720120000_nova.sql')"
caso "bypass: arquivo comum livre"                    pass  h2 "$(jedit 'src/App.tsx')"
caso "bypass: Edit em .claude/settings.json -> deny"  deny  h2 "$(jedit '.claude/settings.json')"
caso "bypass: Edit em hook -> deny"                   deny  h2 "$(jedit '.claude/hooks/h1-bash-guard.sh')"
caso "bypass: Edit em faber.env -> deny"              deny  h2 "$(jedit 'faber/config/faber.env')"
caso "bypass: workflow sem unlock -> deny"            deny  h2 "$(jedit '.github/workflows/ci.yml')"
wu true owner
caso "bypass: workflow com unlock do owner -> allow"  allow h2 "$(jedit '.github/workflows/ci.yml')"
rm -f "$DEM/state.yaml"

echo "== Modo bypass — só vale para bypassPermissions e com FABER_BYPASS=on =="
MODO="acceptEdits"
caso "acceptEdits: docker push segue ask"             ask   h1 "$(jbash 'docker push minha-imagem:latest')"
caso "acceptEdits: Edit em settings.json segue ask"   ask   h2 "$(jedit '.claude/settings.json')"
MODO="default"
caso "default: token de CONFIRMAR segue ask"          ask   h1 "$(jbash 'algum-cli db push --project-ref hml-ref-xyz789')"
MODO="bypassPermissions"
echo 'FABER_BYPASS="off"' >> "$SB/faber/config/faber.env"
caso "FABER_BYPASS=off: docker push segue ask"        ask   h1 "$(jbash 'docker push minha-imagem:latest')"
caso "FABER_BYPASS=off: workflow sem unlock -> ask"   ask   h2 "$(jedit '.github/workflows/ci.yml')"
caso "FABER_BYPASS=off: sed -i em workflow -> ask"    ask   h1 "$(jbash 'sed -i s/a/b/ .github/workflows/ci.yml')"
MODO=""

echo
echo "RESULTADO: $PASS ok, $FAIL falha(s)."
[ "$FAIL" -eq 0 ]
