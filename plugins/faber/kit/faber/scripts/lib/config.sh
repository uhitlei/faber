#!/bin/bash
# =============================================================================
# lib/config.sh — carrega faber/config/faber.env com defaults (zero LLM).
# Use:  . "$(dirname "${BASH_SOURCE[0]}")/lib/config.sh"   (nos scripts)
# Expõe: FABER_ROOT (raiz do checkout atual), FABER_CONFIG (path do env)
# e todas as FABER_* com defaults seguros. Nunca imprime valores de secret.
# =============================================================================
faber_root() {
  local r
  r=$(git rev-parse --show-toplevel 2>/dev/null) && { echo "$r"; return; }
  # fora de git: dois níveis acima de faber/scripts/lib
  echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
}
FABER_ROOT="${FABER_ROOT:-$(faber_root)}"
FABER_CONFIG="${FABER_CONFIG:-$FABER_ROOT/faber/config/faber.env}"
if [ -f "$FABER_CONFIG" ]; then
  FABER_INSTALLED=1
  # shellcheck source=/dev/null
  . "$FABER_CONFIG"
else
  FABER_INSTALLED=0
fi

# faber_require_install — guarda estrita. Nenhum script operacional roda numa
# arvore onde a fabrica nao foi instalada: sem faber/config/faber.env nao ha
# owner, branches nem comandos de validacao, e cair em defaults produziria
# gates aprovados contra a configuracao errada. Falha ruidosa, nunca silenciosa.
# FABER_SKIP_INSTALL_CHECK=1 libera (usado pelas suites em sandbox).
faber_require_install() {
  [ "${FABER_SKIP_INSTALL_CHECK:-0}" = "1" ] && return 0
  [ "$FABER_INSTALLED" = "1" ] && return 0
  echo "ERRO: Faber nao esta instalado nesta arvore." >&2
  echo "      esperado: $FABER_CONFIG" >&2
  echo "      instale com:  /faber:install   (plugin do Claude Code)" >&2
  echo "                ou:  bash install.sh $FABER_ROOT" >&2
  exit 1
}
: "${FABER_PROJECT:=Projeto}"
: "${FABER_OWNER:=owner}"
: "${FABER_OWNER_NAME:=Owner}"
: "${FABER_LANG:=pt-BR}"
: "${FABER_REMOTE:=origin}"
: "${FABER_TRUNK:=develop}"
: "${FABER_MAIN:=main}"
: "${FABER_WORKTREES:=on}"
: "${FABER_INTERACTION:=gates}"
: "${FABER_GH:=on}"
: "${FABER_GH_REPO:=}"
: "${FABER_BOARD:=off}"
: "${FABER_GH_PROJECT_TITLE:=}"
: "${FABER_SPECS_DIR:=specs}"
: "${FABER_CMD_LINT:=npm run lint}"
: "${FABER_CMD_BUILD:=npm run build}"
: "${FABER_CMD_TEST:=npm run test}"
: "${FABER_E2E:=off}"
: "${FABER_CMD_E2E:=npx playwright test}"
: "${FABER_E2E_CMD_REGEX:=playwright\S*\s+test\b}"
: "${FABER_E2E_SUMMARY_REGEX:=\d+\s+passed\b}"
: "${FABER_E2E_FAIL_REGEX:=\d+\s+failed\b}"
: "${FABER_MIGRATIONS_DIR:=}"
: "${FABER_MIGRATION_CHECKS:=}"
: "${FABER_PROTECTED_PATHS:=}"
: "${FABER_SECRET_FILES:=.env,.env.local}"
: "${FABER_REFS_DENY:=}"
: "${FABER_REFS_CONFIRM:=}"
: "${FABER_CMDS_DENY:=}"
: "${FABER_CMDS_CONFIRM:=}"
: "${FABER_SONAR:=off}"
: "${FABER_SONAR_PROJECT_KEY:=}"
: "${FABER_LOCAL_ENV:=off}"
: "${FABER_DESIGN_SYSTEM:=off}"
: "${FABER_DASHBOARD:=off}"

# owner/repo do GitHub: config > remote
faber_gh_repo() {
  if [ -n "$FABER_GH_REPO" ]; then echo "$FABER_GH_REPO"; return; fi
  local url
  url=$(git -C "$FABER_ROOT" remote get-url "$FABER_REMOTE" 2>/dev/null) || return 1
  url="${url%.git}"
  case "$url" in
    git@*:*)   echo "${url#*:}" ;;
    http*://*) echo "$url" | sed -E 's#^https?://[^/]+/##' ;;
    *) return 1 ;;
  esac
}
