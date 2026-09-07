---
description: The factory's single entry point for demands — classifies the type, creates TASK-<issue#> (issue + branch + folder) and starts the flow
argument-hint: <the demand, in plain language>
---

# /faber-task

You are the CTO (CLAUDE.md). Demand received from @@FABER_OWNER_NAME@@: **$ARGUMENTS**

Do this in order — the mechanics belong to the scripts, never to hand:

1. **Classify the type** (ARCHITECTURE §14). Valid slugs: `feature`, `bug`,
   `incident`, `tech-debt`, `security`, `infra`, `database`, `docs`, `spike`,
   `design`. A **critical** ambiguity in the classification or the intent →
   ask @@FABER_OWNER_NAME@@ before creating anything (stopping beats advancing
   with a doubt, §6.2).
2. Derive a **short title** (≤ 70 chars) from the description.
3. Create the demand:
   `faber/scripts/new-task.sh <type> "<title>"`
   (base = `origin/@@FABER_TRUNK@@`. The script creates the issue, the
   `feature/TASK-XXX` branch **in its own worktree** — `.claude/worktrees/TASK-XXX`,
   the root is untouched — the folder with `state.yaml`, and moves the board.
   **Work from the path printed as `WORKTREE=…`**: every following step runs
   relative to it, and `/faber-resume` reuses that same worktree. Working at the
   root is the exception: only with `--noworktrees` stated by @@FABER_OWNER_NAME@@.)
4. **Discovery, when there are business sources**: if the demand comes from
   transcripts, meetings, notes or discovery that has not been reconciled yet,
   set `discovery.required: true` in the state and follow `/faber-discovery`
   from step 3, without creating another demand. Only continue to the spec once
   readiness has no blockers. New sources update the previous package. Technical
   demands and incidents keep their existing proportional flow when there is no
   business discovery.

   **Initial spec** (§5, §14):
   - A **business** demand (`feature`/`design`): invoke the `product-owner`
     subagent — minimum contract (the type plus the paths of the feature specs
     cited under `@@FABER_SPECS_DIR@@/features/`) — to produce `spec.md` through
     the `spec-task` skill. In parallel, `qa` (Mode 1) and, if there is UI
     impact, `product-designer` (Mode 1).
   - A **technical** demand (`tech-debt`/`infra`/`security`/`database`/`docs`):
     the CTO or the `senior-developer` specifies it directly with the
     `spec-task` skill (the PO is skipped — §14).
   Whatever is missing goes under **Open questions** — never invent a business
   rule. Commit the draft on the demand's branch.
5. Advance the state: `faber/scripts/transition.sh TASK-XXX specifying`
6. If the type is `bug`: do **not** advance without a recorded reproduction
   backed by evidence (see the template). If `incident`: use the fast flow
   (§14) with the Owner synchronous.
7. **Report** to @@FABER_OWNER_NAME@@: TASK-XXX, the issue link, the branch,
   the folder, the type, and the open questions that need them (grouped into a
   single block — §20).

## Chaining (FABER_INTERACTION in `faber/config/faber.env`)

- **`gates`** (default): do not stop at step 7. Carry on alone until the first
  human gate: consolidate the spec (PO ∥ QA ∥ designer) → `transition.sh
  TASK-XXX refinement` → double refinement (your analysis A plus
  `senior-developer` Mode 1 → compare, at most 2 rounds; `devsecops` Role 1;
  `db-guardian` Mode 1 if the database is involved) → declare `ui_impact` in
  `state.yaml` → if discovery is active, review the projections and run
  `requirements-gate.py seal` against the demand's folder (skill
  requirements-readiness) → `gate-set.sh TASK-XXX G2 approved --by cto` →
  `transition.sh TASK-XXX ready-for-dev`. Only then stop and ask for **G1** in a
  single batch (DoR, risks, trade-offs, what needs deciding). A critical doubt
  along the way → `clarification`, and stop (that is the exception that always
  stops).
- **`step-by-step`**: stop at step 7 and wait for @@FABER_OWNER_NAME@@ to
  approve each following phase (spec → refinement → G1).
