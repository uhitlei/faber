#!/bin/bash
# =============================================================================
# gate-check.sh — validador determinístico de transições de estado (zero LLM)
# ARQUITETURA §6.2 (nenhuma transição sem validar os artefatos do destino),
# §15 (rejeita autoaprovação; anti-loop; regressão só com motivo),
# §17 (handoff sem evidência = inválido), §18 (critérios objetivos por gate).
#
# Regras implementadas:
#   · fechamento de 'done' exige G1–G8; G9 é aprovado DENTRO de done;
#   · evidência iniciando com http(s):// é URL (CI/Sonar) — não é checada como
#     arquivo local;
#   · "último handoff" ordenado pelo prefixo NUMÉRICO (10 > 2);
#   · aprovador validado POR GATE (§18): G1/G6/G8 = _schema.owner ·
#     G3 = gate-check · G2/G4/G5/G7/G9 = cto;
#   · placeholder '{{' restante em spec.md bloqueia a entrada em ready-for-dev;
#   · `impacto_ui` (true|false) obrigatório para ENTRAR em ready-for-dev — só na
#     PRIMEIRA entrada;
#   · `impacto_ui: true` + FABER_E2E=on exige, em validation → minha-avaliacao,
#     evidência de E2E REALMENTE executado (5 condições no MESMO log do
#     evidence.sh — ver qualifica_e2e).
#
# Uso: gate-check.sh <TASK-XXX | path-da-pasta> <estado-destino> [--reason "..."]
# Saída: lista TODAS as pendências (não só a primeira).
# Exit:  0 = transição liberada · 1 = bloqueada ou uso incorreto.
# =============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/config.sh
. "$SCRIPT_DIR/lib/config.sh"
TEMPLATE="$SCRIPT_DIR/../templates/state.template.yaml"
TASKS_DIR="$SCRIPT_DIR/../tasks"

uso() { echo "uso: gate-check.sh <TASK-XXX | path> <estado-destino> [--reason \"...\"]"; exit 1; }

[ $# -ge 2 ] || uso
ALVO="$1"; DESTINO="$2"; shift 2
REASON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --reason)
      REASON="${2:-}"
      shift
      [ $# -gt 0 ] && shift   # --reason sem valor não trava o parser
      ;;
    *) uso ;;
  esac
done

if [ -d "$ALVO" ]; then DEMANDA_DIR="$ALVO"
elif [ -d "$TASKS_DIR/$ALVO" ]; then DEMANDA_DIR="$TASKS_DIR/$ALVO"
else echo "BLOQUEIO: pasta da demanda não encontrada ($ALVO)"; exit 1; fi

STATE="$DEMANDA_DIR/state.yaml"
[ -f "$STATE" ] || { echo "BLOQUEIO: $STATE não existe"; exit 1; }

if ! python3 -c "import yaml" >/dev/null 2>&1 && ! command -v ruby >/dev/null 2>&1; then
  echo "BLOQUEIO: nem python3+PyYAML nem ruby disponíveis para ler YAML (pip3 install pyyaml)"
  exit 1
fi

yaml_to_json() {
  if python3 -c "import yaml" >/dev/null 2>&1; then
    python3 -c "import json,sys,yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))" "$1"
  else
    ruby -ryaml -rjson -e 'puts YAML.load_file(ARGV[0]).to_json' "$1"
  fi
}

TMP_INST=$(mktemp); TMP_SCHEMA=$(mktemp)
trap 'rm -f "$TMP_INST" "$TMP_SCHEMA"' EXIT
yaml_to_json "$STATE" > "$TMP_INST" 2>/dev/null \
  || { echo "BLOQUEIO: state.yaml inválido (não parseia como YAML)"; exit 1; }
yaml_to_json "$TEMPLATE" > "$TMP_SCHEMA" 2>/dev/null \
  || { echo "BLOQUEIO: template do schema não parseia ($TEMPLATE)"; exit 1; }

# Verificação de push (só quando destino = code-review): branch no remoto?
PUSH="nao-verificado"
if [ "$DESTINO" = "code-review" ]; then
  BRANCH=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('branch') or '')" "$TMP_INST")
  if [ -n "$BRANCH" ]; then
    if git -C "$SCRIPT_DIR" ls-remote --exit-code --heads "$FABER_REMOTE" "$BRANCH" >/dev/null 2>&1; then
      PUSH="sim"
    else
      PUSH="nao"   # inclui falha de rede: explícito, jamais inferido (§4 do CLAUDE.md)
    fi
  fi
fi

export FABER_E2E FABER_E2E_CMD_REGEX FABER_E2E_SUMMARY_REGEX FABER_E2E_FAIL_REGEX FABER_CMD_E2E FABER_OWNER
python3 - "$TMP_INST" "$TMP_SCHEMA" "$DEMANDA_DIR" "$DESTINO" "$REASON" "$PUSH" "$SCRIPT_DIR" <<'PYEOF'
import glob, json, os, re, sys

inst = json.load(open(sys.argv[1]))
schema = json.load(open(sys.argv[2]))["_schema"]
ddir, destino, motivo, push = sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
OWNER = schema.get("owner") or os.environ.get("FABER_OWNER") or "owner"

bloqueios = []
def b(msg): bloqueios.append(msg)

estados = schema["states"]
atual = inst.get("state")

# §18, tabela de gates: quem pode aprovar cada gate.
APROVADOR_POR_GATE = {
    "G1": {OWNER}, "G6": {OWNER}, "G8": {OWNER},
    "G3": {"gate-check"},
    "G2": {"cto"}, "G4": {"cto"}, "G5": {"cto"}, "G7": {"cto"}, "G9": {"cto"},
}

# ── validações genéricas da instância ──────────────────────────────────────
if destino not in estados:
    print(f"BLOQUEIO: estado-destino '{destino}' não existe no _schema (§6.2)")
    sys.exit(1)
if atual not in estados:
    b(f"estado atual '{atual}' inválido no state.yaml")
if "_schema" in inst:
    b("instância contém bloco _schema (vazamento do template — cópia deve ser scriptada)")
if inst.get("type") not in schema["types"]:
    b(f"tipo '{inst.get('type')}' fora do enum (§14)")

demanda, issue = inst.get("task") or "", inst.get("issue")
if not re.match(r"^TASK-\d+$", demanda):
    b(f"demanda '{demanda}' fora do padrão TASK-<issue#> (D5)")
elif issue != int(demanda.split("-")[1]):
    b(f"demanda '{demanda}' incoerente com issue {issue} (D5: ID = número da issue)")
if inst.get("branch") != f"feature/{demanda}":
    b(f"branch '{inst.get('branch')}' incoerente (esperado feature/{demanda})")

impacto_ui = inst.get("ui_impact")
if impacto_ui is not None and not isinstance(impacto_ui, bool):
    b(f"impacto_ui '{impacto_ui}' inválido — use true ou false")

gates = inst.get("gates") or {}
if list(gates.keys()) != schema["gates"]:
    b("chaves de gates diferem de G1..G9")
for g, dados in gates.items():
    st = (dados or {}).get("status")
    if st not in schema["gate_status"]:
        b(f"{g}: status '{st}' fora do enum")
    if st == "approved":
        apr = dados.get("approver")
        permitidos = APROVADOR_POR_GATE.get(g, set(schema["approvers"]))
        if g in schema["human_gates"] and apr != OWNER:
            b(f"{g}: gate humano aprovado por '{apr}' — AUTOAPROVAÇÃO rejeitada (§15; só {OWNER})")
        elif apr not in permitidos:
            b(f"{g}: aprovador '{apr}' não permitido para este gate (§18: {sorted(permitidos)})")
        if not dados.get("at"):
            b(f"{g}: approved sem timestamp 'at'")
        if g in ("G3", "G5") and not dados.get("evidence"):
            b(f"{g}: approved sem 'evidence' (§18 exige critério objetivo verificável)")

def gate_aprovado(g): return (gates.get(g) or {}).get("status") == "approved"

# ── anti-loop (§15): 3+ invocações do mesmo (agente, input) ────────────────
contagem = {}
for inv in inst.get("invocations") or []:
    chave = (inv.get("agent"), inv.get("input"))
    contagem[chave] = contagem.get(chave, 0) + 1
for (agente, entrada), n in contagem.items():
    if n >= 3:
        b(f"anti-loop violado: {n} invocações de '{agente}' com o mesmo input '{entrada}' (máx. 2; §15)")

# ── handoff mais recente (§17): evidências obrigatórias e existentes ───────
def chave_handoff(p):
    m = re.match(r"(\d+)", os.path.basename(p))
    return (int(m.group(1)) if m else 10**9, os.path.basename(p))
handoffs = sorted(glob.glob(os.path.join(ddir, "handoffs", "*.md")), key=chave_handoff)
if handoffs:
    ultimo = handoffs[-1]
    texto = open(ultimo).read()
    itens = []
    m_inline = re.search(r"^evidence:\s*\[(.*?)\]", texto, re.M)
    m_bloco = re.search(r"^evidence:\s*\n((?:\s*-\s*.+\n?)+)", texto, re.M)
    if m_inline:
        itens = [i.strip().strip("'\"") for i in m_inline.group(1).split(",") if i.strip()]
    elif m_bloco:
        itens = [mm.group(1).strip().strip("'\"")
                 for mm in re.finditer(r"^\s*-\s*(.+)$", m_bloco.group(1), re.M)]
    if not itens:
        b(f"handoff '{os.path.basename(ultimo)}' sem evidências referenciadas (handoff inválido, §17)")
    for ev in itens:
        if re.match(r"^https?://", ev):
            continue  # URL (CI, Sonar) — não é arquivo local
        p = os.path.join(ddir, ev)
        if not (os.path.isfile(p) and os.path.getsize(p) > 0):
            b(f"handoff '{os.path.basename(ultimo)}': evidência '{ev}' inexistente ou vazia (§17)")

# ── regras de origem ───────────────────────────────────────────────────────
if atual == "done":
    b("sair de 'done' é proibido — reabertura gera NOVA demanda vinculada (§6.2)")
if atual == "blocked":
    origem = (inst.get("blocking") or {}).get("previous_state")
    if destino != origem:
        b(f"saída de 'blocked' deve retornar ao estado de origem '{origem}', não '{destino}' (§6.2)")

# ── regressão exige motivo (§6.2/§15) ──────────────────────────────────────
LINEARES = estados[:estados.index("done") + 1]
if atual in LINEARES and destino in LINEARES:
    if LINEARES.index(destino) < LINEARES.index(atual) and not motivo:
        b(f"regressão {atual} -> {destino} sem --reason (§6.2: só com motivo registrado)")

# ── artefatos por estado-destino (§6.2/§18) ────────────────────────────────
def arquivo_ok(nome):
    p = os.path.join(ddir, nome)
    return os.path.isfile(p) and os.path.getsize(p) > 0

def exige_arquivo(nome, contexto):
    if not arquivo_ok(nome):
        b(f"{contexto}: '{nome}' ausente ou vazio na pasta da demanda")

def exige_gate(g, contexto):
    if not gate_aprovado(g):
        b(f"{contexto}: {g} ({(gates.get(g) or {}).get('name')}) não está 'approved'")

# ── evidência de E2E REALMENTE executado ───────────────────────────────────
# Nome de arquivo não é prova; "citou o runner" também não. A prova exige as
# CINCO condições no MESMO arquivo gravado pelo evidence.sh:
#   (i)   '# comando:' casa FABER_E2E_CMD_REGEX (o subcomando que EXECUTA) e
#         NÃO contém --list/--dry-run;
#   (ii)  '# exit code:' = 0;
#   (iii) o CORPO tem o sumário de execução do runner (FABER_E2E_SUMMARY_REGEX);
#   (iv)  '# comando:' NÃO contém '|' (o pipe rouba o exit code);
#   (v)   o CORPO não tem sumário de falha (FABER_E2E_FAIL_REGEX).
def _rx(chave, default):
    try:
        return re.compile(os.environ.get(chave) or default, re.I)
    except re.error:
        return re.compile(default, re.I)
E2E_ON = (os.environ.get("FABER_E2E") or "off").lower() in ("on", "true", "1", "sim", "yes")
CMD_E2E = os.environ.get("FABER_CMD_E2E") or "<comando E2E>"
FIM_CABECALHO = re.compile(r"^#\s*[─-]{10,}\s*$")
RE_CMD_EXEC = _rx("FABER_E2E_CMD_REGEX", r"playwright\S*\s+test\b")
RE_CMD_SEM_EXECUCAO = re.compile(r"--list\b|--dry-run\b", re.I)
RE_CMD_PIPE = re.compile(r"\|")
RE_SUMARIO = _rx("FABER_E2E_SUMMARY_REGEX", r"\d+\s+passed\b")
RE_FALHA = _rx("FABER_E2E_FAIL_REGEX", r"\d+\s+failed\b")

def qualifica_e2e(comando, exit_code, tem_sumario, tem_falha):
    return bool(RE_CMD_EXEC.search(comando) and not RE_CMD_SEM_EXECUCAO.search(comando)
                and not RE_CMD_PIPE.search(comando) and exit_code == "0"
                and tem_sumario and not tem_falha)

def analisa_evidencia(path, max_cabecalho=400, max_corpo=60000):
    """(comando, exit_code, tem_sumario, tem_falha) de um log do evidence.sh."""
    comando = exit_code = None
    tem_sumario = tem_falha = False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            no_cabecalho = True
            for i, linha in enumerate(fh):
                if i == 0:
                    if "evidence.sh" not in linha:
                        return None, None, False, False
                    continue
                if no_cabecalho:
                    if i > max_cabecalho or FIM_CABECALHO.match(linha):
                        no_cabecalho = False
                        continue
                    m = re.match(r"^#\s*comando:\s*(.*)$", linha)
                    if m and comando is None:
                        comando = m.group(1)
                    m = re.match(r"^#\s*exit code:\s*(\S+)", linha)
                    if m and exit_code is None:
                        exit_code = m.group(1)
                else:
                    if RE_SUMARIO.search(linha):
                        tem_sumario = True
                    if RE_FALHA.search(linha):
                        tem_falha = True
                    if (tem_sumario and tem_falha) or i > max_corpo:
                        break
    except OSError:
        return None, None, False, False
    return comando, exit_code, tem_sumario, tem_falha

def evidence_e2e(ddir):
    achados = []
    for p in sorted(glob.glob(os.path.join(ddir, "evidence", "*"))):
        if not (os.path.isfile(p) and os.path.getsize(p) > 0):
            continue
        comando, exit_code, tem_sumario, tem_falha = analisa_evidencia(p)
        if comando and qualifica_e2e(comando, exit_code, tem_sumario, tem_falha):
            achados.append(os.path.basename(p))
    return achados

if destino == "refinement":
    exige_arquivo("spec.md", "refinement")
elif destino == "ready-for-dev":
    exige_arquivo("spec.md", "ready-for-dev")
    exige_arquivo("refinamento.md", "ready-for-dev")
    spec_path = os.path.join(ddir, "spec.md")
    if os.path.isfile(spec_path):
        n_ph = open(spec_path).read().count("{{")
        if n_ph:
            b(f"ready-for-dev: spec.md contém {n_ph} placeholder(s) '{{{{' não preenchido(s) (Skill spec-task regra 3; DoR/G1)")
    # impacto_ui obrigatório só na PRIMEIRA entrada em ready-for-dev
    ja_passou_rfd = any((h or {}).get("to_state") == "ready-for-dev"
                        for h in (inst.get("history") or []))
    estado_posterior = (atual in LINEARES
                        and LINEARES.index(atual) > LINEARES.index("ready-for-dev"))
    if not (ja_passou_rfd or estado_posterior) and not isinstance(impacto_ui, bool):
        b("ready-for-dev: campo 'ui_impact' (true|false) ausente ou não preenchido "
          "no state.yaml — declare no refinamento se a demanda muda a interface do "
          "produto. É ele que liga a exigência de E2E no G5.")
elif destino == "in-development":
    exige_gate("G1", "in-development")
elif destino == "developed":
    for padrao, rotulo in (("*lint*", "lint"), ("*build*", "build"), ("*test*", "test")):
        achados = [f for f in glob.glob(os.path.join(ddir, "evidence", padrao))
                   if os.path.isfile(f) and os.path.getsize(f) > 0]
        if not achados:
            b(f"developed: evidência de {rotulo} ausente em evidence/ ({padrao} não-vazio; §18-G3)")
elif destino == "code-review":
    exige_gate("G3", "code-review")
    if push != "sim":
        b(f"code-review: branch '{inst.get('branch')}' não encontrada no remoto (push não verificado; §6.2)")
elif destino == "validation":
    exige_arquivo("review.md", "validation")
    exige_gate("G4", "validation")
elif destino == "my-review":
    exige_gate("G5", "my-review")
    if impacto_ui is True and E2E_ON and not evidence_e2e(ddir):
        b("minha-avaliacao: impacto_ui=true exige evidência de E2E EXECUTADO e nenhum "
          "log de evidence/ qualifica. Como resolver: faber/scripts/evidence.sh "
          f"{demanda or 'TASK-XXX'} e2e -- {CMD_E2E} — chame o runner DIRETO, SEM PIPE, "
          "com a suíte VERDE. Um log do evidence.sh só conta com as 5 condições juntas: "
          "(i) '# comando:' casa FABER_E2E_CMD_REGEX, sem --list/--dry-run; (ii) "
          "'# exit code:     0'; (iii) sumário de execução no corpo; (iv) sem '|' no "
          "comando; (v) sem sumário de falha no corpo. Nome de arquivo com 'e2e' ou "
          "wrapper 'bash script.sh' NÃO são prova de execução.")
elif destino == "ready-for-pr":
    exige_gate("G6", "ready-for-pr")
elif destino == "pr-open":
    exige_gate("G7", "pr-open")
    if not inst.get("pr"):
        b("pr-open: campo 'pr' vazio no state.yaml (número/URL da PR)")
elif destino == "done":
    exige_gate("G8", "done")
    for g, dados in gates.items():
        if g == "G9":
            continue  # G9 é aprovado DENTRO de done (consolidação pós-merge)
        if (dados or {}).get("status") not in ("approved", "not-applicable"):
            b(f"done: {g} está '{(dados or {}).get('status')}' — G1–G8 devem estar aprovado/nao-aplicavel")
elif destino == "blocked":
    blq = inst.get("blocking") or {}
    if not blq.get("reason"):
        b("blocked: bloqueio.motivo obrigatório (§6.2)")
    if blq.get("previous_state") not in estados:
        b(f"blocked: bloqueio.estado_origem '{blq.get('previous_state')}' inválido")
elif destino == "cancelled":
    if not motivo:
        b(f"cancelled: exige --reason (decisão explícita de {OWNER} registrada; §6.2)")

# ── resultado ──────────────────────────────────────────────────────────────
# Discovery é opt-in nas demandas históricas, mas pacote presente sempre ativa.
if destino in ("ready-for-dev", "in-development", "developed", "code-review",
               "validation", "my-review", "ready-for-pr", "pr-open", "done"):
    cfg = inst.get("discovery")
    pacote = os.path.exists(os.path.join(ddir, "requirements"))
    if cfg is not None and (not isinstance(cfg, dict) or type(cfg.get("required")) is not bool):
        b("discovery.required deve ser booleano")
    if pacote or (isinstance(cfg, dict) and cfg.get("required") is True) or (gates.get("G1") or {}).get("requirements_hash"):
        try:
            sys.path.insert(0, os.path.join(sys.argv[7], "lib"))
            from requirements import delivery_hash
            fingerprint = delivery_hash(ddir)
            if destino != "ready-for-dev" and (gates.get("G1") or {}).get("requirements_hash") != fingerprint:
                b("G1 não corresponde à revisão atual dos requisitos; renovar aprovação humana")
        except Exception as exc:
            b(f"discovery: {exc}")

print(f"gate-check: {demanda or '?'}: {atual} -> {destino}")
if bloqueios:
    for msg in bloqueios:
        print(f"BLOQUEIO: {msg}")
    print(f"RESULTADO: BLOQUEADA ({len(bloqueios)} pendência(s))")
    sys.exit(1)
print("RESULTADO: TRANSIÇÃO LIBERADA")
PYEOF
