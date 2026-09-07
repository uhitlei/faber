#!/bin/bash
# H4 — PostToolUse (Bash com git commit): valida a mensagem do commit REAL
# (git log -1) — `tipo(escopo): descrição` sempre; referência TASK-XXX
# exigida quando a branch é feature/TASK-N (§13-H4). Fora de branch de
# demanda (ex.: construção da própria fábrica), só o formato é exigido.
# Guarda de recência: se o commit FALHOU (nada staged, hook negou…),
# `git log -1` devolveria o commit ANTERIOR — que pode ser um merge commit
# legítimo fora do padrão — e o hook bloquearia por engano. Só validamos
# commit criado nos últimos 60s. (--amend segue pulado: é a via de correção
# indicada no reason; tradeoff documentado — amend ruim é pego no review.)
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" <<'PYEOF'
import json, os, re, subprocess, sys, time

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
if data.get("tool_name") != "Bash":
    sys.exit(0)
cmd = (data.get("tool_input") or {}).get("command") or ""
if not re.search(r"\bgit\b[^\n]*\bcommit\b", cmd) or "--amend" in cmd:
    sys.exit(0)
cwd = data.get("cwd") or os.getcwd()

def git(*args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
    return r.stdout.strip() if r.returncode == 0 else None

# Recência — o commit validado precisa ser DESTA execução.
ct = git("log", "-1", "--format=%ct")
if not ct or time.time() - int(ct) > 60:
    sys.exit(0)   # commit não aconteceu agora (falhou/negado) — nada a validar

assunto = git("log", "-1", "--format=%s")
corpo = git("log", "-1", "--format=%B") or ""
if not assunto:
    sys.exit(0)

problemas = []
if not re.match(r"^(feat|fix|chore|docs|test|refactor|perf|style|ci|build|revert)"
                r"(\([\w./-]+\))?: .+", assunto):
    problemas.append(f"assunto '{assunto[:60]}' fora do padrão 'tipo(escopo): descrição'")

branch = git("symbolic-ref", "--short", "HEAD") or ""
m = re.match(r"feature/(TASK-\d+)$", branch)
if m and m.group(1) not in corpo:
    problemas.append(f"branch de demanda ({branch}) exige referência {m.group(1)} na mensagem")

if problemas:
    print(json.dumps({"decision": "block",
                      "reason": "H4: " + "; ".join(problemas) +
                                ". Corrija com: git commit --amend (§13-H4)."}))
sys.exit(0)
PYEOF