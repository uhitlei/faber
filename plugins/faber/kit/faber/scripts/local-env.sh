#!/bin/bash
# =============================================================================
# local-env.sh — ambiente LOCAL descartável da fábrica (zero LLM).
# ARQUITETURA §11 (Skill local-env), P4 (autonomia total AQUI — e somente aqui).
#
# Delega aos comandos configurados em faber/config/faber.env:
#   FABER_CMD_LOCAL_UP · _STATUS · _RESET · _SEED · _STOP
# (ex.: docker compose up -d · docker compose ps · docker compose down -v &&
#  docker compose up -d && npm run db:migrate · npm run db:seed · docker compose down)
#
# Uso: local-env.sh {up|status|reset|seed|stop|report}
#
# GUARD ESTRUTURAL: as operações destrutivas (reset/seed) só rodam se nenhum
# token de FABER_REFS_DENY/FABER_REFS_CONFIRM aparecer no comando
# configurado e se as variáveis de conexão visíveis (DATABASE_URL, DB_URL,
# *_DB_URL) — quando existirem — apontarem para 127.0.0.1/localhost. Isto é
# defesa em profundidade: o H1 já barra refs remotos em qualquer comando.
# Exit: 0 ok · 1 guard/uso · 2 módulo desligado/comando não configurado ·
#       3 não executado (dependência indisponível) · outro = exit do comando.
# =============================================================================
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
. "$DIR/lib/config.sh"
faber_require_install
cd "$FABER_ROOT" || exit 2

[ "$FABER_LOCAL_ENV" = "on" ] || { echo "NAO_EXECUTADO: módulo local-env desligado (FABER_LOCAL_ENV=off em faber/config/faber.env)"; exit 2; }

cmd_de() {  # cmd_de <NOME> -> imprime o comando configurado ou falha
  local var="FABER_CMD_LOCAL_$1" val
  val="${!var:-}"
  [ -n "$val" ] || { echo "NAO_EXECUTADO: $var não configurado em faber/config/faber.env"; exit 2; }
  echo "$val"
}

guard_local() {  # guard_local <comando>
  local c="$1" tok
  for tok in $(echo "$FABER_REFS_DENY,$FABER_REFS_CONFIRM" | tr ',' ' '); do
    [ -n "$tok" ] && case "$c" in *"$tok"*) echo "GUARD: comando contém ref remoto '$tok' — operação destrutiva só no ambiente LOCAL"; return 1 ;; esac
  done
  local v
  for v in DATABASE_URL DB_URL; do
    local url="${!v:-}"
    if [ -n "$url" ]; then
      case "$url" in *127.0.0.1*|*localhost*|*host.docker.internal*) ;; *) echo "GUARD: $v aponta para alvo não-local — recuso operação destrutiva"; return 1 ;; esac
    fi
  done
  return 0
}

roda() {  # roda <rótulo> <comando>
  echo "→ $1: $2"
  bash -c "$2"
  local rc=$?
  echo "← $1: exit $rc"
  return $rc
}

case "${1:-}" in
  up)     roda up "$(cmd_de UP)" ;;
  status) roda status "$(cmd_de STATUS)" ;;
  stop)   roda stop "$(cmd_de STOP)" ;;
  reset)  c=$(cmd_de RESET) || exit $?; guard_local "$c" || exit 1; roda reset "$c" ;;
  seed)   c=$(cmd_de SEED)  || exit $?; guard_local "$c" || exit 1; roda seed "$c" ;;
  report)
    echo "== local-env report ($(date +%Y-%m-%dT%H:%M:%S%z)) =="
    for k in UP STATUS RESET SEED STOP; do v="FABER_CMD_LOCAL_$k"; echo "$v=${!v:-<não configurado>}"; done
    if [ -n "${FABER_CMD_LOCAL_STATUS:-}" ]; then roda status "$FABER_CMD_LOCAL_STATUS" || true; fi
    ;;
  *) echo "uso: local-env.sh {up|status|reset|seed|stop|report}"; exit 1 ;;
esac
