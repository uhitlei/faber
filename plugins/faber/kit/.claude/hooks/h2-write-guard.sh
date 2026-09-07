#!/bin/bash
# H2 — guarda-vidas de escrita (PreToolUse Write/Edit). ARQUITETURA §13-H2.
# Deny: arquivos de secrets (FABER_SECRET_FILES — nunca editados pelo
#       agente) · paths protegidos/gerados (FABER_PROTECTED_PATHS) ·
#       migrations com timestamp já existente no histórico (imutabilidade;
#       FABER_MIGRATIONS_DIR).
# Workflows (.github/workflows/*): ALLOW se a demanda ativa (branch
#       feature/TASK-XXX) tem workflow_unlock autorizado pelo Owner no
#       state.yaml; senão ASK (confirmação manual por execução). Autorização
#       só via faber/scripts/workflow-unlock.sh.
# Ask:  .claude/settings.json, .claude/hooks/* e faber/config/faber.env —
#       os guarda-vidas da própria fábrica; edição só com confirmação do Owner.
# Nota: a checagem de migrations depende de <remote>/<trunk> e <remote>/<main>
#       atualizados — gate-check.sh e /faber-pr executam `git fetch` antes. Sem
#       remoto, usa fallback conservador pelo index local.
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" "$(cd "$(dirname "$0")" && pwd)" <<'PYEOF'
import json, os, re, subprocess, sys

sys.path.insert(0, sys.argv[2])
try:
    import faber_config as fc
except Exception:
    fc = None

try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
except Exception:
    sys.exit(0)

if data.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
    sys.exit(0)

ti = data.get("tool_input") or {}
path = ti.get("file_path") or ti.get("notebook_path") or ""
if not path:
    sys.exit(0)

cwd = data.get("cwd") or os.getcwd()
cfg = fc.carregar(cwd) if fc else {}
OWNER = cfg.get("FABER_OWNER", "owner")
OWNER_NOME = cfg.get("FABER_OWNER_NAME", "Owner")
TRUNK = cfg.get("FABER_TRUNK", "develop")
MAIN = cfg.get("FABER_MAIN", "main")
REMOTE = cfg.get("FABER_REMOTE", "origin")
if not os.path.isabs(path):
    path = os.path.join(cwd, path)
path = os.path.realpath(path)   # realpath: /var -> /private/var no macOS


def decide(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def deny(reason): decide("deny", reason)
def ask(reason): decide("ask", reason)
def allow(reason): decide("allow", reason)


def git_root():
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           cwd=cwd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def workflow_unlock_autorizado(root):
    if not root:
        return False
    try:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                           cwd=cwd, capture_output=True, text=True, timeout=5)
        branch = r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return False
    mb = re.match(r"feature/(TASK-\d+)$", branch)
    if not mb:
        return False
    sp = os.path.join(root, "faber", "tasks", mb.group(1), "state.yaml")
    if not os.path.isfile(sp):
        return False
    try:
        import yaml
        with open(sp) as fh:
            st = yaml.safe_load(fh) or {}
    except Exception:
        return False
    wu = st.get("workflow_unlock") or {}
    return wu.get("autorizado") is True and wu.get("por") == OWNER


root = git_root()
rel = os.path.relpath(path, root) if root else path
base = os.path.basename(path)

# 1. Arquivos de secrets — sempre por NOME, nunca editados pelo agente
secrets = fc.lista(cfg, "FABER_SECRET_FILES") if fc else [".env", ".env.local"]
if base in secrets:
    deny(f"H2: editar '{base}' é proibido — secrets entram por variável de ambiente, "
         "referidos por nome (§13-H2/§19).")

# 2. Paths protegidos/gerados do projeto (FABER_PROTECTED_PATHS)
for p in (fc.lista(cfg, "FABER_PROTECTED_PATHS") if fc else []):
    p = p.strip()
    if not p:
        continue
    if p.endswith("/"):
        if rel.startswith(p) or ("/" + p) in path:
            deny(f"H2: '{rel}' está sob o path protegido '{p}' — nunca editar (§13-H2).")
    elif rel == p or path.endswith("/" + p):
        deny(f"H2: '{rel}' é protegido — nunca editar (gerado/intocável; §13-H2).")

# 3. Workflows do CI — auto-unlock via state.yaml, senão ask
if rel.startswith(".github/workflows/") or "/.github/workflows/" in path:
    if workflow_unlock_autorizado(root):
        allow(f"H2: edição de .github/workflows/ liberada — workflow_unlock autorizado por "
              f"'{OWNER}' no state.yaml da demanda ativa (auto-unlock).")
    ask(f"H2: editar .github/workflows/ exige confirmação de {OWNER_NOME}, por execução "
        "(§2/§19). Autorize de vez na demanda com "
        f"'faber/scripts/workflow-unlock.sh TASK-XXX --por {OWNER}' (auto-unlock).")

# 4. Guarda-vidas da própria fábrica
if rel == ".claude/settings.json" or rel.startswith(".claude/hooks/") \
   or "/.claude/hooks/" in path or path.endswith("/.claude/settings.json") \
   or rel == "faber/config/faber.env":
    ask("H2: '.claude/settings.json', '.claude/hooks/' e 'faber/config/faber.env' são "
        f"os guarda-vidas da fábrica — edição exige confirmação explícita de {OWNER_NOME} (§19).")

# 5. Imutabilidade de migrations (FABER_MIGRATIONS_DIR)
mig = (cfg.get("FABER_MIGRATIONS_DIR") or "").strip("/")
m = re.match(re.escape(mig) + r"/(\d{8,14})_.+\.sql$", rel) if mig else None
if m and root:
    ts = m.group(1)
    historico = []
    for ref in (f"{REMOTE}/{TRUNK}", f"{REMOTE}/{MAIN}"):
        r = subprocess.run(["git", "ls-tree", "-r", "--name-only", ref, "--", mig],
                           cwd=root, capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            historico += r.stdout.splitlines()
    if not historico:
        r = subprocess.run(["git", "ls-files", "--", mig],
                           cwd=root, capture_output=True, text=True, timeout=10)
        historico = r.stdout.splitlines() if r.returncode == 0 else []
    historico = set(historico)
    if rel in historico:
        deny(f"H2: '{base}' já está no histórico — migrations aplicadas são imutáveis; "
             "crie uma NOVA migration corretiva (§13-H2).")
    prefixos = set()
    for h in historico:
        pm = re.match(re.escape(mig) + r"/(\d+)_", h)
        if pm:
            prefixos.add(pm.group(1))
    if ts in prefixos:
        deny(f"H2: timestamp {ts} já existe no histórico de migrations — use um "
             "timestamp novo (§13-H2).")

sys.exit(0)
PYEOF
