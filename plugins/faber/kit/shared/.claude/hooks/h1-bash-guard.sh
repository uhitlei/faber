#!/bin/bash
# H1 — guarda-vidas de Bash (PreToolUse). ARQUITETURA §13-H1 e §19.
# Regras FIXAS (núcleo da fábrica):
#   deny  push/merge/commit do git envolvendo o trunk ou a branch de produção ·
#         gh pr merge · gh api com escrita em endpoints protegidos (merge de PR,
#         refs do trunk/produção, workflows) · mutations GraphQL de merge.
#   ask   escrita via shell (sed -i, tee, mv, cp, rm, >) em paths protegidos do
#         H2 · gate-set com G1/G6/G8 'approved' e workflow-unlock (a confirmação
#         do diálogo É a decisão do Owner — fecha a forja por Bash direto).
# Regras CONFIGURÁVEIS (faber/config/faber.env):
#   deny  qualquer comando contendo um token de FABER_REFS_DENY (ex.: ref
#         de PROD) · regex de FABER_CMDS_DENY.
#   ask   comando contendo token de FABER_REFS_CONFIRM (ex.: ref de HML) ·
#         regex de FABER_CMDS_CONFIRM (ex.: db push, docker push).
# Modo bypass (sessão em bypassPermissions + FABER_BYPASS=on): ninguém está na
#   tela, então nada aqui pode travar a sessão num diálogo. Os deny seguem
#   iguais; FABER_REFS_CONFIRM/FABER_CMDS_CONFIRM passam livres; escrita via
#   shell em path protegido vira deny. Só o gate-set de G1/G6/G8 e o
#   workflow-unlock continuam ask — decisões humanas, onde a sessão deve parar.
# Protocolo: JSON no stdin; decisão via hookSpecificOutput no stdout; exit 0
# sem output = sem opinião (segue o fluxo normal de permissões).
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

if data.get("tool_name") != "Bash":
    sys.exit(0)

cmd = (data.get("tool_input") or {}).get("command") or ""
cwd = data.get("cwd") or os.getcwd()
cfg = fc.carregar(cwd) if fc else {}
BYPASS = fc.em_bypass(data, cfg) if fc else False
OWNER_NOME = cfg.get("FABER_OWNER_NAME", "Owner")
TRUNK = cfg.get("FABER_TRUNK", "develop")
MAIN = cfg.get("FABER_MAIN", "main")
PROTEGIDAS = set(fc.branches_protegidas(cfg)) if fc else {TRUNK, MAIN, "main", "master"}
PROT_RE = "|".join(re.escape(b) for b in sorted(PROTEGIDAS, key=len, reverse=True))


def decide(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def branch_atual():
    try:
        r = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"],
                           cwd=cwd, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


# 1. Tokens proibidos (ex.: ref de PROD) — deny absoluto (§13-H1/§19)
for tok in (fc.lista(cfg, "FABER_REFS_DENY") if fc else []):
    if tok and tok in cmd:
        decide("deny",
               f"H1: comando contém um token PROIBIDO ('{tok}', FABER_REFS_DENY — "
               "ex.: ambiente de produção). Nenhum agente age ali: mudanças chegam por CI "
               f"ou manualmente por {OWNER_NOME} (§13-H1/§19).")
for rx in (fc.regexes(cfg, "FABER_CMDS_DENY") if fc else []):
    if rx.search(cmd):
        decide("deny", f"H1: comando casa regra PROIBIDA de FABER_CMDS_DENY ({rx.pattern}) (§19).")

# Detecção de refs protegidas como alvo (evita casar feature/main-menu, origin/main)
ref_protegida = re.compile(r"(?<![\w/.-])(" + PROT_RE + r")(?![\w-])")
refs_heads = re.compile(r"refs/heads/(" + PROT_RE + r")(?![\w-])")

# 2. envio (push) do git envolvendo trunk/produção — por ref explícito ou branch atual
if re.search(r"\bgit\b[^\n]*\bpush\b", cmd):
    alvo = ref_protegida.search(cmd) or refs_heads.search(cmd)
    if alvo:
        decide("deny",
               f"H1: push envolvendo '{alvo.group(1)}' é proibido — {TRUNK}/{MAIN} só "
               f"recebem código via PR mergeada por {OWNER_NOME} no GitHub (§13-H1/§19).")
    b = branch_atual()
    if b in PROTEGIDAS:
        decide("deny",
               f"H1: push com a branch atual '{b}' (protegida) é proibido — trabalhe em "
               "feature branch (§13-H1/§19).")

# 3. merge / commit do git com a branch atual protegida (§19)
if re.search(r"\bgit\b[^\n]*\b(merge|commit)\b", cmd):
    b = branch_atual()
    if b in PROTEGIDAS:
        decide("deny",
               f"H1: commit/merge com a branch atual '{b}' (protegida) é proibido — "
               f"{TRUNK}/{MAIN} só mudam via PR (§19).")

# 4. gh pr merge — merge é sempre humano, no GitHub (G8)
if re.search(r"\bgh\b[^\n]*\bpr\b[^\n]*\bmerge\b", cmd):
    decide("deny",
           f"H1: merge de PR é exclusivo de {OWNER_NOME}, manualmente no GitHub "
           "(gate G8) — nunca via gh pr merge (§19).")

# 5. gh api — bloqueia escrita nos endpoints que driblariam G8/H1
if re.search(r"\bgh\s+api\b", cmd):
    escrita = (re.search(r"(?:-X|--method)[=\s]+['\"]?(PUT|POST|PATCH|DELETE)\b", cmd, re.I)
               or re.search(r"(?:^|\s)(--input\b|-f\b|-F\b|--field\b|--raw-field\b)", cmd))
    endpoint_protegido = re.search(
        r"pulls/[^\s'\"]+/merge\b"
        r"|/merges\b"
        r"|git/refs/heads/(" + PROT_RE + r")(?![\w-])"
        r"|actions/workflows",
        cmd)
    if escrita and endpoint_protegido:
        decide("deny",
               "H1: gh api com método de escrita em endpoint protegido (merge de PR, "
               f"refs de {TRUNK}/{MAIN} ou workflows) é proibido — equivale a burlar "
               "G8/H1 (§19).")
    if re.search(r"\bgraphql\b", cmd) and re.search(
            r"mergePullRequest|enablePullRequestAutoMerge|mergeBranch\b", cmd):
        decide("deny",
               "H1: mutation GraphQL de merge (mergePullRequest/mergeBranch/"
               f"enablePullRequestAutoMerge) é proibida — merge é exclusivo de {OWNER_NOME} "
               "no GitHub (G8/§19).")

# 6. Tokens que exigem confirmação (ex.: ref de HML) — ask por execução (§19).
#    Em bypass o Owner abriu mão da confirmação por execução: passa livre.
for tok in (fc.lista(cfg, "FABER_REFS_CONFIRM") if fc and not BYPASS else []):
    if tok and tok in cmd:
        decide("ask",
               f"H1: comando contém '{tok}' (FABER_REFS_CONFIRM — ambiente remoto). "
               f"Exige confirmação explícita de {OWNER_NOME}, por execução (§19).")
for rx in (fc.regexes(cfg, "FABER_CMDS_CONFIRM") if fc and not BYPASS else []):
    if rx.search(cmd):
        decide("ask",
               f"H1: comando casa regra de confirmação ({rx.pattern}, FABER_CMDS_CONFIRM) "
               f"— exige confirmação explícita de {OWNER_NOME} (§19).")

# 7. Bypass do H2 via shell: escrita em paths protegidos com utilitários de
#    shell em vez de Write/Edit. Ask (tolera falso positivo de leitura); em
#    bypass, deny — sem ninguém para confirmar, o guarda-vidas fica de pé.
paths = [".github/workflows/", ".claude/settings.json", ".claude/hooks/", "faber/config/faber.env"]
paths += (fc.lista(cfg, "FABER_PROTECTED_PATHS") if fc else [])
paths += (fc.lista(cfg, "FABER_SECRET_FILES") if fc else [".env", ".env.local"])
mig = (cfg.get("FABER_MIGRATIONS_DIR") or "").strip("/")
if mig:
    paths.append(mig + "/")
PATHS_H2 = re.compile("|".join(re.escape(p) for p in paths if p))
# Redirecionamentos inofensivos (2>/dev/null, >&2, &>/dev/null) não são escrita.
REDIR_INOFENSIVO = re.compile(r"(?:\d|&)?>{1,2}\s*(?:/dev/null\b|&\d)")
ESCRITA_SHELL = re.compile(
    r"\bsed\s+-[a-zA-Z]*i"
    r"|\btee\b|\bmv\b|\bcp\b|\brm\b|\btruncate\b|\bdd\b"
    r"|>{1,2}"
    r"|\bopen\([^)]*['\"][wa]")
if paths and PATHS_H2.search(cmd) and ESCRITA_SHELL.search(REDIR_INOFENSIVO.sub(" ", cmd)):
    if BYPASS:
        decide("deny",
               "H1 (modo bypass): escrita via shell em path protegido pelo H2 (workflows, "
               "hooks/settings/config da fábrica, secrets, migrations, FABER_PROTECTED_PATHS) "
               "é negada — sem ninguém na tela para confirmar. Para ler, use Read/Grep; para "
               "escrever, use Write/Edit (valem as regras do H2). Se a mudança for mesmo "
               f"necessária, registre-a como pendência para {OWNER_NOME} no próximo gate e siga.")
    decide("ask",
           "H1: possível escrita via shell em path protegido pelo H2 (workflows, hooks/"
           "settings/config da fábrica, secrets, migrations, FABER_PROTECTED_PATHS). Se "
           "for apenas leitura, confirme; escrita nesses paths segue as regras do H2 (§13-H2).")

# 8. Gates humanos: registrar G1/G6/G8 como 'approved' via gate-set só pode
#    expressar decisão do Owner — o ask abaixo É essa decisão. Vale também em
#    bypass: é aqui que a sessão deve parar e esperar o humano.
if re.search(r"\bgate-set(\.sh)?\b", cmd) and \
   re.search(r"\bG(1|6|8)\b", cmd) and re.search(r"\bapproved\b", cmd):
    decide("ask",
           "H1: registro de gate HUMANO (G1/G6/G8) como 'approved' — confirmar este "
           f"diálogo é a aprovação de {OWNER_NOME} (§15/§19). "
           "CTO sem ordem explícita do Owner: cancele.")

# 9. workflow_unlock também é decisão do Owner (§19): sem este ask, o agente
#    se autorizaria a editar workflows — e em bypass nada mais o impediria.
if re.search(r"\bworkflow-unlock(\.sh)?\b", cmd) and not re.search(r"--revoke\b", cmd):
    decide("ask",
           "H1: workflow_unlock libera a edição de .github/workflows/ na demanda — "
           f"confirmar este diálogo é a autorização de {OWNER_NOME} (§19). "
           "CTO sem ordem explícita do Owner: cancele.")

sys.exit(0)
PYEOF
