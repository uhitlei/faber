---
description: Atalho de spike/investigação — tipo já classificado; timebox no intake, saída = mini-ADR (sem implementação de produção), pode gerar demandas filhas
argument-hint: <pergunta técnica a investigar> [timebox]
---

# /faber-spike

Você é o CTO (CLAUDE.md). Investigação (spike) pedida por @@FABER_OWNER_NAME@@: **$ARGUMENTS**

Tipo já classificado como `spike` (§14) — investigação com timebox, **sem
implementação de produção**. Execute nesta ordem:

1. Defina o **timebox** no intake (peça a @@FABER_OWNER_NAME@@ se não veio no
   pedido) e derive um **título curto** (≤ 70 chars) da pergunta.
2. Crie a demanda: `faber/scripts/new-task.sh spike "<título>"`
   (cria issue + branch em worktree próprio + pasta + board; trabalhe a partir
   do `WORKTREE=…` impresso).
3. **Spec do spike:** invoque a Skill `spec-task` (template `spec-spike`): §1
   pergunta, §2 contexto, §3 investigação, §4 **mini-ADR** (a saída), §5 demandas
   filhas. Registre o **timebox** e respeite-o: estourou → pare e registre o que
   houver. Commit do rascunho na branch.
4. Avance o estado: `faber/scripts/transition.sh TASK-XXX specifying`
5. **Investigue** (CTO + `senior-developer` se preciso): leitura, provas de
   conceito descartáveis, medições. **Nada de código de produção** (§14).
   Medição com comando executado → grave via
   `faber/scripts/evidence.sh TASK-XXX <slug> -- <comando>`.
6. **Saída = decisão técnica:** consolide o **mini-ADR** (contexto, opções,
   decisão, autor, data) em `faber/tasks/TASK-XXX/decisions.md` (§15).
7. **Demandas filhas:** o que o spike recomendar implementar vira nova(s)
   demanda(s) via `/faber-task`, com `relacionada_a: TASK-XXX` — **nunca**
   implemente aqui.
8. **Reporte** a @@FABER_OWNER_NAME@@: TASK-XXX, o mini-ADR (decisão) e as
   demandas filhas propostas (um único bloco — §20).

## Encadeamento (FABER_INTERACTION)

- **`gates`**: execute 1–8 sem parar (o timebox é o limite); pare no passo 8
  para o Owner decidir sobre as demandas filhas.
- **`step-by-step`**: pare após o passo 4 (spec pronta) e aguarde ok para investigar.
