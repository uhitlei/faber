---
description: Post-G6 — checks every gate, updates the branch with the trunk, consolidates the description (what/why/how to test/risk/rollback) and opens the PR
argument-hint: TASK-XXX
---

# /faber-pr

Demand: **$ARGUMENTS**

Runs G7 and opens the PR (§12/§18-G7). Precondition: G6 approved by
@@FABER_OWNER_NAME@@ (through `/faber-approve`) and state `ready-for-pr`.
Merging the PR (G8) is **always the Owner's, on GitHub** — you never merge.

1. **Check the gates** in `state.yaml`: G1–G6 `approved`/`not-applicable`
   (self-approval of a human gate is impossible — but check anyway). Anything
   pending → stop and report.
2. **Update the branch with the trunk** (on the demand's branch):
   `faber/scripts/evidence.sh TASK-XXX merge-trunk -- bash -c "git fetch origin @@FABER_TRUNK@@ && git merge --no-edit origin/@@FABER_TRUNK@@"`
   Conflicts: resolve them within the demand's scope; a conflict that needs a
   product decision → `clarification` with the Owner.
3. **Post-merge sanity** (real evidence):
   `faber/scripts/evidence.sh TASK-XXX lint-post-merge -- @@FABER_CMD_LINT@@`
   `faber/scripts/evidence.sh TASK-XXX build-post-merge -- @@FABER_CMD_BUILD@@`
   `faber/scripts/evidence.sh TASK-XXX test-post-merge -- @@FABER_CMD_TEST@@`
   Red → fix it before going on (or regress with a reason).
4. **Record G7:**
   `faber/scripts/gate-set.sh TASK-XXX G7 approved --by cto --evidence "evidence/NN-merge-trunk.log"`
5. **Push the branch** (autonomous — it is a feature branch): `git push -u origin feature/TASK-XXX`
6. **Consolidate the PR description** by reading `spec.md`, `review.md`,
   `decisions.md` and `evidence/` — the structure is mandatory (§18-G7):
   - **What** (the scope delivered, the ACs) · **Why** (problem / value)
   - **How to test** (the short script from G6)
   - **Risk & rollback** (from the refinement / migration-safe; cite the migrations)
   - **Evidence** (paths to the lint/build/test/e2e/static-analysis logs in the
     demand's folder) · **Spec:** `faber/tasks/TASK-XXX/spec.md`
7. **Open the PR:** `gh pr create --base @@FABER_TRUNK@@ --title "type(scope): summary (TASK-XXX)" --body "<consolidated description>"`
   (with `FABER_GH=off`: write the description to `faber/tasks/TASK-XXX/pr.md`
   and pass `--pr pr.md` on the transition.)
8. **Transition:** `faber/scripts/transition.sh TASK-XXX pr-open --pr "<the PR url>"`
9. **Report to the Owner:** the PR link + a 3-line summary + a reminder that the
   merge (G8) is theirs; after the merge, follow the post-G8 steps in
   `/faber-approve` (G9 → done).

This command **always stops** at step 9 — G8 is human, in either interaction mode.
