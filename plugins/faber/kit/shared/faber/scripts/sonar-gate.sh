#!/bin/bash
# =============================================================================
# sonar-gate.sh — consulta o Sonar e imprime um veredito parseável (zero LLM)
# para o G5. ARQUITETURA §11 (Skill sonar-gate), §18-G5 (Critical/High JAMAIS
# excepcionável), P2 (SONAR_TOKEN por NOME). §15: indisponível = "não
# executado", jamais inferido — com MOTIVO preciso, nunca genérico.
#
# Decisões de desenho (aprendidas no projeto de origem):
#
#  1. Modelo de severidade errado. `severities=BLOCKER,CRITICAL` é o modelo
#     LEGACY; "Critical e High" (a regra do gate) mistura os dois
#     modelos — HIGH é do modelo de IMPACTO. Não são sinônimos: na medição do
#     refinamento havia HIGH que o script antigo não enxergava. Pior, passar os
#     dois parâmetros na MESMA chamada é AND, não união. Agora são duas
#     chamadas, as duas contagens são impressas, e o bloqueio é pela UNIÃO real
#     (união dos conjuntos de chaves, não max nem soma).
#  2. `QG=OK` como condição de aprovação era armadilha. O Quality Gate herda
#     `new_security_hotspots_reviewed=100` com 33 hotspots por revisar e
#     `new_violations>0` sobre um New Code Period indefinido: mesmo zerando
#     Critical/High o veredito sairia `reprovado` para sempre, por motivo que
#     NÃO é o que foi pedido. Decisão: o status do QG passa a ser
#     INFORMATIVO no veredito; o bloqueio é só por Critical/High.
#  3. Alvo fixo no projeto do trunk + `branch=`. O servidor é Community Edition (sem
#     multi-branch): TODA feature branch caía em "sem análise" → exit 3 →
#     com o gate ligado, toda demanda bloqueada. Agora aceita `--project`
#     (o espelho `<PROJECT_KEY>-TASK-XXX` publicado por sonar-task.sh) e mede
#     *overall*, que é o único recorte que existe no Community.
#
# Regras adicionais:
#
#  A-1. AMARRAÇÃO AO COMMIT. O veredito só vale para o código que foi analisado:
#       a `revision` da última análise é comparada com o commit local da branch
#       avaliada. Divergiu (ou não dá para provar) → `not-executed`. Antes, uma
#       análise de três commits atrás continuava dizendo "approved".
#  A-2. RATCHET POR DIFERENÇA DE CONJUNTOS. Comparar TOTAIS deixava passar a
#       troca "removi 5 herdadas, introduzi 5 novas". Agora o que reprova é a
#       existência de issue Critical/High no projeto medido que NÃO existe no
#       baseline.
#
#       IDENTIDADE DE ISSUE ENTRE PROJETOS (decisão documentada): a `key` da
#       issue é um UUID por projeto — o espelho `<PROJECT_KEY>-TASK-XXX` e o projeto do trunk (`FABER_SONAR_PROJECT_KEY`)
#       nunca compartilham keys, então comparar keys entre projetos daria
#       "tudo novo". A identidade usada é `rule|caminho|hash`, com os três
#       campos vindos de `issues/search` (verificado na API 26.4):
#         - `rule`      — a regra violada (ex.: typescript:S3776);
#         - `caminho`   — `component` menos o prefixo `<projectKey>:`, que é o
#                         que difere entre espelho e trunk;
#         - `hash`      — hash da LINHA da issue. Escolhido em vez de `line`
#                         de propósito: código que só desce de lugar mantém o
#                         hash (não vira "issue nova" falsa), e código alterado
#                         muda o hash (vira issue nova, que é o que se quer).
#                         Issue sem hash (nível de arquivo) cai em `L<line>`.
#       Limite conhecido: duas issues da MESMA regra, no MESMO arquivo, em
#       linhas de conteúdo IDÊNTICO colapsam numa identidade só — a catraca
#       fica levemente permissiva nesse caso raro. O total (`CRITICAL_HIGH`)
#       continua sendo contado por key, sem colapso, e é impresso do lado.
#  M-1. `--project`/`--branch`/`--baseline` são validados contra padrão ancorado
#       ANTES de virarem URL (um rótulo com `&` desligava o filtro do gate).
#  M-2. A união é conferida contra as contagens da API (`C_UNI >= C_LEG` e
#       `C_UNI >= C_IMP`) e o status do `jq` da paginação é checado: página que
#       não rende chaves vira `not-executed`, nunca uma união subcontada.
#
# RATCHET: enquanto a dívida herdada não zera, `--baseline`
# compara o projeto medido com o trunk LIDO NA HORA. Zero Critical/High aprova;
# nenhuma issue nova em relação ao baseline aprova (com os números impressos);
# qualquer issue nova reprova, com as identidades listadas. O número nunca fica
# escondido.
#
# Uso:
#   sonar-gate.sh [branch]                       # trunk (compatível com o uso antigo)
#   sonar-gate.sh --project <PROJECT_KEY>-TASK-XXX [--branch <nome>] [--baseline <PROJECT_KEY>]
#
#   --project/$SONAR_PROJECT_KEY  projeto-espelho da demanda; ativa o modo
#                                 OVERALL (sem `branch=`, inexistente no Community).
#                                 `--branch` aí é só rótulo do veredito.
#   --baseline <key>              liga a catraca contra esse projeto (overall).
#
# Env exigido (por NOME, nunca versionado): SONAR_TOKEN, SONAR_HOST_URL.
# NUNCA imprime o token. Saída = linhas CHAVE=VALOR + exit code:
#   0  aprovado       zero Critical/High (ou, com catraca, nenhuma issue nova)
#   2  reprovado      há Critical/High acima do permitido (não excepcionável)
#   3  not-executed  token/host/rede/jq ausentes, projeto ou branch SEM
#                     análise, análise de outro commit, dado inconsistente —
#                     sempre com MOTIVO específico. Ausência de dado NUNCA é
#                     aprovação.
# =============================================================================
set -u
# shellcheck source=lib/config.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/config.sh"

PROJ="${SONAR_PROJECT_KEY:-}"
BRANCH=""
BASELINE=""

nao_executado() { echo "VERDICT=not-executed"; echo "REASON=$1"; exit 3; }

while [ $# -gt 0 ]; do
  case "$1" in
    --project)  [ $# -ge 2 ] || nao_executado "--project exige um valor";  PROJ="$2";     shift 2 ;;
    --branch)   [ $# -ge 2 ] || nao_executado "--branch exige um valor";   BRANCH="$2";   shift 2 ;;
    --baseline) [ $# -ge 2 ] || nao_executado "--baseline exige um valor"; BASELINE="$2"; shift 2 ;;
    -*)         nao_executado "opção desconhecida: $1" ;;
    *)          [ -z "$BRANCH" ] || nao_executado "argumento extra: $1"; BRANCH="$1"; shift ;;
  esac
done

# MODE=overall quando há projeto-espelho (Community não tem branch); MODE=branch
# é o caminho legado, para o projeto do trunk (`FABER_SONAR_PROJECT_KEY`), onde a "branch" do Sonar existe.
if [ -n "$PROJ" ]; then MODE="overall"; else
  PROJ="${FABER_SONAR_PROJECT_KEY:-}"; MODE="branch"
  [ -n "$PROJ" ] || nao_executado "FABER_SONAR_PROJECT_KEY vazio em faber/config/faber.env (projeto do trunk no Sonar)"
fi
[ -n "$BRANCH" ] || BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

[ -n "${SONAR_TOKEN:-}" ]    || nao_executado "SONAR_TOKEN ausente no ambiente (P2)"
[ -n "${SONAR_HOST_URL:-}" ] || nao_executado "SONAR_HOST_URL ausente no ambiente (P2)"
[ -n "$BRANCH" ]             || nao_executado "branch indeterminada"
command -v jq   >/dev/null 2>&1 || nao_executado "jq ausente"
command -v curl >/dev/null 2>&1 || nao_executado "curl ausente"
command -v git  >/dev/null 2>&1 || nao_executado "git ausente — sem git é impossível provar que a análise é do código avaliado (A-1)"
[ "$BASELINE" != "$PROJ" ]   || nao_executado "baseline '$BASELINE' é o próprio projeto medido — a catraca compararia o projeto consigo mesmo"

# M-1: nada entra em URL sem casar com padrão ANCORADO. Um rótulo de branch com
# `&` acrescentaria parâmetros à query e desligaria o filtro do gate (a API
# honra a última ocorrência) — controle de gate desligado por argumento.
[[ "$PROJ"   =~ ^[A-Za-z0-9._:-]+$ ]]     || nao_executado "chave de projeto fora do padrão ([A-Za-z0-9._:-]): '$PROJ' — recusado antes de virar URL"
[[ "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]     || nao_executado "rótulo de branch fora do padrão ([A-Za-z0-9._/-]): '$BRANCH' — recusado antes de virar URL"
[ -z "$BASELINE" ] || [[ "$BASELINE" =~ ^[A-Za-z0-9._:-]+$ ]] \
                                          || nao_executado "chave de baseline fora do padrão ([A-Za-z0-9._:-]): '$BASELINE' — recusado antes de virar URL"

HOST="${SONAR_HOST_URL%/}"      # remove barra final se houver
# Sufixo de branch aplicado às consultas: só existe no modo legado.
Q_BRANCH=""; [ "$MODE" = "branch" ] && Q_BRANCH="&branch=$BRANCH"

# call_api <path> — faz a chamada, separa corpo (BODY) e código HTTP (CODE) e
# trata TODA falha como "não executado" com MOTIVO específico. O token vai por
# basic auth (-u "token:") e nunca é impresso; stderr descartado. Chamada DIRETA
# (não em $(...)) para os globais BODY/CODE sobreviverem — e, principalmente,
# para que `nao_executado` encerre o SCRIPT: dentro de uma substituição de
# comando ela mataria só a subshell e a falha viraria veredito inferido.
BODY=""; CODE=""
ALVO="$PROJ"      # projeto da consulta em curso (muda para o baseline na catraca)
call_api() {
  local raw
  raw="$(curl -sS -m 30 -u "$SONAR_TOKEN:" -w $'\n%{http_code}' "$HOST/api/$1" 2>/dev/null)" \
    || nao_executado "API do Sonar inacessível (SONAR_HOST_URL)"
  CODE="${raw##*$'\n'}"     # última linha = código HTTP
  BODY="${raw%$'\n'*}"      # tudo antes = corpo
  case "$CODE" in
    2*) : ;;
    401|403) nao_executado "SONAR_TOKEN inválido ou sem permissão (HTTP $CODE) — regenere o token (P2)" ;;
    404)     # N-2: a mensagem do modo trunk só vale quando o 404 é do projeto
             # MEDIDO. Com `--baseline` em modo trunk, o alvo da consulta é o
             # baseline — a mensagem antiga nomeava o projeto errado e mandava
             # o operador reescanear a demanda por um 404 do trunk.
             if [ "$MODE" = "branch" ] && [ "$ALVO" = "$PROJ" ]; then
               nao_executado "projeto '$PROJ' ou branch '$BRANCH' sem análise no Sonar (HTTP 404). Servidores sem análise multi-branch só têm branch no trunk. Para a branch de uma demanda, use o espelho: sonar-task.sh TASK-XXX && sonar-gate.sh --project <PROJECT_KEY>-TASK-XXX"
             fi
             nao_executado "projeto '$ALVO' não encontrado no Sonar (HTTP 404) — o espelho já foi publicado? rode faber/scripts/sonar-task.sh TASK-XXX (se '$ALVO' for o baseline, ele nunca é ignorado: sem baseline não há catraca)" ;;
    "")      nao_executado "sem código HTTP do Sonar (host/rede)" ;;
    *)       nao_executado "Sonar retornou HTTP $CODE em $1" ;;
  esac
  # 2xx que ainda traz {"errors":[...]} (ex.: parâmetro inválido)
  if echo "$BODY" | jq -e '.errors' >/dev/null 2>&1; then
    nao_executado "$(echo "$BODY" | jq -r '.errors[0].msg')"
  fi
  [ -n "$BODY" ] || nao_executado "resposta vazia do Sonar (host/rede)"
}

# coleta <projeto> <filtro> <arq-chaves> <arq-mapa> <sufixo-branch> — pagina
# issues/search gravando as CHAVES das issues (união exata dentro do projeto) e
# um MAPA `identidade<TAB>key<TAB>linha` (comparação ENTRE projetos, A-2).
# Deixa o total da API em N_TOTAL.
N_TOTAL=0
coleta() {
  local pag=1 total=0
  ALVO="$1"
  : > "$3" || nao_executado "não consegui escrever arquivo temporário"
  : > "$4" || nao_executado "não consegui escrever arquivo temporário"
  while : ; do
    call_api "issues/search?components=$1&resolved=false&$2&ps=500&p=$pag$5"
    total="$(echo "$BODY" | jq -r '.total // empty')"
    case "$total" in ''|*[!0-9]*) nao_executado "contagem de issues inválida do Sonar (projeto $1)" ;; esac
    # M-2: status do jq CHECADO. Uma página sem `.issues` (erro parcial, mudança
    # de contrato da API, resposta truncada) deixaria o arquivo curto e a união
    # subcontada — e união subcontada vira veredito "approved" falso.
    echo "$BODY" | jq -r '.issues[].key' >> "$3" \
      || nao_executado "resposta de issues/search sem o campo esperado (projeto $1, página $pag) — união não confiável"
    # Sem pipe direto para o awk: num pipeline o status é o do ÚLTIMO comando, e
    # uma falha do jq passaria despercebida (o mesmo defeito que M-2 aponta).
    echo "$BODY" | jq -r --arg p "$1" '
        .issues[]
        | [ .rule,
            (.component | ltrimstr($p + ":")),
            (.hash // ("L" + ((.line // 0) | tostring))),
            .key,
            ((.line // 0) | tostring) ]
        | @tsv' > "$3.pagina" \
      || nao_executado "não consegui montar a identidade das issues (projeto $1, página $pag)"
    awk -F'\t' 'NF>=5 {printf "%s|%s|%s\t%s\t%s\n", $1, $2, $3, $4, $5}' "$3.pagina" >> "$4" \
      || nao_executado "falha ao gravar a identidade das issues (projeto $1, página $pag)"
    # Teto duro do endpoint: ps*p <= 10000. Acima disso não dá para enumerar —
    # e um número inventado aqui seria pior que não responder.
    [ "$total" -gt 10000 ] && nao_executado "projeto '$1' com $total issues no filtro ($2): acima do teto de paginação da API (10000), impossível contar a união com exatidão"
    [ $(( pag * 500 )) -ge "$total" ] && break
    pag=$(( pag + 1 ))
  done
  N_TOTAL="$total"
}

# conta <projeto> <sufixo-branch> <prefixo> — define C_LEG (legacy), C_IMP
# (impacto) e C_UNI (união exata por key), e deixa em $TMPD/<prefixo>.ids as
# identidades comparáveis entre projetos. Sem substituição de comando: `coleta`
# precisa poder encerrar o script.
TMPD="$(mktemp -d)" || nao_executado "não consegui criar diretório temporário"
trap 'rm -rf "$TMPD"' EXIT
C_LEG=0; C_IMP=0; C_UNI=0
conta() {
  local alvo="$1" qb="$2" px="$3"
  coleta "$alvo" "severities=BLOCKER,CRITICAL"   "$TMPD/$px.a.keys" "$TMPD/$px.a.map" "$qb"; C_LEG="$N_TOTAL"
  coleta "$alvo" "impactSeverities=BLOCKER,HIGH" "$TMPD/$px.b.keys" "$TMPD/$px.b.map" "$qb"; C_IMP="$N_TOTAL"
  cat "$TMPD/$px.a.keys" "$TMPD/$px.b.keys" | LC_ALL=C sort -u > "$TMPD/$px.keys"
  cat "$TMPD/$px.a.map"  "$TMPD/$px.b.map"  | LC_ALL=C sort -u > "$TMPD/$px.map"
  C_UNI="$(grep -c . "$TMPD/$px.keys" | tr -d ' ')"
  case "$C_UNI" in ''|*[!0-9]*) nao_executado "falha ao calcular a união das issues do projeto $alvo" ;; esac
  cut -f1 "$TMPD/$px.map" | LC_ALL=C sort -u > "$TMPD/$px.ids"
  # M-2: a união NUNCA pode ser menor que qualquer uma das contagens da API.
  # Se for, alguma página não rendeu chaves e o número que decide o veredito
  # está errado — para em vez de aprovar com dado torto.
  { [ "$C_UNI" -ge "$C_LEG" ] && [ "$C_UNI" -ge "$C_IMP" ]; } \
    || nao_executado "união inconsistente com as contagens da API no projeto '$alvo' (união=$C_UNI, legacy=$C_LEG, impacto=$C_IMP) — chaves faltando na paginação"
}

# 0. Token válido? (diagnóstico limpo antes de qualquer gate)
call_api "authentication/validate"
[ "$(echo "$BODY" | jq -r '.valid // false')" = "true" ] \
  || nao_executado "SONAR_TOKEN inválido (authentication/validate=false) — regenere o token (P2)"

# 1. EXISTE análise? Guarda contra o pior fail-open possível: um projeto
# provisionado e nunca escaneado devolve QG=NONE e ZERO issues — o que passaria
# por "approved" sem ninguém ter analisado nada.
call_api "project_analyses/search?project=$PROJ&ps=1$Q_BRANCH"
[ "$(echo "$BODY" | jq -r '.analyses | length')" -gt 0 ] 2>/dev/null \
  || nao_executado "projeto '$PROJ' (modo $MODE) sem NENHUMA análise no Sonar — rode faber/scripts/sonar-task.sh antes do gate"
ANALYSIS="$(echo "$BODY" | jq -r '.analyses[0].date // "?"')"
REVISION="$(echo "$BODY" | jq -r '.analyses[0].revision // "?"')"

# 1b. A-1 — a análise é DESTE código? Sem esta conferência, `sonar-task.sh`
# rodado uma vez e três commits depois ainda devolveria "approved" sobre código
# que não existe mais. O `sonar-task.sh` já publica `sonar.scm.revision`; o
# que faltava era conferir do outro lado.
#
#   modo overall (espelho da demanda) → compara com o HEAD do worktree;
#   modo branch  (trunk)              → compara com refs/heads/<branch> OU
#                                       refs/remotes/origin/<branch> (N-2).
#
# Falha FECHADA em todos os "não dá para saber": fora de repositório git, sem
# `revision` publicada, ref local inexistente. O baseline da catraca NÃO passa
# por aqui de propósito — ele é ponto de referência (o trunk, no estado em que
# estiver), não o código sob julgamento.
[ "$REVISION" != "?" ] && [ -n "$REVISION" ] \
  || nao_executado "a última análise de '$PROJ' não publicou a revisão (sonar.scm.revision) — impossível provar que o veredito é do código avaliado; reescaneie com faber/scripts/sonar-task.sh"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || nao_executado "fora de um repositório git: impossível comparar a revisão analisada ($REVISION) com o código local — rode o gate a partir do worktree da demanda"
#
# N-2: no modo trunk, `refs/heads/<branch>` costuma estar velho — ou nem existir
# — num worktree de demanda (a fábrica isola cada demanda e nunca faz checkout de
# trunk). `refs/remotes/origin/<branch>` é o ref que `git fetch` de fato
# atualiza, então ele TAMBÉM vale como prova: qualquer ref local que aponte para
# o commit analisado prova a correspondência (é sempre o mesmo SHA sendo
# comparado; aceitar mais candidatos não afrouxa nada).
if [ "$MODE" = "overall" ]; then
  CANDIDATOS="HEAD"
else
  CANDIDATOS="refs/heads/$BRANCH refs/remotes/origin/$BRANCH"
fi
REF_LOCAL=""; REV_LOCAL=""; CONFERIDOS=""
for ref in $CANDIDATOS; do
  rev="$(git rev-parse --verify "$ref^{commit}" 2>/dev/null)" || rev=""
  [ -n "$rev" ] || continue
  CONFERIDOS="$CONFERIDOS $ref=${rev:0:12}"
  [ -n "$REF_LOCAL" ] || { REF_LOCAL="$ref"; REV_LOCAL="$rev"; }   # 1º que resolve
  if [ "$rev" = "$REVISION" ]; then REF_LOCAL="$ref"; REV_LOCAL="$rev"; break; fi
done
[ -n "$REV_LOCAL" ] \
  || nao_executado "nenhuma referência local resolvida entre '$CANDIDATOS' — sem isso não dá para provar que a análise ($REVISION) corresponde ao código avaliado. No modo trunk, é 'git fetch origin $BRANCH' que atualiza refs/remotes/origin/$BRANCH (o ref conferido aqui); 'git fetch' sozinho NÃO move refs/heads/$BRANCH"
[ "$REV_LOCAL" = "$REVISION" ] \
  || nao_executado "a análise publicada de '$PROJ' é do commit ${REVISION:0:12}, mas os refs locais estão em${CONFERIDOS} — veredito recusado sobre código diferente do analisado; no modo espelho rode faber/scripts/sonar-task.sh de novo, no modo trunk rode 'git fetch origin $BRANCH' (atualiza refs/remotes/origin/$BRANCH; 'git fetch' sozinho NÃO move refs/heads/$BRANCH)"

# 2. Quality Gate — INFORMATIVO (D-2). Não entra no veredito.
call_api "qualitygates/project_status?projectKey=$PROJ$Q_BRANCH"
QG="$(echo "$BODY" | jq -r '.projectStatus.status // "NONE"')"

# 3. Critical/High pela união dos dois modelos de severidade.
conta "$PROJ" "$Q_BRANCH" "proj"
P_LEG="$C_LEG"; P_IMP="$C_IMP"; P_UNI="$C_UNI"

echo "PROJECT=$PROJ"
echo "BRANCH=$BRANCH"
echo "MODE=$MODE"
echo "ANALYSIS=$ANALYSIS"
echo "REVISION=$REVISION"
echo "REVISION_CHECKED=$REF_LOCAL=$REV_LOCAL"
echo "QUALITY_GATE=$QG (informativo — D-2: não bloqueia o G5)"
echo "CRITICAL_LEGACY=$P_LEG"
echo "HIGH_IMPACT=$P_IMP"
echo "CRITICAL_HIGH=$P_UNI"

# 4. Catraca (D-3 + A-2): baseline lido NA HORA, nunca um número fixo em arquivo
# — a dívida se move sozinha e um limite escrito à mão nasce velho. O que
# reprova é a DIFERENÇA DE CONJUNTOS (issue no projeto medido que não existe no
# baseline), não a comparação de totais: trocar 5 herdadas por 5 novas passava
# como "não piorou".
if [ -n "$BASELINE" ]; then
  conta "$BASELINE" "" "base"
  echo "BASELINE_PROJECT=$BASELINE"
  echo "BASELINE_CRITICAL_LEGACY=$C_LEG"
  echo "BASELINE_HIGH_IMPACTO=$C_IMP"
  echo "BASELINE_CRITICAL_HIGH=$C_UNI"

  LC_ALL=C comm -23 "$TMPD/proj.ids" "$TMPD/base.ids" > "$TMPD/novas.ids" \
    || nao_executado "falha ao comparar os conjuntos de issues (projeto x baseline)"
  NOVAS="$(grep -c . "$TMPD/novas.ids" | tr -d ' ')"
  case "$NOVAS" in ''|*[!0-9]*) nao_executado "falha ao contar as issues novas em relação ao baseline" ;; esac
  echo "NEW_VS_BASELINE=$NOVAS"

  if [ "$NOVAS" -gt 0 ]; then
    # As identidades novas, com a key da issue no projeto medido (para abrir no
    # servidor). Teto de 50 linhas: a evidência precisa ser legível.
    while IFS= read -r id; do
      [ -n "$id" ] || continue
      det="$(awk -F'\t' -v i="$id" '$1==i {print "key="$2" linha="$3; exit}' "$TMPD/proj.map")"
      echo "NEW=$id $det"
    done < <(head -50 "$TMPD/novas.ids")
    [ "$NOVAS" -gt 50 ] && echo "NEW=... (${NOVAS} no total; 50 listadas)"
    echo "RATCHET=issue-nova"
    echo "REASON=$NOVAS issue(s) Critical/High existem em '$PROJ' e NÃO existem no baseline '$BASELINE' — a demanda introduziu dívida nova (D-3/§18-G5: não excepcionável). Identidade = regra|caminho|hash da linha"
    echo "VERDICT=rejected"; exit 2
  fi

  if [ "$P_UNI" -eq 0 ]; then echo "RATCHET=zero"; else
    echo "RATCHET=sem-novas ($P_UNI herdada(s) do baseline, 0 nova(s))"
    echo "REASON=dívida herdada de $P_UNI Critical/High, toda ela já presente no baseline '$BASELINE' — aprovado pela catraca (D-3); a meta continua sendo zero"
  fi
  echo "VERDICT=approved"; exit 0
fi

# 5. Sem catraca: a régua é zero (§18-G5).
if [ "$P_UNI" -eq 0 ]; then
  echo "VERDICT=approved"; exit 0
fi
echo "REASON=$P_UNI issue(s) Critical/High abertas (legacy=$P_LEG, impacto=$P_IMP) — §18-G5: não excepcionável"
echo "VERDICT=rejected"; exit 2
