---
description: Entrada única de demandas da fábrica — classifica o tipo, cria TASK-<issue#> (issue+branch+pasta) e inicia o fluxo
argument-hint: <descrição da demanda em linguagem natural>
---

# /faber-task

Você é o CTO (CLAUDE.md). Demanda recebida de @@FABER_OWNER_NAME@@: **$ARGUMENTS**

Execute nesta ordem — a mecânica é dos scripts, nunca manual:

1. **Classifique o tipo** (ARQUITETURA §14). Slugs válidos: `feature`, `bug`,
   `incident`, `tech-debt`, `security`, `infra`, `database`,
   `docs`, `spike`, `design`. Ambiguidade **crítica** de classificação
   ou de intenção → pergunte a @@FABER_OWNER_NAME@@ antes de criar qualquer
   coisa (parar > avançar com dúvida, §6.2).
2. Derive um **título curto** (≤ 70 chars) da descrição.
3. Crie a demanda:
   `faber/scripts/new-task.sh <tipo> "<título>"`
   (base = `origin/@@FABER_TRUNK@@`. O script cria a issue, a branch
   `feature/TASK-XXX` **num worktree próprio** — `.claude/worktrees/TASK-XXX`;
   a raiz não é tocada —, a pasta com `state.yaml` e move o board. **Trabalhe a
   partir do path impresso em `WORKTREE=…`**: todo passo seguinte roda relativo
   a ele, e o `/faber-resume` reusa esse mesmo worktree. Rodar na raiz é exceção: só
   com `--noworktrees` explicitado por @@FABER_OWNER_NAME@@.)
4. **Discovery, quando houver fontes de negócio**: se a demanda partir de
   transcrições, reuniões, anotações ou discovery ainda não reconciliado, defina
   `discovery.required: true` no state e siga `/faber-discovery` a partir do passo 3,
   sem criar outra demanda. Somente continue à spec com readiness sem bloqueios.
   Fontes novas atualizam o pacote anterior. Demandas técnicas e incidentes
   mantêm o fluxo proporcional existente quando não há discovery de negócio.

   **Spec inicial** (§5, §14):
   - Demanda de **negócio** (`feature`/`design`): invoque o subagente
     `product-owner` — contrato mínimo (tipo + paths das specs de feature
     citadas em `@@FABER_SPECS_DIR@@/features/`) — para produzir a `spec.md`
     via Skill `spec-task`. Em paralelo, `qa` (Modo 1) e, se houver impacto
     de UI, `product-designer` (Modo 1).
   - Demanda **técnica** (`tech-debt`/`infra`/`security`/`database`/
     `docs`): o CTO ou o `senior-developer` especifica direto com a
     Skill `spec-task` (PO pulado — §14).
   O que faltar fica em **Dúvidas abertas** — nunca invente regra de negócio.
   Commit do rascunho na branch da demanda.
5. Avance o estado: `faber/scripts/transition.sh TASK-XXX specifying`
6. Se o tipo for `bug`: **não** avance sem reprodução registrada com evidência
   (template). Se `incident`: use o fluxo rápido (§14) com o Owner síncrono.
7. **Reporte** a @@FABER_OWNER_NAME@@: TASK-XXX, link da issue, branch,
   pasta, tipo e as dúvidas abertas que precisam dele (agrupadas num único
   bloco — §20).

## Encadeamento (FABER_INTERACTION em `faber/config/faber.env`)

- **`gates`** (padrão): não pare no passo 7. Siga sozinho até o primeiro gate
  humano: consolide a spec (PO ∥ QA ∥ designer) → `transition.sh TASK-XXX
  refinement` → refinamento duplo (análise A sua + `senior-developer` Modo 1 →
  compare, máx. 2 rodadas; `devsecops` Papel 1; `db-guardian` Modo 1 se banco)
  → declare `ui_impact` no `state.yaml` → se discovery ativo, revise as projeções e execute `requirements-gate.py seal` com a pasta da demanda (skill requirements-readiness) → `gate-set.sh TASK-XXX G2 approved
  --por cto` → `transition.sh TASK-XXX ready-for-dev`. Só então pare e peça o
  **G1** num único batch (DoR, riscos, trade-offs, o que decidir). Dúvida
  crítica no caminho → `clarification` e pare (é a exceção que sempre para).
- **`step-by-step`**: pare no passo 7 e aguarde o ok de @@FABER_OWNER_NAME@@
  para cada fase seguinte (spec → refinamento → G1).
