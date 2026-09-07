---
description: Estado consolidado de uma demanda (ou de todas) lido do disco e do GitHub — nunca da memória da sessão
argument-hint: "[TASK-XXX]"
---

# /faber-status

Argumento (opcional): **$ARGUMENTS**

Tudo é lido **agora, do disco e do `gh`** — o que não está lá não aconteceu.
Atalho sem LLM: `python3 faber/scripts/monitor.py --once` (snapshot) ou sem
`--once` (monitor vivo no terminal).

**Sem argumento (visão geral):**
1. Liste `faber/tasks/TASK-*/state.yaml`; para cada uma: demanda,
   tipo, estado, última entrada do `historico`, bloqueio (se houver).
2. Destaque a **fila de @@FABER_OWNER_NAME@@** (batching, §20): demandas
   paradas em gate humano — `ready-for-dev` aguardando G1, `minha-avaliacao`
   aguardando G6, `pr-open` aguardando G8 — com o link de cada issue.
3. Se `faber/bootstrap/CONTEXT.md` tiver `status: pendente`, diga que o
   bootstrap da fábrica ainda não foi concluído (`/faber-init`).

**Com TASK-XXX:**
1. `state.yaml`: estado, bloqueio, últimas 3 transições do `historico`,
   tabela dos 9 gates (status/aprovador/evidência), `impacto_ui`.
2. `faber/scripts/board.sh status <issue#>` (coluna real + labels; no-op se
   `FABER_GH=off`).
3. `gh issue view <issue#> --comments` (últimos 3 comentários) — se `FABER_GH=on`.
4. Handoff de maior prefixo numérico em `handoffs/` (se existir):
   `proxima_acao_sugerida` e `pendencias`.
5. Divergência entre as projeções (state × board × issue)? Aponte e sugira
   reconciliar via `board.sh` — `state.yaml` é a fonte de verdade (§6.1).

Formato: tabela curta + no máximo 5 linhas de prosa com a próxima ação.
