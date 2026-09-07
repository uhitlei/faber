---
description: The post-G1 development flow — implementation (senior-developer), G3, a frozen diff, a clean-context review, G4, and technical validation G5 (QA ∥ db-guardian ∥ devsecops)
argument-hint: TASK-XXX
---

# /faber-develop

Demand: **$ARGUMENTS** — precondition: state `in-development` (G1 approved by
@@FABER_OWNER_NAME@@ through `/faber-approve`).

This command encodes the choreography between G1 and `/faber-validate`. The
mechanics always go through the scripts — never by hand. Work in the demand's
worktree.

0. **Approval still valid:** run `faber/scripts/gate-check.sh TASK-XXX in-development`
   before invoking the developer, even when resuming in the same state. If
   discovery changed since G1, the gate blocks: reconcile and renew the approval
   before continuing.

1. **Implementation:** invoke the `senior-developer` subagent (Mode 2) with the
   minimum contract — the paths to the demand's `spec.md` and `refinement.md`,
   never a dump of the project. Its handoff is validated by H5 (and counts
   toward `invocations`; anti-loop §15).

2. **Developed + G3:**
   - `faber/scripts/transition.sh TASK-XXX developed`
     (gate-check requires the lint/build/test logs in `evidence/`);
   - `faber/scripts/gate-set.sh TASK-XXX G3 approved --by gate-check --evidence "evidence/<NN>-test-run.log"`
     — G3 belongs to `gate-check` (§18); the record **mirrors** the transition
     that was released, with the real NN of the test log.

3. **Push + frozen diff:**
   - `git push -u origin feature/TASK-XXX` (the `code-review` destination
     requires the branch on the remote — and the push triggers the branch CI
     used in step 6);
   - `faber/scripts/evidence.sh TASK-XXX diff -- bash -c "git fetch -q origin @@FABER_TRUNK@@ && git diff origin/@@FABER_TRUNK@@...HEAD"`

4. **Clean-context review:**
   - `faber/scripts/transition.sh TASK-XXX code-review`;
   - invoke `code-reviewer` with **only**: `spec.md`, the path to the frozen
     diff, and the cited sections of `06-CONVENTIONS`/`03-SECURITY`. No developer
     handoffs, no narrative of the implementation (it contaminates the review).

5. **G4:** if the verdict is `blocked` → mirror the correction tasks onto the
   issue and regress: `faber/scripts/transition.sh TASK-XXX in-development --reason "review: <summary>"`
   (corrections come back through this same flow). Otherwise:
   - `faber/scripts/gate-set.sh TASK-XXX G4 approved --by cto --evidence "review.md"`
   - `faber/scripts/transition.sh TASK-XXX validation`

6. **G5 — parallel validations** (§5): fire these in a single round
   - `qa` (Mode 2): acceptance criteria + regression; E2E through the
     `e2e-runner` skill when `ui_impact: true` (evidence of the command run
     **directly**, with no pipe);
   - `db-guardian` (Mode 2) if the demand touches the database;
   - `devsecops` (Role 2): Sonar through the `sonar-gate` skill when
     `FABER_SONAR=on`; otherwise the branch CI:
     `faber/scripts/evidence.sh TASK-XXX ci-branch -- gh run list --branch feature/TASK-XXX --limit 3`
     and `... ci-run -- gh run view <run-id>`.
   Criterion: everything green **or a formally documented exception** (Medium/Low,
   coverage — Critical/High never). "Not executed" never becomes approved
   (CLAUDE.md §4).
   - Green → `faber/scripts/gate-set.sh TASK-XXX G5 approved --by cto --evidence "evidence/<NN>-<slug>.log"`
   - Red → regress with a reason (`in-development`) and go back to step 1.

7. **Continue to `/faber-validate TASK-XXX`** — G6 belongs to @@FABER_OWNER_NAME@@.

## Chaining (FABER_INTERACTION)

- **`gates`**: run 1–7 without stopping, `/faber-validate` included; stop only at G6.
- **`step-by-step`**: stop after G3, after G4 and after G5, waiting for an ok.
