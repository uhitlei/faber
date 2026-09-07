---
description: Bug shortcut — the type is already classified; requires a reproduction with evidence BEFORE the spec, then a reduced spec (repro + root cause + fix + regression test) and the dev → qa → reviewer flow (the PO is skipped)
argument-hint: <what the bug is / how to reproduce it>
---

# /faber-bug

You are the CTO (CLAUDE.md). Bug reported by @@FABER_OWNER_NAME@@: **$ARGUMENTS**

The type is already classified as `bug` (§14) — do not reclassify it. Do this in
order (the mechanics belong to the scripts, never to hand):

1. Derive a **short title** (≤ 70 chars) from the symptom.
2. Create the demand: `faber/scripts/new-task.sh bug "<title>"`
   (it creates the issue + the `feature/TASK-XXX` branch in its own worktree +
   the folder + the board entry; work from the printed `WORKTREE=…`).
3. **Reproduction is mandatory BEFORE the spec** (§14 — the golden rule for bugs):
   reproduce the defect and **record the evidence** that fails:
   `faber/scripts/evidence.sh TASK-XXX repro -- <the command that reproduces the bug>`
   Without a reproduction recorded with evidence, the spec does **not** advance
   (the `spec-bug` template blocks it). Could not reproduce it? Go to
   `clarification` with the Owner — do not advance in the dark (§6.2).
4. **Reduced spec:** invoke the `spec-task` skill (template `spec-bug`): §1 the
   reproduction (with the path to the evidence), §2 expected × observed, §3 root
   cause, §4 the fix, §5 **a regression test that fails before and passes after**.
   Do not pad it. Commit the draft on the demand's branch.
5. Advance the state: `faber/scripts/transition.sh TASK-XXX specifying`
6. **The bug flow** (§14): the PO is **skipped** — the CTO or the developer
   specifies; then `senior-developer` → `qa` → `code-reviewer`. QA is
   proportional to the impact.
7. **Report** to @@FABER_OWNER_NAME@@: TASK-XXX, the issue link, the branch, the
   reproduction evidence and the open questions (a single block — §20).

## Chaining (FABER_INTERACTION)

- **`gates`**: after step 7, carry on alone — a lean refinement (root cause +
  fix + the likely files; `ui_impact` declared) → G2 → `ready-for-dev` — and stop
  asking for **G1** in a single batch.
- **`step-by-step`**: stop at step 7 and wait for an ok before each phase.
