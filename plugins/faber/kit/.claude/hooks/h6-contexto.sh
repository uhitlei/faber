#!/bin/bash
# H6 — SessionStart: injeta contexto mínimo — demandas ativas (state.yaml),
# modo de interação e lembrete das regras invioláveis (§13-H6). Sem demanda
# ativa e com a fábrica já inicializada: silêncio total (economia de contexto,
# §20). Fábrica recém-instalada (bootstrap pendente): aponta para /faber-init.
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" "$(cd "$(dirname "$0")" && pwd)" <<'PYEOF'
import glob, json, os, subprocess, sys

sys.path.insert(0, sys.argv[2])
try:
    import faber_config as fc
except Exception:
    fc = None
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    data = {}
cwd = data.get("cwd") or os.getcwd()
cfg = fc.carregar(cwd) if fc else {}
root = cfg.get("_root") or cwd
owner = cfg.get("FABER_OWNER_NAME", "Owner")
interacao = cfg.get("FABER_INTERACTION", "gates")
trunk = cfg.get("FABER_TRUNK", "develop"); main = cfg.get("FABER_MAIN", "main")

# bootstrap pendente? (install.sh grava faber/bootstrap/CONTEXT.md; /faber-init o conclui)
ctx = os.path.join(root, "faber", "bootstrap", "CONTEXT.md")
if os.path.isfile(ctx):
    try:
        pendente = "status: pendente" in open(ctx, encoding="utf-8").read()
    except Exception:
        pendente = False
    if pendente:
        print("🏭 Fábrica instalada, bootstrap PENDENTE — rode /faber-init para gerar "
              "specs/ARQUITETURA a partir do contexto detectado (faber/bootstrap/CONTEXT.md).")
        print(f"Modo de interação: {interacao}. Aprovador humano: {owner}.")
        sys.exit(0)

ativas = []
try:
    import yaml
    for p in sorted(glob.glob(os.path.join(root, "faber", "tasks", "TASK-*", "state.yaml"))):
        try:
            d = yaml.safe_load(open(p))
        except Exception:
            continue
        if d.get("estado") not in ("done", "cancelled"):
            ativas.append(f"{d.get('demanda')} [{d.get('estado')}] {str(d.get('titulo') or '')[:40]}")
except Exception:
    sys.exit(0)
if not ativas:
    sys.exit(0)

try:
    r = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"],
                       cwd=cwd, capture_output=True, text=True, timeout=5)
    branch = r.stdout.strip() or "?"
except Exception:
    branch = "?"

print("🏭 Fábrica — demandas ativas: " + " · ".join(ativas))
print(f"Branch atual: {branch}. Retome com /faber-resume TASK-XXX (contexto vem do disco). "
      f"Modo de interação: {interacao}.")
print(f"Lembretes: nunca {trunk}/{main}/produção; evidência executada antes de concluir; "
      f"gates G1/G6/G8 só com {owner} (/faber-approve); transições só via transition.sh.")
sys.exit(0)
PYEOF
