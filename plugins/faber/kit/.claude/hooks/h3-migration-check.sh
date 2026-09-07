#!/bin/bash
# H3 — PostToolUse (Write/Edit em FABER_MIGRATIONS_DIR/*.sql): valida a
# migration recém-escrita contra o template (§13-H3): placeholders {{...}}
# restantes e os termos obrigatórios de FABER_MIGRATION_CHECKS (ex.: GRANT,
# RLS, POLICY, search_path em Postgres). "Avisa e marca pendência": o Write já
# ocorreu; ausências viram decision=block (o agente vê e completa) + pendência
# anotada no log.md da demanda da branch. Módulo desligado (dir vazio) = silêncio.
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" "$(cd "$(dirname "$0")" && pwd)" <<'PYEOF'
import json, os, re, subprocess, sys
from datetime import datetime

sys.path.insert(0, sys.argv[2])
try:
    import faber_config as fc
except Exception:
    fc = None
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
    sys.exit(0)
path = (data.get("tool_input") or {}).get("file_path") or ""
if not path:
    sys.exit(0)
cwd = data.get("cwd") or os.getcwd()
cfg = fc.carregar(cwd) if fc else {}
mig = (cfg.get("FABER_MIGRATIONS_DIR") or "").strip("/")
if not mig:
    sys.exit(0)
if not os.path.isabs(path):
    path = os.path.join(cwd, path)
path = os.path.realpath(path)
if not re.search(re.escape(mig) + r"/[^/]+\.sql$", path) or not os.path.isfile(path):
    sys.exit(0)

corpo = open(path, encoding="utf-8", errors="replace").read().lower()
ausencias = []
for termo in (fc.lista(cfg, "FABER_MIGRATION_CHECKS") if fc else []):
    if termo.lower() not in corpo:
        ausencias.append(termo.strip().upper())
if "{{" in corpo:
    ausencias.append("placeholders {{...}} do template não preenchidos")
if "security definer" in corpo:
    cab = []
    for linha in corpo.splitlines():
        ls = linha.strip()
        if ls.startswith("--") or not ls:
            cab.append(ls)
        else:
            break
    if "definer" not in "\n".join(cab):
        ausencias.append("justificativa do SECURITY DEFINER na ANÁLISE do cabeçalho")

if not ausencias:
    sys.exit(0)

try:
    r = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"],
                       cwd=cwd, capture_output=True, text=True, timeout=5)
    m = re.match(r"feature/(TASK-\d+)$", r.stdout.strip())
    if m:
        pasta = os.path.join(cwd, "faber", "tasks", m.group(1))
        if os.path.isdir(pasta):
            with open(os.path.join(pasta, "log.md"), "a") as f:
                f.write(f"- {datetime.now().astimezone().isoformat(timespec='seconds')} "
                        f"H3: pendência em {os.path.basename(path)} — ausente: {', '.join(ausencias)}\n")
except Exception:
    pass

print(json.dumps({"decision": "block",
                  "reason": f"H3: migration '{os.path.basename(path)}' sem: {', '.join(ausencias)}. "
                            "Complete conforme faber/templates/migration.template.sql "
                            "(Skill migration-safe) OU, se a ausência for LEGÍTIMA (ex.: "
                            "migration só de índice), registre-a na ANÁLISE do cabeçalho e "
                            "siga — este aviso não desfaz o Write. Pendência anotada no "
                            "log da demanda."}))
sys.exit(0)
PYEOF
