---
description: Reconstrói o contexto de uma demanda a partir do disco e continua de onde parou — sessões são descartáveis, isoladas em worktree
argument-hint: TASK-XXX
---

# /faber-resume

Demanda: **$ARGUMENTS**

Sessões são descartáveis; a fonte de verdade é o disco (CLAUDE.md §4).
Nunca confie na memória de sessões anteriores: **o que não está em disco não
aconteceu**.

0. **Abra o worktree** (isolamento de concorrência entre instâncias; a mecânica
   é do script, nunca manual):
   `faber/scripts/worktree.sh abrir TASK-XXX`
   - Ele faz `fetch` do **trunk atual** (`@@FABER_TRUNK@@`), resolve
     `feature/TASK-XXX` (local ou remota — se a pasta não está no working
     tree mas a branch existe, o worktree a puxa) e **mescla o trunk** na
     branch (todo resume parte do trunk atual).
   - **Conflito de merge** (exit 3): **pare**, resolva/commite no worktree (ou
     `merge --abort`) e só então continue — nunca avance com o conflito aberto (§6.2).
   - **Demanda inexistente no git** (sem branch): a demanda nunca foi aberta.
     **Pare** e oriente @@FABER_OWNER_NAME@@ a abrir com `/faber-task`.
   - Trabalhe a partir do path impresso em `WORKTREE=…` (todo caminho abaixo é
     relativo a esse worktree).
1. Leia, nesta ordem, o que existir em `faber/tasks/TASK-XXX/`:
   `state.yaml` (estado, gates, `historico`, `bloqueio`, `invocacoes`,
   `impacto_ui`), `spec.md`, `refinamento.md`, `decisions.md`, `tarefas.md`,
   `review.md`, o handoff de **maior prefixo numérico** em `handoffs/` e o `log.md`.
   Se houver discovery ativo ou `requirements/`, leia sources, model,
   assessment e handoff BA. Rode requirements-gate.py report para recalcular;
   não confie em readiness.json antigo. Confira selo e vínculo G1 antes de
   retomar desenvolvimento; mudanças exigem reconciliar e renovar aprovação.
2. Sincronize as projeções: `faber/scripts/board.sh status <issue#>` e
   `gh issue view <issue#> --comments` (últimos comentários) — se `FABER_GH=on`.
3. Se `estado: blocked`: reporte `bloqueio.motivo` e o que falta para sanar;
   o retorno é sempre para `bloqueio.estado_origem` (§6.2).
4. Resuma para @@FABER_OWNER_NAME@@ em ≤ 10 linhas: onde a demanda está, o que
   já foi validado (com as evidências existentes), qual o próximo passo do fluxo
   (§5/§6.2) e o que depende dele.
5. **Continue** a partir do próximo passo — sem refazer trabalho já
   evidenciado; respeite o anti-loop (§15: máx. 2 invocações do mesmo
   subagente com o mesmo input; conte pelas `invocacoes` do state.yaml). Em
   `FABER_INTERACTION=gates`, siga até o próximo gate humano; em
   `step-by-step`, pare após o resumo e aguarde ok.
6. **Ao encerrar** a sessão de retomada, feche o worktree (limpeza):
   `faber/scripts/worktree.sh fechar TASK-XXX`. Ele **recusa** se houver
   mudança não-commitada (o trabalho vive na branch: commite antes). A branch e
   os commits sobrevivem; só o checkout descartável é removido.
