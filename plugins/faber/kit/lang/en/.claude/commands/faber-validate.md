---
description: Prepares gate G6 (My Review) — brings up the local environment (if configured) and the build, and hands the Owner a step-by-step test script on the issue
argument-hint: TASK-XXX
---

# /faber-validate

Demand: **$ARGUMENTS**

Prepares G6 (§12/§18): a ready environment plus a test script. Precondition:
state `validation` with G5 approved (check `state.yaml`; if G5 is pending, stop
and report what is missing — never skip technical validation).

1. **Transition to `my-review`:**
   `faber/scripts/transition.sh TASK-XXX my-review`
   (gate-check requires G5 approved and, with `ui_impact: true` and
   `FABER_E2E=on`, evidence of an executed E2E run; if it blocks → resolve the
   pending items first).
2. **Environment, with real evidence:**
   - If `FABER_LOCAL_ENV=on` (skill `local-env`; a stopped dependency → ask the
     Owner to start it):
     `faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`
     `faber/scripts/evidence.sh TASK-XXX seed-local -- faber/scripts/local-env.sh seed`
   - Always: `faber/scripts/evidence.sh TASK-XXX build-validation -- @@FABER_CMD_BUILD@@`
   - Bring up whatever the Owner needs in order to test (e.g. a dev server —
     give them the URL; long-running processes go to the background, never block
     the session).
3. **Test script** derived from the acceptance criteria in `spec.md`: a
   clickable step-by-step (screen or command, action, expected result), with the
   test data and users documented in
   `@@FABER_SPECS_DIR@@/global/05-TESTING.md`, and which AC each step covers.
   Include the relevant exception cases from the spec.
4. **Summary on the issue — MANDATORY (§20).** The Owner validates from the
   **issue**, not from the chat. Before asking for approval, write the summary
   to `faber/tasks/TASK-XXX/validation-g6.md` and **post it on the issue**:
   - **(i)** a brief summary of **what was done**;
   - **(ii)** the review's **caveats** (from `review.md`: what was fixed, and
     what became a follow-up or a child demand);
   - **(iii)** **exactly what to validate** — the clickable script plus the
     approval phrase.

   Post it with: `faber/scripts/board.sh comment-file <issue#> faber/tasks/TASK-XXX/validation-g6.md`
   (with `FABER_GH=off`, the file on disk is the source — point at the path in
   the chat).
5. **Batch in the chat:** point at the issue comment (the single source) plus
   the expected approval phrase: reply **"TASK-XXX validated"** (G6 approved —
   follow with `/faber-approve TASK-XXX G6`) or **reject with the reason**.
6. **If rejected:** record the reason and regress:
   `faber/scripts/transition.sh TASK-XXX in-development --reason "<the Owner's reason>"`
   (the fixes follow the normal flow: dev → G3 → review → validation → G6).

This command **always stops** at step 5 — G6 is human, in either interaction mode.
