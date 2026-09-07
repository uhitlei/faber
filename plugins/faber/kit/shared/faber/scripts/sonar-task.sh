#!/bin/bash
# =============================================================================
# sonar-task.sh — analisa a branch da demanda no SonarQube, LOCALMENTE,
# publicando num projeto-espelho `<PROJECT_KEY>-TASK-XXX` (zero LLM).
#
# Por que existe (TASK-118, decisão D-8 do G1): o servidor é Community
# Edition — não há análise multi-branch nem decoração de PR (evidência 02).
# Rodar o scanner numa feature branch contra o projeto do trunk SOBRESCREVERIA o
# trunk com código não mergeado. O contorno aprovado é um projeto por demanda,
# medido em *overall* (num projeto novo todo o código é "new code", então as
# condições `new_*` são estruturalmente inúteis), provisionado no primeiro scan
# e apagado no G9 (subcomando `apagar`).
#
# D-8 também tirou isto do CI: quem escaneia a demanda é a fábrica, na máquina
# local, com o token local (que tem `provisioning`). O CI continua analisando
# só o trunk, em push ao trunk/produção.
#
# Uso:
#   sonar-task.sh <TASK-XXX> [--branch <nome>] [--sem-cobertura]
#   sonar-task.sh apagar <TASK-XXX>
#
#   --branch        rótulo gravado no veredito (default: branch git atual).
#                   NÃO vira `sonar.branch.name` (indisponível no Community);
#                   entra como metadado da análise.
#   --sem-cobertura pula `npm run test:coverage` e EXIGE coverage/lcov.info já
#                   presente E mais novo que o último commit (falha se não
#                   houver ou se estiver velho — nunca escaneia sem cobertura em
#                   silêncio, senão `coverage` volta a 0.0 por omissão, nem
#                   publica cobertura de outro código como se fosse deste).
#
# Secrets por NOME (P2): SONAR_TOKEN e SONAR_HOST_URL vêm do ambiente ou, se
# ausentes, de um arquivo de env local NÃO versionado (SONAR_ENV_FILE, ou
# `.env.sonar` na raiz do repositório principal — worktrees inclusive).
# Nenhum valor é impresso, em nenhum caminho de código.
#
# FALHA FECHADO (lição da TASK-114): qualquer erro — token, rede, testes,
# scanner, processamento no servidor — encerra com exit != 0 e MOTIVO explícito.
# Sucesso significa "análise publicada e processada", nunca "o comando rodou".
#
# Exit codes:
#   0  ok            análise publicada e processada pelo servidor
#   1  uso           argumentos inválidos
#   3  nao-executado pré-requisito ausente (token/host/rede/ferramenta)
#   4  cobertura     `npm run test:coverage` falhou ou não gerou lcov.info
#   5  scanner       o sonar-scanner terminou com erro
#   6  servidor      a tarefa de processamento (Compute Engine) falhou/expirou
# =============================================================================
set -u
# shellcheck source=lib/config.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/config.sh"
faber_require_install

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$DIR/../.." && pwd)"          # raiz do worktree em uso

falha() { echo "RESULTADO=falha"; echo "MOTIVO=$1"; exit "$2"; }
uso() {
  echo "uso: sonar-task.sh <TASK-XXX> [--branch <nome>] [--sem-cobertura]"
  echo "     sonar-task.sh apagar <TASK-XXX>"
  exit 1
}

# --- 0. Argumentos -----------------------------------------------------------
[ $# -ge 1 ] || uso
ACAO="analisar"
if [ "$1" = "apagar" ]; then ACAO="apagar"; shift; [ $# -ge 1 ] || uso; fi

TASK="$1"; shift
# `[[ =~ ]]` e não `grep -qE`: o grep casa POR LINHA, então
# $'TASK-1\nqualquer' passaria na validação (B-1 do review). O `[[ ]]` do bash
# 3.2 não tem semântica de linha — o valor inteiro precisa casar.
[[ "$TASK" =~ ^TASK-[0-9]+$ ]] \
  || falha "demanda '$TASK' fora do padrão TASK-<numero>" 1

BRANCH=""; COBERTURA="sim"
while [ $# -gt 0 ]; do
  case "$1" in
    --branch)        [ $# -ge 2 ] || uso; BRANCH="$2"; shift 2 ;;
    --sem-cobertura) COBERTURA="nao"; shift ;;
    *) uso ;;
  esac
done
[ -n "$BRANCH" ] || BRANCH="$(git -C "$RAIZ" rev-parse --abbrev-ref HEAD 2>/dev/null)"

# PROTEÇÃO: a chave do espelho é derivada da demanda e casada com um padrão
# estrito. É o que impede `apagar` de encostar no projeto real do trunk — a chave
# nunca pode ser a do trunk porque sempre carrega o sufixo -TASK-<numero>.
[ -n "${FABER_SONAR_PROJECT_KEY:-}" ] || falha "FABER_SONAR_PROJECT_KEY vazio em faber/config/faber.env" 3
PROJ="${FABER_SONAR_PROJECT_KEY}-$TASK"
[[ "$PROJ" =~ ^"$FABER_SONAR_PROJECT_KEY"-TASK-[0-9]+$ ]] \
  || falha "chave de projeto derivada inválida ('$PROJ') — abortado por segurança" 1

# --- 1. Ferramentas ----------------------------------------------------------
command -v curl >/dev/null 2>&1 || falha "curl ausente" 3
command -v jq   >/dev/null 2>&1 || falha "jq ausente" 3

# --- 2. Secrets por NOME -----------------------------------------------------
# Carrega do arquivo local só o que faltar no ambiente. `git rev-parse
# --git-common-dir` devolve o .git do repositório PRINCIPAL mesmo quando o
# script roda de um worktree (a fábrica isola cada demanda em worktree, e o
# .env.sonar mora só na raiz principal).
if [ -z "${SONAR_TOKEN:-}" ] || [ -z "${SONAR_HOST_URL:-}" ]; then
  ENV_FILE="${SONAR_ENV_FILE:-}"
  if [ -z "$ENV_FILE" ]; then
    # B-3: `--path-format=absolute` exige git >= 2.31. Com git antigo o comando
    # falha, `dirname ""` devolveria "." e o candidato viraria "./.env.sonar",
    # relativo ao cwd de QUEM CHAMOU — um arquivo de env inesperado poderia ser
    # carregado. O retorno é checado: sem ele, só o candidato do worktree vale.
    COMMON="$(git -C "$RAIZ" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || COMMON=""
    case "$COMMON" in /*) PRINCIPAL="$(dirname "$COMMON")" ;; *) PRINCIPAL="" ;; esac
    for cand in "$RAIZ/.env.sonar" ${PRINCIPAL:+"$PRINCIPAL/.env.sonar"}; do
      [ -f "$cand" ] && { ENV_FILE="$cand"; break; }
    done
  fi
  [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ] \
    || falha "SONAR_TOKEN/SONAR_HOST_URL ausentes no ambiente e nenhum arquivo de env encontrado (defina SONAR_ENV_FILE ou crie .env.sonar na raiz do repositório principal; com git < 2.31 o worktree não enxerga a raiz principal) — P2" 3
  # PRESSUPOSTO EXPLÍCITO (B-4): `. "$ENV_FILE"` EXECUTA o arquivo e exporta
  # tudo que ele definir. O arquivo é local, não versionado e escolhido pelo
  # operador (SONAR_ENV_FILE ou .env.sonar da raiz) — quem controla esse arquivo
  # já executa código nesta máquina. Não é fronteira de segurança; é conveniência
  # administrativa. Nunca aponte SONAR_ENV_FILE para arquivo de terceiro.
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE" || falha "falha ao ler o arquivo de env (caminho: ${ENV_FILE##*/})" 3
  set +a
fi
[ -n "${SONAR_TOKEN:-}" ]    || falha "SONAR_TOKEN ausente (P2 — por nome, nunca em arquivo versionado)" 3
[ -n "${SONAR_HOST_URL:-}" ] || falha "SONAR_HOST_URL ausente (P2)" 3
HOST="${SONAR_HOST_URL%/}"

# api <metodo> <path> — chama a API e devolve o corpo em BODY; qualquer HTTP
# fora de 2xx encerra o script. O token vai por basic auth e nunca é impresso.
BODY=""; CODE=""
api() {
  local raw
  raw="$(curl -sS -m 60 -X "$1" -u "$SONAR_TOKEN:" -w $'\n%{http_code}' "$HOST/api/$2" 2>/dev/null)" \
    || falha "API do Sonar inacessível (host de SONAR_HOST_URL)" 3
  CODE="${raw##*$'\n'}"; BODY="${raw%$'\n'*}"
  case "$CODE" in
    2*) : ;;
    401|403) falha "SONAR_TOKEN inválido ou sem permissão (HTTP $CODE) — regenere o token (P2)" 3 ;;
    "")      falha "sem código HTTP do Sonar (host/rede)" 3 ;;
    *)       falha "Sonar retornou HTTP $CODE em $2" 3 ;;
  esac
}

api GET "authentication/validate"
[ "$(echo "$BODY" | jq -r '.valid // false')" = "true" ] \
  || falha "SONAR_TOKEN inválido (authentication/validate=false) — regenere o token (P2)" 3

# --- 3. Subcomando `apagar` (faxina do G9) -----------------------------------
if [ "$ACAO" = "apagar" ]; then
  # Idempotente: projeto inexistente não é erro (o G9 pode rodar duas vezes).
  raw="$(curl -sS -m 60 -X POST -u "$SONAR_TOKEN:" -w $'\n%{http_code}' \
         "$HOST/api/projects/delete?project=$PROJ" 2>/dev/null)" \
    || falha "API do Sonar inacessível (host de SONAR_HOST_URL)" 3
  code="${raw##*$'\n'}"
  case "$code" in
    2*)  echo "PROJECT=$PROJ"; echo "RESULTADO=apagado"; exit 0 ;;
    404) echo "PROJECT=$PROJ"; echo "RESULTADO=inexistente (nada a apagar)"; exit 0 ;;
    401|403) falha "sem permissão para apagar '$PROJ' (HTTP $code) — o token precisa de 'Administer' no projeto" 3 ;;
    *)   falha "falha ao apagar '$PROJ' (HTTP $code)" 3 ;;
  esac
fi

# --- 4. Cobertura ------------------------------------------------------------
LCOV="$RAIZ/coverage/lcov.info"
if [ "$COBERTURA" = "sim" ]; then
  echo "→ gerando cobertura (npm run test:coverage)…"
  ( cd "$RAIZ" && npm run test:coverage ) \
    || falha "npm run test:coverage falhou — sem cobertura confiável, a análise mediria 0.0 e o veredito seria falso" 4
fi
[ -s "$LCOV" ] || falha "coverage/lcov.info ausente ou vazio em $RAIZ (rode sem --sem-cobertura)" 4

# B-9 (review): "existe e não está vazio" aceitava um lcov gerado noutra branch,
# dias antes, e o publicava como cobertura DESTA análise — mesma família do A-1
# (dado aceito sem prova de que corresponde ao código). Com --sem-cobertura, o
# relatório precisa ser MAIS NOVO que o último commit.
if [ "$COBERTURA" = "nao" ]; then
  MT="$(stat -f %m "$LCOV" 2>/dev/null)" || MT="$(stat -c %Y "$LCOV" 2>/dev/null)" || MT=""
  CT="$(git -C "$RAIZ" log -1 --format=%ct 2>/dev/null)" || CT=""
  { [ -n "$MT" ] && [ -n "$CT" ]; } \
    || falha "não consegui datar coverage/lcov.info ou o último commit (stat/git) — sem isso não dá para provar que a cobertura é deste código; rode sem --sem-cobertura" 4
  [ "$MT" -ge "$CT" ] \
    || falha "coverage/lcov.info é ANTERIOR ao último commit (lcov=$MT, commit=$CT, epoch) — publicaria cobertura de outro código; rode sem --sem-cobertura" 4
fi

# --- 5. Scanner --------------------------------------------------------------
# `npx @sonar/scan` (wrapper npm oficial do sonar-scanner CLI): não exige Java
# nem Docker na máquina — baixa o scanner na primeira execução e o mantém em
# cache. As propriedades de escopo/cobertura vêm do sonar-project.properties;
# aqui só sobrescrevemos a identidade do projeto-espelho.
#
# M-7 (review): a versão é FIXA. `npx --yes @sonar/scan` sem versão baixava e
# executava a ÚLTIMA publicada — num processo que recebe SONAR_TOKEN no
# ambiente (superfície de supply chain) e com o efeito colateral de tornar a
# medição não reprodutível (mesma branch, números diferentes por troca de
# scanner). Ao subir a versão, atualize aqui de propósito, com evidência.
SCANNER_PKG="@sonar/scan@5.0.0"
command -v npx >/dev/null 2>&1 || falha "npx ausente (Node.js não instalado?)" 3
VERSAO="$(node -p "require('$RAIZ/package.json').version" 2>/dev/null)" || VERSAO=""
REV="$(git -C "$RAIZ" rev-parse HEAD 2>/dev/null)" || REV=""
CARIMBO="${VERSAO:-0}-$TASK"

# M-3 (review/AC-7): o VALOR de SONAR_HOST_URL não aparece em nenhuma saída —
# só o nome. O que o scanner imprime por conta própria (Server URL, links do
# relatório) é mascarado no pipe abaixo. O token também é mascarado ali: NUNCA
# rode este scanner com `-Dsonar.verbose=true` fora deste pipe — o modo verboso
# do scanner despeja TODAS as propriedades, incluindo `sonar.token` em claro
# (medido nesta demanda, ao investigar o M-5).
# As chaves em ${REV:0:8} e ${SCANNER_PKG} são de propósito: colada num
# caractere multibyte (as reticências), a variável tem os bytes engolidos no
# nome pelo bash 3.2 do macOS e o script morre com "unbound variable"
# (evidência 04 na primeira rodada; evidência 23, pelo mesmo motivo, na segunda).
echo "→ escaneando $PROJ (branch $BRANCH, revisão ${REV:0:8}) no host de SONAR_HOST_URL, com ${SCANNER_PKG}…"

# N-1 (re-review): a máscara vai para um ARQUIVO de script do sed (`-f`), nunca
# para a linha de comando — o valor do token na linha de comando fica visível em
# `ps` para qualquer processo local (mesma família do B-2, aceito para o curl,
# mas aqui era gratuito). O arquivo nasce com umask 077 + chmod 600.
# Duas regras para o host: a URL inteira e o host SEM ESQUEMA — uma linha do
# scanner que imprima só o hostname escapava da máscara antiga.
# O delimitador do `s///` é escolhido entre candidatos que NÃO aparecem no valor
# (com `#` fixo, um token contendo `#` quebrava a expressão). Não achou
# delimitador → falha fechado: melhor não escanear do que despejar o valor.
UMASK_ANT="$(umask)"; umask 077
SEDF="$(mktemp "${TMPDIR:-/tmp}/sonar-mask.XXXXXX")" \
  || falha "não consegui criar o arquivo temporário da máscara de saída" 3
chmod 600 "$SEDF" 2>/dev/null
umask "$UMASK_ANT"      # restaurado: o scanner cria .scannerwork logo abaixo
trap 'rm -f "$SEDF"' EXIT
regra_mascara() {   # regra_mascara <valor> <substituto>
  local v="$1" sub="$2" d
  [ -n "$v" ] || return 0
  for d in '#' '%' '@' '|' '^' '!' ',' '~'; do
    case "$v" in *"$d"*) continue ;; esac
    printf 's%s%s%s%s%sg\n' "$d" "$v" "$d" "$sub" "$d" >> "$SEDF"
    return 0
  done
  return 1
}
regra_mascara "$HOST"          '$SONAR_HOST_URL' || falha "não consegui montar a máscara do host (valor com todos os delimitadores possíveis) — abortado para não imprimir o valor" 3
regra_mascara "${HOST#*://}"   '$SONAR_HOST_URL' || falha "não consegui montar a máscara do host sem esquema — abortado para não imprimir o valor" 3
regra_mascara "$SONAR_TOKEN"   '$SONAR_TOKEN'    || falha "não consegui montar a máscara do token — abortado para não imprimir o valor" 3

rm -rf "$RAIZ/.scannerwork"
# pipefail localizado: sem ele o status do pipe seria o do `sed` e um scanner
# quebrado passaria por sucesso — fail-open pela porta dos fundos.
set -o pipefail
( cd "$RAIZ" && SONAR_TOKEN="$SONAR_TOKEN" SONAR_HOST_URL="$HOST" npx --yes "$SCANNER_PKG" \
    -Dsonar.projectKey="$PROJ" \
    -Dsonar.projectName="$PROJ" \
    -Dsonar.projectVersion="$CARIMBO" \
    -Dsonar.scm.revision="$REV" \
    -Dsonar.working.directory=.scannerwork ) 2>&1 \
    | sed -f "$SEDF" \
  || falha "sonar-scanner falhou (veja a saída acima) — nada foi publicado para '$PROJ'" 5
set +o pipefail
rm -f "$SEDF"

TASKFILE="$RAIZ/.scannerwork/report-task.txt"
[ -f "$TASKFILE" ] || falha "scanner não gerou report-task.txt — impossível confirmar a publicação" 5
CE_ID="$(sed -n 's/^ceTaskId=//p' "$TASKFILE" | head -1)"
[ -n "$CE_ID" ] || falha "report-task.txt sem ceTaskId — impossível confirmar a publicação" 5

# --- 6. Esperar o servidor processar -----------------------------------------
# O scanner só ENVIA o relatório; a análise vira medida depois, numa tarefa
# assíncrona. Retornar 0 aqui sem esperar faria o sonar-gate.sh ler dados
# velhos (ou nenhum) e emitir veredito falso — exatamente o fail-open que esta
# demanda existe para eliminar.
echo "→ aguardando o processamento no servidor (tarefa $CE_ID)…"
STATUS=""
for _ in $(seq 1 120); do          # 120 x 5s = 10 min de teto
  api GET "ce/task?id=$CE_ID"
  STATUS="$(echo "$BODY" | jq -r '.task.status // empty')"
  case "$STATUS" in
    SUCCESS)                 break ;;
    FAILED|CANCELED)         falha "o servidor rejeitou a análise (tarefa $CE_ID: $STATUS)" 6 ;;
    PENDING|IN_PROGRESS|"")  sleep 5 ;;
    *)                       falha "estado desconhecido da tarefa $CE_ID: $STATUS" 6 ;;
  esac
done
[ "$STATUS" = "SUCCESS" ] || falha "a análise não terminou de processar em 10 min (tarefa $CE_ID: ${STATUS:-sem status})" 6

echo "PROJECT=$PROJ"
echo "BRANCH=$BRANCH"
echo "REVISION=$REV"
echo "VERSION=$CARIMBO"
echo "SCANNER=$SCANNER_PKG"
echo "RESULTADO=publicado"
echo "PROXIMO=faber/scripts/sonar-gate.sh --project $PROJ --branch $BRANCH"
exit 0
