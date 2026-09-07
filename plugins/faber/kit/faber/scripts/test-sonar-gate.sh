#!/bin/bash
# =============================================================================
# test-sonar-gate.sh — Evidência executável do sonar-gate.sh (TASK-118, M-8)
#
# No estilo do test-gate-check.sh: sandbox descartável, cenários explícitos,
# comparação do resultado (exit code + trecho da saída) com o esperado.
#
# O `curl` é STUBADO no PATH: cada cenário escreve fixtures JSON num diretório e
# o stub responde por endpoint (authentication/validate, project_analyses/search,
# qualitygates/project_status, issues/search), com código HTTP configurável. O
# `jq` é o REAL de propósito — os filtros jq do gate (união por key, identidade
# rule|caminho|hash) são parte do que precisa ser testado; um jq de mentira
# testaria o stub. Há um cenário que remove o jq do PATH para cobrir a ausência.
# O `git` também é real, num repo-sandbox com HEAD conhecido: é contra ele que a
# guarda A-1 (análise ≠ HEAD → nao-executado) é exercida.
#
# Cobre: união com sobreposição, união inconsistente (M-2), baseline 404,
# HTTP 500, projeto sem análise, revisão divergente do HEAD (A-1), catraca com
# issue nova (A-2), catraca sem novidade, tudo limpo, parâmetro fora do padrão
# (M-1), jq ausente, reprovado SEM catraca (N-6a) e o modo legado/trunk —
# `&branch=` na query + revisão conferida contra refs/remotes/origin/<branch>
# (N-6b, N-2).
#
# Uso: bash test-sonar-gate.sh [dir-com-sonar-gate.sh]
#      (default: diretório deste script)
# =============================================================================
set -u
export FABER_SONAR_PROJECT_KEY="TRK"   # projeto do trunk usado pelas fixturas
SRC="${1:-$(cd "$(dirname "$0")" && pwd)}"
GATE="$SRC/sonar-gate.sh"
[ -f "$GATE" ] || { echo "sonar-gate.sh não encontrado em $SRC"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq ausente — este teste exige o jq real"; exit 1; }

SB="$(mktemp -d)"; trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB/bin" "$SB/repo"

# --- repo-sandbox: dá um HEAD estável para a guarda A-1 ----------------------
cd "$SB/repo" || exit 1
git init -q -b main
git config user.email t@t; git config user.name t
echo x > a.txt; git add -A; git commit -qm base
HEAD_SHA="$(git rev-parse HEAD)"
# N-2: ref REMOTO sem ref local correspondente — é o estado normal de um
# worktree de demanda (ninguém faz checkout de Develop lá). Só existe
# refs/remotes/origin/Develop; refs/heads/Develop NÃO existe.
git update-ref refs/remotes/origin/Develop "$HEAD_SHA"

# --- stub de curl ------------------------------------------------------------
# Responde a partir de $FIXDIR: <chave>.json (corpo) e <chave>.code (HTTP,
# default 200). Chave inexistente = 404, que é como o servidor responde a
# projeto que não existe.
cat > "$SB/bin/curl" <<'STUB'
#!/bin/bash
url=""
for a in "$@"; do case "$a" in http://*|https://*) url="$a" ;; esac; done
printf '%s\n' "$url" >> "$FIXDIR/urls.log"   # cenário 12 confere a query montada
p() { printf '%s' "$url" | sed -n -E "s/.*[?&]$1=([^&]*).*/\1/p"; }
case "$url" in
  *authentication/validate*)     chave="auth" ;;
  *project_analyses/search*)     chave="analyses.$(p project)" ;;
  *qualitygates/project_status*) chave="qg.$(p projectKey)" ;;
  *issues/search*)
      case "$url" in *impactSeverities=*) f=imp ;; *) f=leg ;; esac
      chave="issues.$(p components).$f.$(p p)" ;;
  *) chave="desconhecido" ;;
esac
corpo="$FIXDIR/$chave.json"
if [ -f "$corpo" ]; then
  codigo=200
  [ -f "$FIXDIR/$chave.code" ] && codigo="$(cat "$FIXDIR/$chave.code")"
  printf '%s\n%s\n' "$(cat "$corpo")" "$codigo"
else
  printf '%s\n%s\n' '{}' '404'
fi
exit 0
STUB
chmod +x "$SB/bin/curl"

export PATH="$SB/bin:$PATH"
export SONAR_TOKEN="token-de-mentira"
export SONAR_HOST_URL="http://sonar.invalido.local"

# --- helpers de fixture ------------------------------------------------------
FIXDIR=""; export FIXDIR
novo_cenario() {           # novo_cenario <nome-curto>
  FIXDIR="$SB/fx-$1"; mkdir -p "$FIXDIR"
  echo '{"valid":true}' > "$FIXDIR/auth.json"
}
fx()      { printf '%s\n' "$2" > "$FIXDIR/$1.json"; }
fxcode()  { printf '%s\n' "$2" > "$FIXDIR/$1.code"; }

analises() {               # analises <proj> <revision>
  fx "analyses.$1" "{\"analyses\":[{\"date\":\"2026-08-17T00:00:00+0000\",\"revision\":\"$2\"}]}"
  fx "qg.$1" '{"projectStatus":{"status":"OK"}}'
}

# issues <proj> <leg|imp> <total|auto> [item...]  — item = regra,caminho,hash,key
issues() {
  local proj="$1" filtro="$2" total="$3"; shift 3
  local arr="" n=0 item r c h k
  for item in "$@"; do
    IFS=',' read -r r c h k <<< "$item"
    [ -z "$arr" ] || arr="$arr,"
    arr="$arr{\"key\":\"$k\",\"rule\":\"$r\",\"component\":\"$proj:$c\",\"hash\":\"$h\",\"line\":10}"
    n=$((n+1))
  done
  [ "$total" = "auto" ] && total="$n"
  fx "issues.$proj.$filtro.1" "{\"total\":$total,\"issues\":[$arr]}"
}

# --- runner ------------------------------------------------------------------
PASS=0; FAIL=0
caso() {                   # caso <nome> <exit-esperado> <trecho-esperado> [args do gate...]
  local nome="$1" esp="$2" trecho="$3"; shift 3
  local out rc ok=1
  out="$(bash "$GATE" "$@" 2>&1)"; rc=$?
  [ "$rc" = "$esp" ] || ok=0
  [ -z "$trecho" ] || echo "$out" | grep -qF -- "$trecho" || ok=0
  if [ $ok -eq 1 ]; then PASS=$((PASS+1)); st="OK  "; else FAIL=$((FAIL+1)); st="FALHOU"; fi
  printf '%-6s %-58s exit=%s (esperado %s)\n' "$st" "$nome" "$rc" "$esp"
  [ $ok -eq 0 ] && printf '       └─ %s\n' "$(echo "$out" | tail -3 | tr '\n' '|')"
  return 0
}

P="TRK-TASK-500"; B="TRK"

# ── 1. União com sobreposição: 3 legacy + 3 impacto, 2 em comum = 4 ──────────
# (soma daria 6, max daria 3 — só a união por key acerta). Baseline tem as
# mesmas 4 identidades, com keys diferentes: nada novo, aprova.
novo_cenario uniao; analises "$P" "$HEAD_SHA"; analises "$B" "irrelevante"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1" "ts:S2,src/b.ts,h2,k2" "ts:S3,src/c.ts,h3,k3"
issues "$P" imp auto "ts:S2,src/b.ts,h2,k2" "ts:S3,src/c.ts,h3,k3" "ts:S4,src/d.ts,h4,k4"
issues "$B" leg auto "ts:S1,src/a.ts,h1,b1" "ts:S2,src/b.ts,h2,b2" "ts:S3,src/c.ts,h3,b3"
issues "$B" imp auto "ts:S2,src/b.ts,h2,b2" "ts:S3,src/c.ts,h3,b3" "ts:S4,src/d.ts,h4,b4"
caso "união com sobreposição = 4 (não 6, não 3)" 0 "CRITICAL_HIGH=4" \
     --project "$P" --branch main --baseline "$B"
caso "as duas contagens saem separadas na evidência"   0 "CRITICAL_LEGACY=3" \
     --project "$P" --branch main --baseline "$B"
caso "catraca sem issue nova aprova"              0 "NOVAS_VS_BASELINE=0" \
     --project "$P" --branch main --baseline "$B"

# ── 2. União inconsistente (M-2): a API diz 5, a página entrega 1 chave ──────
novo_cenario inconsistente; analises "$P" "$HEAD_SHA"
issues "$P" leg 5 "ts:S1,src/a.ts,h1,k1"
issues "$P" imp auto "ts:S1,src/a.ts,h1,k1"
caso "união menor que a contagem da API = nao-executado" 3 "união inconsistente" \
     --project "$P" --branch main

# ── 3. Baseline inexistente (404) bloqueia — nunca vira "baseline zero" ──────
novo_cenario baseline404; analises "$P" "$HEAD_SHA"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1"
issues "$P" imp auto "ts:S1,src/a.ts,h1,k1"
analises "$B" "irrelevante"     # o baseline existe como projeto…
                                # …mas issues/search dele responde 404 (sem fixture)
caso "baseline 404 = nao-executado (nomeia o baseline)" 3 "projeto 'TRK' não encontrado" \
     --project "$P" --branch main --baseline "$B"

# ── 4. HTTP 500 em issues/search ────────────────────────────────────────────
novo_cenario http500; analises "$P" "$HEAD_SHA"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1"; fxcode "issues.$P.leg.1" 500
caso "HTTP 500 = nao-executado" 3 "HTTP 500" --project "$P" --branch main

# ── 5. Projeto provisionado e nunca escaneado (o pior fail-open) ─────────────
novo_cenario semanalise; fx "analyses.$P" '{"analyses":[]}'
fx "qg.$P" '{"projectStatus":{"status":"NONE"}}'
issues "$P" leg auto; issues "$P" imp auto
caso "projeto sem NENHUMA análise = nao-executado" 3 "sem NENHUMA análise" \
     --project "$P" --branch main

# ── 6. A-1: análise publicada é de outro commit ─────────────────────────────
novo_cenario revisaovelha; analises "$P" "0000000000000000000000000000000000000000"
issues "$P" leg auto; issues "$P" imp auto
caso "revisão analisada ≠ HEAD = nao-executado" 3 "veredito recusado sobre código diferente" \
     --project "$P" --branch main

# ── 6b. A-1: análise sem revisão publicada ──────────────────────────────────
novo_cenario semrevisao
fx "analyses.$P" '{"analyses":[{"date":"2026-08-17T00:00:00+0000"}]}'
fx "qg.$P" '{"projectStatus":{"status":"OK"}}'
issues "$P" leg auto; issues "$P" imp auto
caso "análise sem sonar.scm.revision = nao-executado" 3 "não publicou a revisão" \
     --project "$P" --branch main

# ── 7. A-2: catraca com issue NOVA (mesmo total, conjunto diferente) ────────
# O projeto tem 2 Critical/High e o baseline tem 2: pela comparação de TOTAIS
# (o defeito A-2) isto passaria como "não piorou". Uma delas é nova.
novo_cenario issuenova; analises "$P" "$HEAD_SHA"; analises "$B" "irrelevante"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1" "ts:S9,src/novo.ts,h9,k9"
issues "$P" imp auto "ts:S1,src/a.ts,h1,k1" "ts:S9,src/novo.ts,h9,k9"
issues "$B" leg auto "ts:S1,src/a.ts,h1,b1" "ts:S7,src/velho.ts,h7,b7"
issues "$B" imp auto "ts:S1,src/a.ts,h1,b1" "ts:S7,src/velho.ts,h7,b7"
caso "issue nova com total igual = reprovado"  2 "NOVA=ts:S9|src/novo.ts|h9" \
     --project "$P" --branch main --baseline "$B"
caso "issue nova: contagem impressa"           2 "NOVAS_VS_BASELINE=1" \
     --project "$P" --branch main --baseline "$B"

# ── 7b. Issue que SAIU do projeto (só herdadas) aprova ──────────────────────
novo_cenario sonovas; analises "$P" "$HEAD_SHA"; analises "$B" "irrelevante"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1"
issues "$P" imp auto "ts:S1,src/a.ts,h1,k1"
issues "$B" leg auto "ts:S1,src/a.ts,h1,b1" "ts:S7,src/velho.ts,h7,b7"
issues "$B" imp auto "ts:S1,src/a.ts,h1,b1" "ts:S7,src/velho.ts,h7,b7"
caso "só dívida herdada = aprovado pela catraca" 0 "CATRACA=sem-novas" \
     --project "$P" --branch main --baseline "$B"

# ── 8. Tudo limpo ───────────────────────────────────────────────────────────
novo_cenario limpo; analises "$P" "$HEAD_SHA"; analises "$B" "irrelevante"
issues "$P" leg auto; issues "$P" imp auto
issues "$B" leg auto; issues "$B" imp auto
caso "zero Critical/High = aprovado"            0 "CATRACA=zero" \
     --project "$P" --branch main --baseline "$B"
caso "zero Critical/High sem catraca = aprovado" 0 "VEREDITO=aprovado" \
     --project "$P" --branch main

# ── 9. M-1: parâmetro que desligaria o filtro do gate ───────────────────────
novo_cenario injecao; analises "$P" "$HEAD_SHA"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1"; issues "$P" imp auto "ts:S1,src/a.ts,h1,k1"
caso "branch com & = nao-executado (M-1)" 3 "rótulo de branch fora do padrão" \
     --project "$P" --branch 'main&resolved=true'
caso "projeto com & = nao-executado (M-1)" 3 "chave de projeto fora do padrão" \
     --project "$P&resolved=true" --branch main
caso "baseline com & = nao-executado (M-1)" 3 "chave de baseline fora do padrão" \
     --project "$P" --branch main --baseline 'TRK&x=1'

# ── 10. Ferramenta ausente = nao-executado, nunca aprovado ──────────────────
novo_cenario semjq; analises "$P" "$HEAD_SHA"
issues "$P" leg auto; issues "$P" imp auto
SEMJQ="$SB/semjq"; mkdir -p "$SEMJQ"
for prog in curl git sed awk cat grep sort cut head mktemp tr; do
  origem="$(command -v "$prog" 2>/dev/null)"; [ -n "$origem" ] && ln -sf "$origem" "$SEMJQ/$prog"
done
ln -sf "$SB/bin/curl" "$SEMJQ/curl"
( PATH="$SEMJQ"; "$BASH" "$GATE" --project "$P" --branch main >"$SB/semjq.out" 2>&1 )
rc=$?
if [ "$rc" = 3 ] && grep -q "jq ausente" "$SB/semjq.out"; then
  PASS=$((PASS+1)); printf '%-6s %-58s exit=%s (esperado 3)\n' "OK  " "jq ausente = nao-executado" "$rc"
else
  FAIL=$((FAIL+1)); printf '%-6s %-58s exit=%s (esperado 3)\n' "FALHOU" "jq ausente = nao-executado" "$rc"
fi

# ── 11. N-6(a): reprovado SEM catraca — o caminho mais básico do gate ───────
# Sem `--baseline` a régua é zero (§18-G5). União = k1,k2,k3 = 3.
novo_cenario reprovado; analises "$P" "$HEAD_SHA"
issues "$P" leg auto "ts:S1,src/a.ts,h1,k1" "ts:S2,src/b.ts,h2,k2"
issues "$P" imp auto "ts:S2,src/b.ts,h2,k2" "ts:S3,src/c.ts,h3,k3"
caso "Critical/High sem catraca = reprovado" 2 "MOTIVO=3 issue(s) Critical/High abertas (legacy=2, impacto=2)" \
     --project "$P" --branch main

# ── 12. N-6(b) + N-2: modo legado/trunk ─────────────────────────────────────
# Uso antigo (`sonar-gate.sh <branch>`): MODO=branch, `&branch=` nas consultas e
# revisão conferida contra ref de branch. O repo-sandbox tem SÓ
# refs/remotes/origin/Develop (sem refs/heads/Develop), que é o estado de um
# worktree de demanda — antes do N-2 isto era nao-executado.
novo_cenario trunk; analises "$B" "$HEAD_SHA"
issues "$B" leg auto; issues "$B" imp auto
out="$(bash "$GATE" Develop 2>&1)"; rc=$?
ok=1
[ "$rc" = 0 ] || ok=0
echo "$out" | grep -qF "MODO=branch" || ok=0
echo "$out" | grep -qF "REVISAO_CONFERIDA=refs/remotes/origin/Develop=$HEAD_SHA" || ok=0
grep -q 'issues/search.*branch=Develop' "$FIXDIR/urls.log" || ok=0   # `&branch=` só existe no modo legado
if [ $ok -eq 1 ]; then
  PASS=$((PASS+1)); printf '%-6s %-58s exit=%s (esperado 0)\n' "OK  " "modo trunk: branch= na query + ref origin (N-2)" "$rc"
else
  FAIL=$((FAIL+1)); printf '%-6s %-58s exit=%s (esperado 0)\n' "FALHOU" "modo trunk: branch= na query + ref origin (N-2)" "$rc"
  printf '       └─ %s\n' "$(echo "$out" | tail -3 | tr '\n' '|')"
fi

echo
echo "RESULTADO: $PASS ok, $FAIL falha(s)."
[ "$FAIL" -eq 0 ] || exit 1
exit 0
