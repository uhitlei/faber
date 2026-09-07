---
description: Records the Owner's approval of a human gate (G1/G6/G8) and unlocks the matching transition
argument-hint: TASK-XXX <G1|G6|G8>
---

# /faber-approve

Arguments: **$ARGUMENTS**

This command records **@@FABER_OWNER_NAME@@**'s decision — G1, G6 and G8 belong
to them alone (CLAUDE.md §1). The CTO **never** runs `/faber-approve` on its own
initiative; if this command was typed, the Owner is the one who approved.

1. Confirm in your reply which gate is being approved and for which demand;
   if the argument is ambiguous (no gate, or no TASK), ask.
2. Record it (mechanics by script, with `@@FABER_OWNER@@` as the author):
   `faber/scripts/gate-set.sh TASK-XXX <gate> approved --by @@FABER_OWNER@@ --evidence "approved by @@FABER_OWNER_NAME@@ via /faber-approve on <date>"`
   (H1 asks for confirmation on this command: confirming the dialog **is** the approval.)
3. Unlock the flow's transition (§5/§6.2):
   - **G1** → `faber/scripts/transition.sh TASK-XXX in-development`
   - **G6** → `faber/scripts/transition.sh TASK-XXX ready-for-pr`
   - **G8** (the Owner has already merged on GitHub) → final consolidation:
     invoke `doc-writer` (skill `spec-sync`) to consolidate
     `@@FABER_SPECS_DIR@@/` from the already-merged trunk — the documentation
     changes go on a `docs/TASK-XXX-specs` branch and become a closing PR,
     because `@@FABER_TRUNK@@` never receives a direct push (H1). Then record
     `gate-set.sh TASK-XXX G9 approved --by cto` and
     `transition.sh TASK-XXX done`.
     **Mandatory cleanup on entering `done`:**
     `faber/scripts/worktree.sh clean TASK-XXX` — closes the worktree and
     **deletes the demand's branch**, local and remote. Fail-closed: it refuses
     if the branch is not merged into the trunk (exit 2). With `FABER_SONAR=on`,
     delete the mirror too: `faber/scripts/sonar-task.sh delete TASK-XXX`.
4. If `gate-check` blocks the transition, **do not force it**: report the
   pending items it listed and resolve them first.
5. Report the new state and the flow's next action.

## Chaining (FABER_INTERACTION)

- **`gates`**: after **G1**, run `/faber-develop TASK-XXX` and then
  `/faber-validate TASK-XXX` without stopping (stop only at G6). After **G6**,
  run `/faber-pr TASK-XXX` (stop at G8). After **G8**, finish G9 → `done` →
  cleanup.
- **`step-by-step`**: stop at step 5 and wait for the Owner to call the next command.

The CTO's own gates (G2/G4/G5/G7/G9) do **not** go through `/faber-approve` —
they are recorded inside the flow itself with `gate-set.sh ... --by cto` plus evidence.
