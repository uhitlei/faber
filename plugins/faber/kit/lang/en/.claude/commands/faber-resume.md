---
description: Rebuilds a demand's context from disk and continues where it stopped — sessions are disposable, isolated in a worktree
argument-hint: TASK-XXX
---

# /faber-resume

Demand: **$ARGUMENTS**

Sessions are disposable; the source of truth is the disk (CLAUDE.md §4). Never
trust the memory of an earlier session: **what is not on disk did not happen**.

0. **Open the worktree** (concurrency isolation between instances; the mechanics
   belong to the script, never to hand):
   `faber/scripts/worktree.sh open TASK-XXX`
   - It fetches the **current trunk** (`@@FABER_TRUNK@@`), resolves
     `feature/TASK-XXX` (local or remote — if the folder is not in the working
     tree but the branch exists, the worktree pulls it) and **merges the trunk**
     into the branch (every resume starts from the current trunk).
   - **Merge conflict** (exit 3): **stop**, resolve and commit inside the
     worktree (or `merge --abort`), and only then continue — never advance with
     an open conflict (§6.2).
   - **Demand not in git** (no branch): the demand was never opened. **Stop** and
     tell @@FABER_OWNER_NAME@@ to open it with `/faber-task`.
   - Work from the path printed as `WORKTREE=…` (every path below is relative to
     that worktree).
1. Read, in this order, whatever exists under `faber/tasks/TASK-XXX/`:
   `state.yaml` (state, gates, `history`, `blocking`, `invocations`,
   `ui_impact`), `spec.md`, `refinamento.md`, `decisions.md`, `tarefas.md`,
   `review.md`, the handoff with the **highest numeric prefix** in `handoffs/`,
   and `log.md`.
   If discovery is active or `requirements/` exists, read sources, model,
   assessment and the BA's handoff. Run `requirements-gate.py report` to
   recompute; do not trust an old `readiness.json`. Check the seal and the G1
   binding before resuming development; changes require reconciling and renewing
   the approval.
2. Sync the projections: `faber/scripts/board.sh status <issue#>` and
   `gh issue view <issue#> --comments` (the latest comments) — when `FABER_GH=on`.
3. If `state: blocked`: report `blocking.reason` and what is missing to clear it;
   the return is always to `blocking.previous_state` (§6.2).
4. Summarise for @@FABER_OWNER_NAME@@ in ≤ 10 lines: where the demand stands,
   what has already been validated (with the evidence that exists), the flow's
   next step (§5/§6.2), and what depends on them.
5. **Continue** from the next step — without redoing work that already has
   evidence; respect the anti-loop (§15: at most 2 invocations of the same
   subagent with the same input; count them from `invocations` in `state.yaml`).
   With `FABER_INTERACTION=gates`, carry on to the next human gate; with
   `step-by-step`, stop after the summary and wait for an ok.
6. **When ending** the resumed session, close the worktree (cleanup):
   `faber/scripts/worktree.sh close TASK-XXX`. It **refuses** if there are
   uncommitted changes (the work lives on the branch: commit first). The branch
   and the commits survive; only the disposable checkout is removed.
