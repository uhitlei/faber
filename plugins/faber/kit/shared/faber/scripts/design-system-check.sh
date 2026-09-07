#!/bin/bash
# =============================================================================
# design-system-check.sh — checklist executável do Design System (zero LLM).
# ARQUITETURA §11 (Skill design-system-check); specs 02-DESIGN-SYSTEM (regra de
# ouro: ZERO cor hardcoded — tudo vem de tokens semânticos em src/index.css,
# consumidos via classes Tailwind: bg-primary, text-foreground, border-border).
#
# Detecta por grep (o que a máquina pega): (a) cor hex em classe arbitrária
# Tailwind `[#...]`; (b) utilitárias de cor absolutas `text/bg/border-white|black`.
# NÃO cobre 44px, dark+light e reuso de componente — esses ficam no checklist
# MANUAL da Skill (o grep não vê layout renderizado).
#
# Uso: design-system-check.sh [arquivo|dir ...]
#   sem args → arquivos .tsx/.ts/.css ALTERADOS vs <remote>/<trunk> (escopo da demanda).
#   src/index.css e tailwind.config.ts são excluídos (é onde as cores moram).
#
# Saída = CHAVE=VALOR + exit: 0 conforme · 2 violações · 3 not-executed.
# =============================================================================
set -u
# shellcheck source=lib/config.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/config.sh"
faber_require_install

nao_executado() { echo "VERDICT=not-executed"; echo "REASON=$1"; exit 3; }
command -v grep >/dev/null 2>&1 || nao_executado "grep ausente"

# 1. alvos: args explícitos, ou o diff vs o trunk (bash 3.2 — sem mapfile)
if [ "$#" -gt 0 ]; then
  ARQS=$(printf '%s\n' "$@")
else
  command -v git >/dev/null 2>&1 || nao_executado "sem args e git ausente"
  # git diff sai 0 mesmo sem mudanças; sai != 0 só em ERRO (ref inexistente).
  # Guardar o exit (como no sonar-gate) para ref ausente virar "não executado",
  # não um "conforme" silencioso sobre 0 arquivos (§15).
  RAW=$(git diff --name-only "$FABER_REMOTE/$FABER_TRUNK"...HEAD -- src 2>/dev/null) \
    || nao_executado "git diff falhou — $FABER_REMOTE/$FABER_TRUNK existe/foi buscado? (§15)"
  ARQS=$(printf '%s\n' "$RAW" | grep -E '\.(tsx|ts|css)$')
fi

# 2. padrões de hardcode proibido (02-DESIGN-SYSTEM §2/§8)
#   a) hex entre colchetes e utilitárias absolutas (white/black)
#   b) literal de cor em valor arbitrário do Tailwind — hsl()/rgb() com número.
#      `hsl(var(--token))` NÃO casa: o `[^)]*` não cruza o ')' de var(, então
#      uso legítimo de token em valor arbitrário continua liberado.
#   (b) existe porque `text-[hsl(0_0%_100%)]` é o mesmo branco que `text-white`,
#   só numa sintaxe que o padrão antigo não reconhecia: o gate dizia "conforme"
#   por forma, não por substância (TASK-101, achado B-9).
PADRAO='\[#[0-9a-fA-F]{3,8}\]|(text|bg|border|fill|stroke|ring|from|via|to)-(white|black)([^a-zA-Z0-9-]|$)|\[(hsla?|rgba?)\([^)]*[0-9]{1,3}[,%_ ]'

# Exceção declarada: o marcador `ds-exception:` abre uma FAIXA de exceção que
# vale da linha do marcador até o fim do bloco (primeira linha que fecha com
# `}` ou linha em branco). Faixa, e não linha isolada, porque o padrão exigido
# pela §8.2 é justamente concentrar os literais num bloco único.
# Exceção é LISTADA, nunca escondida: cor de marca de terceiro é legítima
# (02-DESIGN-SYSTEM §8.2), mas tem de ficar visível para o review.
MARCADOR='ds-exception:'

VIOL=0
EXC=0
N_ARQ=0
ACHADOS=""
EXCECOES=""
for f in $ARQS; do
  case "$f" in
    src/index.css|tailwind.config.ts) continue ;;
  esac
  [ -f "$f" ] || continue
  N_ARQ=$((N_ARQ + 1))
  M=$(grep -nE "$PADRAO" "$f" 2>/dev/null) || continue
  [ -n "$M" ] || continue
  # linhas cobertas por uma faixa de exceção declarada
  ISENTAS=$(awk -v m="$MARCADOR" '
    index($0, m) { faixa = 1; print NR; next }
    faixa {
      print NR
      if ($0 ~ /^[[:space:]]*\}/ || $0 ~ /^[[:space:]]*$/) faixa = 0
    }
  ' "$f")
  while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    ln=${hit%%:*}
    if printf '%s\n' "$ISENTAS" | grep -qx "$ln"; then
      EXC=$((EXC + 1))
      EXCECOES="$EXCECOES$f:$hit
"
    else
      VIOL=$((VIOL + 1))
      ACHADOS="$ACHADOS$f:$hit
"
    fi
  done <<EOF
$M
EOF
done

echo "FILES_ANALYSED=$N_ARQ"
echo "HARDCODE_VIOLATIONS=$VIOL"
echo "DECLARED_EXCEPTIONS=$EXC"
if [ "$EXC" -gt 0 ]; then
  echo "--- exceções declaradas (ds-exception) — legítimas, mas visíveis ---"
  printf '%s' "$EXCECOES" | sed '/^$/d'
fi
if [ "$VIOL" -eq 0 ]; then
  if [ "$EXC" -gt 0 ]; then
    echo "VERDICT=compliant-with-exceptions"
  else
    echo "VERDICT=compliant"
  fi
  echo "NOTE=checklist manual (44px, dark+light, mobile, reuso) na Skill design-system-check"
  exit 0
fi
echo "VERDICT=non-compliant"
echo "--- linhas com hardcode (arquivo:linha:trecho) ---"
printf '%s' "$ACHADOS" | sed '/^$/d'
exit 2