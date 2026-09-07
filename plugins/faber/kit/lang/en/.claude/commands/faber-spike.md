---
description: Spike/investigation shortcut — the type is already classified; a timebox at intake, the output is a mini-ADR (no production implementation), and it may spawn child demands
argument-hint: <the technical question to investigate> [timebox]
---

# /faber-spike

You are the CTO (CLAUDE.md). Investigation (spike) requested by @@FABER_OWNER_NAME@@: **$ARGUMENTS**

The type is already classified as `spike` (§14) — a timeboxed investigation,
**with no production implementation**. Do this in order:

1. Set the **timebox** at intake (ask @@FABER_OWNER_NAME@@ if it did not come
   with the request) and derive a **short title** (≤ 70 chars) from the question.
2. Create the demand: `faber/scripts/new-task.sh spike "<title>"`
   (it creates the issue + the branch in its own worktree + the folder + the
   board entry; work from the printed `WORKTREE=…`).
3. **The spike's spec:** invoke the `spec-task` skill (template `spec-spike`):
   §1 the question, §2 context, §3 the investigation, §4 the **mini-ADR** (the
   output), §5 child demands. Record the **timebox** and respect it: if it runs
   out, stop and record whatever you have. Commit the draft on the branch.
4. Advance the state: `faber/scripts/transition.sh TASK-XXX specifying`
5. **Investigate** (the CTO, plus `senior-developer` if needed): reading,
   disposable proofs of concept, measurements. **No production code** (§14). A
   measurement made by running a command → record it with
   `faber/scripts/evidence.sh TASK-XXX <slug> -- <command>`.
6. **The output is a technical decision:** consolidate the **mini-ADR** (context,
   options, decision, author, date) in `faber/tasks/TASK-XXX/decisions.md` (§15).
7. **Child demands:** whatever the spike recommends implementing becomes one or
   more new demands through `/faber-task`, with `related_to: TASK-XXX` — **never**
   implement it here.
8. **Report** to @@FABER_OWNER_NAME@@: TASK-XXX, the mini-ADR (the decision) and
   the proposed child demands (a single block — §20).

## Chaining (FABER_INTERACTION)

- **`gates`**: run 1–8 without stopping (the timebox is the limit); stop at step
  8 so the Owner can decide about the child demands.
- **`step-by-step`**: stop after step 4 (the spec is ready) and wait for an ok
  before investigating.
