#!/bin/bash
# =============================================================================
# sonar-token-check.sh — testa se o par (SONAR_TOKEN, host) autentica no Sonar.
# Diagnóstico rápido (zero LLM), separado do sonar-gate.sh (que roda o gate).
# P2: o token entra por NOME via env (nunca em arg/arquivo) e NUNCA é impresso.
#
# Uso:
#   SONAR_TOKEN=<token> faber/scripts/sonar-token-check.sh [host-url]
#     host-url  opcional; default = $SONAR_HOST_URL
#   Ex.: SONAR_TOKEN=squ_xxx faber/scripts/sonar-token-check.sh \
#          https://sonar.exemplo.com/
#
# Saída = linhas CHAVE=VALOR + exit code:
#   0  token-valido
#   2  token-invalido      (authentication/validate=false)
#   3  not-executed       (token/host ausente, host off, HTTP inesperado)
# =============================================================================
set -u

HOST_IN="${1:-${SONAR_HOST_URL:-}}"

falha() { echo "RESULTADO=$1"; echo "REASON=$2"; exit "$3"; }

[ -n "${SONAR_TOKEN:-}" ] || falha not-executed "SONAR_TOKEN ausente — use: SONAR_TOKEN=... $0 <host> (P2)" 3
[ -n "$HOST_IN" ]         || falha not-executed "host ausente — passe como arg ou defina SONAR_HOST_URL" 3
command -v curl >/dev/null 2>&1 || falha not-executed "curl ausente" 3
command -v jq   >/dev/null 2>&1 || falha not-executed "jq ausente" 3

HOST="${HOST_IN%/}"     # remove barra final se houver

# 1. host alcançável? (endpoint público, NÃO usa o token)
code="$(curl -sS -m 20 -o /dev/null -w '%{http_code}' "$HOST/api/system/status" 2>/dev/null)" \
  || falha not-executed "host inacessível ($HOST)" 3
[ "$code" = "200" ] || falha not-executed "host respondeu HTTP $code em /api/system/status (URL errada?)" 3

# 2. token válido? (basic auth -u "token:"; corpo = {"valid":true|false})
resp="$(curl -sS -m 20 -u "$SONAR_TOKEN:" -w $'\n%{http_code}' "$HOST/api/authentication/validate" 2>/dev/null)" \
  || falha not-executed "falha ao consultar authentication/validate ($HOST)" 3
vcode="${resp##*$'\n'}"     # última linha = código HTTP
vbody="${resp%$'\n'*}"      # tudo antes = corpo
[ "$vcode" = "200" ] || falha not-executed "authentication/validate retornou HTTP $vcode" 3

echo "HOST=$HOST"
if [ "$(echo "$vbody" | jq -r '.valid // false')" = "true" ]; then
  echo "RESULTADO=token-valido"; exit 0
fi
echo "RESULTADO=token-invalido"
echo "REASON=authentication/validate=false (token revogado, expirado ou incorreto)"
exit 2
