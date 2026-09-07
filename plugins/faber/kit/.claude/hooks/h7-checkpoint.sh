#!/bin/bash
# H7 — PreCompact: checkpoint antes da compactação de contexto (§13-H7).
# A sessão pode perder detalhes na compactação — o que importa deve estar em
# disco (state.yaml, decisions.md, handoffs) e commitado. Este hook alerta
# sobre artefatos de demanda não commitados; a persistência é do CTO.
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" <<'PYEOF'
import json, os, subprocess, sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    data = {}
cwd = data.get("cwd") or os.getcwd()
try:
    r = subprocess.run(["git", "status", "--porcelain", "--", "faber/tasks"],
                       cwd=cwd, capture_output=True, text=True, timeout=10)
    sujos = [l for l in r.stdout.splitlines() if l.strip()]
except Exception:
    sys.exit(0)
if not sujos:
    sys.exit(0)

lista = ", ".join(l.split()[-1] for l in sujos[:8]) + (" …" if len(sujos) > 8 else "")
print(json.dumps({"systemMessage":
    f"H7 (pré-compactação): {len(sujos)} artefato(s) de demanda NÃO commitados: {lista}. "
    "Persista agora (state.yaml/decisions.md/handoffs + commit) — o que não está "
    "em disco pode se perder na compactação (§13-H7)."}))
sys.exit(0)
PYEOF
