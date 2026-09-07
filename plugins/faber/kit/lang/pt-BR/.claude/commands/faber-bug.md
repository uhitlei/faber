---
description: Atalho de bug — tipo já classificado; exige reprodução com evidência ANTES da spec, depois spec reduzida (repro + causa raiz + fix + teste de regressão) e o fluxo dev → qa → reviewer (PO pulado)
argument-hint: <descrição do bug / como reproduzir>
---

# /faber-bug

Você é o CTO (CLAUDE.md). Bug reportado por @@FABER_OWNER_NAME@@: **$ARGUMENTS**

Tipo já classificado como `bug` (§14) — não reclassifique. Execute nesta ordem
(a mecânica é dos scripts, nunca manual):

1. Derive um **título curto** (≤ 70 chars) do sintoma.
2. Crie a demanda: `faber/scripts/new-task.sh bug "<título>"`
   (cria issue + branch `feature/TASK-XXX` em worktree próprio + pasta + board;
   trabalhe a partir do `WORKTREE=…` impresso).
3. **Reprodução obrigatória ANTES da spec** (§14 — regra de ouro do bug):
   reproduza o defeito e **grave a evidência** que falha:
   `faber/scripts/evidence.sh TASK-XXX repro -- <comando que reproduz o bug>`
   Sem reprodução registrada com evidência, a spec **não avança** (o template
   `spec-bug` bloqueia). Não reproduziu? Estado `clarification` com o Owner —
   não avance no escuro (§6.2).
4. **Spec reduzida:** invoque a Skill `spec-task` (template `spec-bug`): §1
   reprodução (com o path da evidência), §2 esperado×observado, §3 causa raiz,
   §4 fix, §5 **teste de regressão que falha antes e passa depois**. Não inchar.
   Commit do rascunho na branch da demanda.
5. Avance o estado: `faber/scripts/transition.sh TASK-XXX specifying`
6. **Fluxo do bug** (§14): PO **pulado** — o CTO/dev especifica; segue
   `senior-developer` → `qa` → `code-reviewer`. QA proporcional ao impacto.
7. **Reporte** a @@FABER_OWNER_NAME@@: TASK-XXX, link da issue, branch, a
   evidência de reprodução e as dúvidas abertas (um único bloco — §20).

## Encadeamento (FABER_INTERACTION)

- **`gates`**: após o passo 7 siga sozinho — refinamento enxuto (causa raiz +
  fix + arquivos prováveis; `impacto_ui` declarado) → G2 → `ready-for-dev` —
  e pare pedindo o **G1** num único batch.
- **`step-by-step`**: pare no passo 7 e aguarde o ok para cada fase.
