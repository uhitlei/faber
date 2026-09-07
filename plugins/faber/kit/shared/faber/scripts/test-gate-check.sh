#!/bin/bash
# =============================================================================
# test-gate-check.sh — Evidência executável do gate-check.sh do kit
# Cria um repo-sandbox descartável (com origin bare local para testar o
# ls-remote do destino code-review), gera instâncias de state.yaml por cenário
# e compara o resultado (LIBERADA/BLOQUEADA) com o esperado.
# Uso: bash test-gate-check.sh [dir-com-gate-check.sh]
#      (default: diretório deste script; o template é procurado em
#       ../templates/state.template.yaml e, na falta, ao lado dos scripts)
# =============================================================================
set -u
SRC="${1:-$(cd "$(dirname "$0")" && pwd)}"
GC_SRC="$SRC/gate-check.sh"
TPL_SRC="$SRC/../templates/state.template.yaml"
[ -f "$TPL_SRC" ] || TPL_SRC="$SRC/state.template.yaml"
[ -f "$GC_SRC" ] && [ -f "$TPL_SRC" ] || { echo "gate-check.sh/template não encontrados a partir de $SRC"; exit 1; }

SB=$(mktemp -d); trap 'rm -rf "$SB"' EXIT
git init -q --bare "$SB/origin.git"
mkdir -p "$SB/repo"; cd "$SB/repo" || exit 1
git init -q -b main; git config user.email t@t; git config user.name t
git remote add origin "$SB/origin.git"
mkdir -p faber/scripts faber/templates faber/tasks
cp "$GC_SRC" faber/scripts/gate-check.sh
mkdir -p faber/scripts/lib faber/config
cp "$SRC/lib/config.sh" faber/scripts/lib/config.sh
# template com owner='owner' (o kit traz @@FABER_OWNER@@; a instalação já vem renderizada)
sed -e "s/@@FABER_OWNER@@/owner/g" -e 's/^  owner: .*/  owner: "owner"/' \
    -e 's/^  aprovadores: .*/  aprovadores: ["owner", cto, gate-check]/' "$TPL_SRC" > faber/templates/state.template.yaml
# config do sandbox: owner genérico e módulo E2E ligado (para exercitar o gate do G5)
printf 'FABER_OWNER="owner"\nFABER_TRUNK="main"\nFABER_E2E="on"\n' > faber/config/faber.env
git add -A; git commit -qm base
git checkout -qb feature/TASK-500 && git push -qu origin feature/TASK-500 2>/dev/null
GC="faber/scripts/gate-check.sh"

PASS=0; FAIL=0
# timeout portátil: macOS não traz 'timeout' (GNU coreutils); tenta gtimeout
# (brew coreutils) e, na falta de ambos, roda sem timeout.
# (patch de portabilidade de Uhitlei, incorporado — item 6)
if command -v timeout >/dev/null 2>&1; then TO="timeout 10"
elif command -v gtimeout >/dev/null 2>&1; then TO="gtimeout 10"
else TO=""; fi
mk() {  # mk <pasta> <json-overrides>
  local d="faber/tasks/$1"; mkdir -p "$d/handoffs" "$d/evidence"
  python3 - "$d/state.yaml" "$2" <<'PY'
import json, sys, yaml
nomes = ["ready-for-development","technical-consensus","developed","code-review",
         "technical-validation","my-review","ready-for-pr","merge","done"]
base = {"task":"TASK-500","issue":500,"title":"t","type":"feature",
 "branch":"feature/TASK-500","pr":None,"related_to":None,
 "state":"intake","blocking":None,
 "created_at":"2026-07-22T10:00:00-03:00","updated_at":"2026-07-22T10:00:00-03:00",
 "history":[],
 "gates":{f"G{i+1}":{"name":n,"status":"pending","approver":None,"at":None,
                     "evidence":None,"note":None} for i,n in enumerate(nomes)},
 "invocations":[]}
def deep(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict): deep(dst[k], v)
        else: dst[k] = v
deep(base, json.loads(sys.argv[2]))
open(sys.argv[1], "w").write(yaml.safe_dump(base, allow_unicode=True, sort_keys=False))
PY
}
APR() { echo "{\"status\":\"approved\",\"approver\":\"$1\",\"at\":\"2026-07-22T12:00:00-03:00\"$2}"; }

# ── geradores de evidência com o cabeçalho EXATO do evidence.sh ──
# (7 linhas '# ', acento em 'início', alinhamento por espaços, fecho em '─')
ev() {  # ev <pasta> <arquivo> <comando> <exit-code> [linha-do-corpo]
  local d="faber/tasks/$1/evidence"; mkdir -p "$d"
  {
    printf '# ── evidência executada por evidence.sh — NUNCA editar à mão ──\n'
    printf '# demanda/pasta: faber/tasks/%s\n' "$1"
    printf '# comando:       %s\n' "$3"
    printf '# início:        2026-08-12T12:00:00-0300\n'
    printf '# fim:           2026-08-12T12:02:00-0300 (duração: 120s)\n'
    printf '# exit code:     %s\n' "$4"
    printf '# ────────────────────────────────────────────────────────────────\n'
    # corpo default = saída de uma execução real do Playwright (com o sumário
    # 'N passed' que a condição (iii) do AC-4 exige)
    printf '%s\n' "${5:-Running 12 tests using 1 worker

  12 passed (34.5s)}"
  } > "$d/$2"
}
# Réplica de um falso-positivo real observado no projeto de origem:
# 'bash -c' multi-linha — a linha '# comando:' só tem "bash -c", o corpo do
# script (que cita Playwright à vontade) fica DENTRO do cabeçalho, e o exit
# code é 0 porque o `grep`/`gh` rodou. O glob '*e2e*' aceitaria isto como
# "E2E executado" sem nenhum teste ter rodado; o AC-4 tem de recusar.
ev_inspecao() {  # ev_inspecao <pasta> <arquivo>
  local d="faber/tasks/$1/evidence"; mkdir -p "$d"
  {
    printf '# ── evidência executada por evidence.sh — NUNCA editar à mão ──\n'
    printf '# demanda/pasta: faber/tasks/%s\n' "$1"
    printf '# comando:       bash -c \n'
    printf 'echo "=== Status do job Playwright E2E Tests por evento ==="\n'
    printf 'gh run view 31518629934 --json jobs -q ".jobs[] | select(.name==\\"Playwright E2E Tests\\")"\n'
    printf 'grep -n "webServer|process.env.CI" playwright.config.ts\n'
    printf '# início:        2026-08-11T22:58:02-0300\n'
    printf '# fim:           2026-08-11T22:58:09-0300 (duração: 7s)\n'
    printf '# exit code:     0\n'
    printf '# ────────────────────────────────────────────────────────────────\n'
    printf 'Playwright E2E Tests  skipped\n'
    printf 'exit code: 0\n'
  } > "$d/$2"
}
caso() {  # caso <nome> <LIB|BLQ> <pasta> <destino> [args extras...]
  local nome="$1" esp="$2" pasta="$3" dest="$4"; shift 4
  local out rc
  # shellcheck disable=SC2086  # $TO precisa de word splitting ("timeout 10")
  out=$($TO bash "$GC" "faber/tasks/$pasta" "$dest" "$@" 2>&1); rc=$?
  local ok=0
  if [ $rc -eq 124 ]; then ok=0
  elif [ "$esp" = LIB ] && [ $rc -eq 0 ]; then ok=1
  elif [ "$esp" = BLQ ] && [ $rc -ne 0 ]; then ok=1; fi
  if [ $ok -eq 1 ]; then PASS=$((PASS+1)); st="OK  "; else FAIL=$((FAIL+1)); st="FALHOU"; fi
  printf '%-6s %-56s esperado=%s rc=%s\n' "$st" "$nome" "$esp" "$rc"
  [ $ok -eq 0 ] && printf '       └─ %s\n' "$(echo "$out" | tail -3 | tr '\n' ' | ')"
}

# ── cenários ────────────────────────────────────────────────────────────────
mk d01 '{"state":"intake"}'
caso "happy: intake -> specifying"                    LIB d01 specifying

caso "estado-destino inexistente"                     BLQ d01 foo

mk d02 '{"state":"intake","_schema":{"x":1}}'
caso "vazamento de _schema na instância"              BLQ d02 specifying

mk d03 "{\"state\":\"refinement\",\"gates\":{\"G1\":$(APR cto '')}}"
caso "G1 approved por cto = autoaprovação"            BLQ d03 in-development

mk d04 "{\"state\":\"refinement\",\"gates\":{\"G1\":$(APR owner '')}}"
caso "G1 approved por owner -> in-development"      LIB d04 in-development

mk d05 '{"state":"in-development"}'
caso "developed sem logs de lint/build/test"          BLQ d05 developed
for f in 01-lint 02-build 03-test; do echo ok > "faber/tasks/d05/evidence/$f.log"; done
caso "developed com os 3 logs presentes"              LIB d05 developed

mk d06 "{\"state\":\"developed\",\"task\":\"TASK-501\",\"issue\":501,\"branch\":\"feature/TASK-501\",\"gates\":{\"G3\":$(APR gate-check ',"evidence":"evidence/03-test.log"')}}"
caso "code-review sem push da branch no origin"       BLQ d06 code-review

mk d07 "{\"state\":\"developed\",\"gates\":{\"G3\":$(APR gate-check ',"evidence":"evidence/03-test.log"')}}"
caso "code-review com branch publicada (ls-remote)"   LIB d07 code-review

mk d08 "{\"state\":\"developed\",\"gates\":{\"G3\":$(APR cto ',"evidence":"evidence/x.log"')}}"
caso "G3 approved por cto (mapa §18 rejeita)"         BLQ d08 code-review

G18="{\"G1\":$(APR owner ''),\"G2\":$(APR cto ''),\"G3\":$(APR gate-check ',"evidence":"evidence/03-test.log"'),\"G4\":$(APR cto ''),\"G5\":$(APR cto ',"evidence":"evidence/05-e2e.log"'),\"G6\":$(APR owner ''),\"G7\":$(APR cto ''),\"G8\":$(APR owner '')}"
mk d09 "{\"state\":\"pr-open\",\"pr\":\"#77\",\"gates\":$G18}"
caso "done com G1-G8 ok e G9 pending"      LIB d09 'done'

G17="{\"G1\":$(APR owner ''),\"G2\":$(APR cto ''),\"G3\":$(APR gate-check ',"evidence":"e.log"'),\"G4\":$(APR cto ''),\"G6\":$(APR owner ''),\"G7\":$(APR cto ''),\"G8\":$(APR owner '')}"
mk d10 "{\"state\":\"pr-open\",\"pr\":\"#78\",\"gates\":$G17}"
caso "done com G5 ainda pending"                     BLQ d10 'done'

mk d11 '{"state":"specifying"}'
printf 'de: po\npara: cto\n' > faber/tasks/d11/handoffs/01-po-para-cto.md
caso "handoff sem evidências referenciadas"           BLQ d11 refinement

mk d12 '{"state":"specifying"}'
echo spec > faber/tasks/d12/spec.md
echo log > faber/tasks/d12/evidence/01-spec.log
printf 'evidence: [evidence/01-spec.log, https://sonar.exemplo/branch]\n' > faber/tasks/d12/handoffs/01-po-para-cto.md
caso "handoff com arquivo real + URL"       LIB d12 refinement

mk d13 '{"state":"specifying"}'
echo spec > faber/tasks/d13/spec.md
echo log > faber/tasks/d13/evidence/01.log
printf 'evidence: [evidence/01.log]\n' > faber/tasks/d13/handoffs/2-a.md
printf 'de: x\npara: y\n' > faber/tasks/d13/handoffs/10-b.md
caso "ordenação numérica: 10-b (inválido) é o último" BLQ d13 refinement

mk d14 '{"state":"refinement","invocations":[{"agent":"senior-developer","at":"t1","input":"h/02.md"},{"agent":"senior-developer","at":"t2","input":"h/02.md"},{"agent":"senior-developer","at":"t3","input":"h/02.md"}]}'
caso "anti-loop: 3ª invocação idêntica"               BLQ d14 ready-for-dev

mk d15 '{"state":"validation"}'
caso "regressão validation -> specifying sem motivo"  BLQ d15 specifying
caso "regressão com --reason registrado"              LIB d15 specifying --reason "qa reprovou cenário 3"

mk d16 "{\"state\":\"done\",\"gates\":$G18}"
caso "sair de done é proibido"                        BLQ d16 in-development --reason "x"

mk d17 '{"state":"blocked","blocking":{"reason":"aguardando token","since":"t","previous_state":"refinement"}}'
echo spec > faber/tasks/d17/spec.md
caso "blocked -> estado diferente da origem"          BLQ d17 specifying --reason "x"
caso "blocked -> retorna à origem (refinement)"       LIB d17 refinement

mk d18 '{"state":"intake"}'
caso "--reason sem valor não trava"         BLQ d18 cancelled --reason

# impacto_ui já declarado em d19/d20: estes casos testam o placeholder,
# não o campo novo — cada caso com uma causa só.
mk d19 '{"state":"refinement","ui_impact":false}'
printf '# Spec\nAC-1: {{...}} ainda pending\n' > faber/tasks/d19/spec.md
echo ref > faber/tasks/d19/refinamento.md
caso "ready-for-dev com placeholder {{"       BLQ d19 ready-for-dev

mk d20 '{"state":"refinement","ui_impact":false}'
printf '# Spec\nAC-1: dado X, quando Y, entao Z\n' > faber/tasks/d20/spec.md
echo ref > faber/tasks/d20/refinamento.md
caso "ready-for-dev com spec limpa"                   LIB d20 ready-for-dev

# ── gate de E2E no G5 ─────────────────────────────
G5OK="{\"G5\":$(APR cto ',"evidence":"evidence/05-qa.log"')}"

mk d21 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
caso "(a) UI=true sem nenhuma evidência de E2E"       BLQ d21 my-review
ev d21 06-e2e-taxonomia.log "npx playwright test --project=chromium e2e/taxonomia.spec.ts --workers=1" 0
caso "(b) UI=true com playwright exit 0 (executado)"  LIB d21 my-review

mk d22 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev_inspecao d22 01-ci-e2e-inspecao.log
caso "(c) falso-positivo: log de inspeção com 'e2e'"  BLQ d22 my-review

mk d23 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d23 01-e2e-suite-vermelha.log "npx playwright test --project=chromium" 1
caso "(c) falso-positivo: playwright com exit code 1" BLQ d23 my-review

mk d24 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
printf '# comando:       npx playwright test\n# exit code:     0\n' \
  > faber/tasks/d24/evidence/01-e2e-forjado.log
caso "(c) falso-positivo: e2e forjado à mão"          BLQ d24 my-review

# (e) falsos-positivos que sobreviviam a "playwright + exit 0" (casos reais).
mk d32 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d32 09-guard-alvo-local-libera.log "npx playwright test --list --project=chromium" 0 \
  "Listing tests:
  e2e/auth.spec.ts:12:3 › login
Total: 36 tests in 6 files"
caso "(e) --list enumera, não executa"                BLQ d32 my-review

mk d33 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d33 03-playwright-capacidade-b.log "bash /tmp/scratchpad/b2-playwright.sh" 0 \
  "  36 passed (39.5s)"
caso "(e) 'playwright' vem do NOME do script (wrapper)" BLQ d33 my-review

mk d34 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d34 16-playwright-zero-testes.log "npx playwright test --project=chromium --grep=@naoexiste" 0 \
  "Running 0 tests using 0 workers"
caso "(e) exit 0 sem sumário de execução no corpo"     BLQ d34 my-review

mk d35 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d35 14-smoke-auth-spec-no-harness.log "npx playwright test --project=chromium e2e/auth.spec.ts --reporter=list" 0 \
  "Running 7 tests using 1 worker
  ✓  1 [chromium] › e2e/auth.spec.ts:12:3 › login (2.1s)
  7 passed (18.0s)"
caso "(e) execução real: comando + exit 0 + N passed"  LIB d35 my-review

# (f) o pipe (causa) e a suíte parcialmente vermelha (efeito).
mk d36 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d36 17-e2e-com-pipe.log "bash -c npx playwright test --project=chromium | tail -20" 0 \
  "  10 passed (30.2s)"
caso "(f) pipe no comando rouba o exit code"          BLQ d36 my-review

mk d37 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d37 18-e2e-parcialmente-vermelha.log "npx playwright test --project=chromium" 0 \
  "  2 failed
    e2e/taxonomia.spec.ts:44:5 › admin cria 4o nivel
  10 passed (30.2s)"
caso "(f) suíte parcialmente vermelha (N failed)"     BLQ d37 my-review

mk d38 "{\"state\":\"validation\",\"ui_impact\":true,\"gates\":$G5OK}"
ev d38 19-e2e-verde-sem-pipe.log "npx playwright test --project=chromium e2e/taxonomia.spec.ts" 0 \
  "Running 12 tests using 1 worker
  12 passed (41.0s)"
caso "(f) execução legítima segue liberando"          LIB d38 my-review

mk d25 "{\"state\":\"validation\",\"ui_impact\":false,\"gates\":$G5OK}"
caso "(d) UI=false sem E2E (banco/infra/doc)"   LIB d25 my-review

mk d26 "{\"state\":\"validation\",\"gates\":$G5OK}"
caso "(d) impacto_ui ausente (demanda anterior)"      LIB d26 my-review

# ── impacto_ui obrigatório em ready-for-dev ───────
spec_ok() { printf '# Spec\nAC-1: dado X, quando Y, entao Z\n' > "faber/tasks/$1/spec.md"
            echo ref > "faber/tasks/$1/refinamento.md"; }

mk d27 '{"state":"refinement"}'; spec_ok d27
caso "ready-for-dev NOVA sem impacto_ui declarado"    BLQ d27 ready-for-dev

mk d28 '{"state":"refinement","ui_impact":true}'; spec_ok d28
caso "ready-for-dev NOVA com impacto_ui: true"        LIB d28 ready-for-dev

mk d29 '{"state":"refinement","ui_impact":"sim"}'; spec_ok d29
caso "impacto_ui com valor não-booleano ('sim')"      BLQ d29 ready-for-dev

# Compatibilidade: demanda ANTERIOR à regra não é travada retroativamente —
# o histórico prova que ela já entrou em ready-for-dev sob o regime antigo.
mk d30 '{"state":"validation","history":[{"from_state":"refinement","to_state":"ready-for-dev","at":"2026-08-01T10:00:00-03:00","by":"cto","reason":null}]}'
spec_ok d30
caso "volta a ready-for-dev: antiga com histórico"    LIB d30 ready-for-dev --reason "DoR reaberto"

# Mesma compatibilidade pelo outro fato estrutural: estado atual já é posterior
# a ready-for-dev (histórico vazio, como em demandas migradas na mão).
mk d31 '{"state":"in-development"}'; spec_ok d31
caso "volta a ready-for-dev: antiga sem histórico"    LIB d31 ready-for-dev --reason "DoR reaberto"

echo
echo "RESULTADO: $PASS ok, $FAIL falha(s)."
[ "$FAIL" -eq 0 ]