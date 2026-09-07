#!/bin/bash
# H5 — SubagentStop: confere o handoff mais recente (formato §17) e registra a
# invocação — no log.md E em `invocacoes` do state.yaml (base do anti-loop —
# §13-H5/§15; o gate-check conta por (agente, input) no state.yaml).
# Handoff INVÁLIDO = bloqueia o encerramento UMA vez (stop_hook_active evita
# loop). Handoff AUSENTE = aviso apenas (o hook não sabe se o subagente que
# parou era da fábrica — o CTO julga).
TMP=$(mktemp) || exit 0
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"
python3 - "$TMP" <<'PYEOF'
import glob, json, os, re, sys, time
from datetime import datetime

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
if data.get("stop_hook_active"):
    sys.exit(0)          # já bloqueamos uma vez — não entrar em loop
cwd = data.get("cwd") or os.getcwd()
base = os.path.join(cwd, "faber", "tasks")
if not os.path.isdir(base):
    sys.exit(0)

JANELA = 15 * 60         # handoff "desta invocação" = modificado há < 15 min
agora = time.time()
recentes = [p for p in glob.glob(os.path.join(base, "TASK-*", "handoffs", "*.md"))
            if agora - os.path.getmtime(p) < JANELA]
if not recentes:
    print(json.dumps({"systemMessage":
        "H5: subagente encerrou sem handoff novo em faber/tasks/*/handoffs/ "
        "(últimos 15 min). Se era um subagente da fábrica, o handoff é obrigatório (§17)."}))
    sys.exit(0)

ultimo = max(recentes, key=os.path.getmtime)
pasta_demanda = os.path.dirname(os.path.dirname(ultimo))
texto = open(ultimo).read()
m = re.search(r"```yaml\n(.*?)```", texto, re.S)
bruto = m.group(1) if m else texto
problemas = []
d = {}
try:
    import yaml
    d = yaml.safe_load(bruto) or {}
    for campo in ("demanda", "de", "para", "estado_sugerido", "evidence"):
        if not d.get(campo):
            problemas.append(f"campo '{campo}' ausente/vazio")
    for ev in (d.get("evidence") or []):
        if isinstance(ev, str) and not ev.startswith("http"):
            p = os.path.join(pasta_demanda, ev)
            if not (os.path.isfile(p) and os.path.getsize(p) > 0):
                problemas.append(f"evidência '{ev}' inexistente/vazia")
except Exception as e:
    problemas.append(f"não parseia como YAML ({e.__class__.__name__})")

if problemas:
    print(json.dumps({"decision": "block",
                      "reason": f"H5: handoff '{os.path.relpath(ultimo, cwd)}' inválido: "
                                + "; ".join(problemas) +
                                ". Corrija o handoff antes de encerrar (§17)."}))
    sys.exit(0)

# válido: registra a invocação — state.yaml (contador do anti-loop) + log.md
agora_iso = datetime.now().astimezone().isoformat(timespec="seconds")
registrado = "log"
try:
    import yaml
    state_path = os.path.join(pasta_demanda, "state.yaml")
    if os.path.isfile(state_path):
        st = yaml.safe_load(open(state_path)) or {}
        invs = st.get("invocacoes") or []
        nome_handoff = os.path.basename(ultimo)
        if not any(i.get("handoff") == nome_handoff for i in invs if isinstance(i, dict)):
            entradas = d.get("entradas_consumidas") or []
            invs.append({"agente": d.get("de"), "em": agora_iso,
                         "input": ", ".join(map(str, entradas)) or nome_handoff,
                         "handoff": nome_handoff})
            st["invocacoes"] = invs
            yaml.safe_dump(st, open(state_path, "w"), allow_unicode=True, sort_keys=False)
            registrado = "state.yaml + log"
        else:
            registrado = "já registrado (dedupe) + log"
except Exception:
    pass
try:
    with open(os.path.join(pasta_demanda, "log.md"), "a") as f:
        f.write(f"- {agora_iso} H5: handoff {os.path.basename(ultimo)} validado "
                f"(de={d.get('de')}, estado_sugerido={d.get('estado_sugerido')}; "
                f"invocação: {registrado})\n")
except Exception:
    pass
sys.exit(0)
PYEOF