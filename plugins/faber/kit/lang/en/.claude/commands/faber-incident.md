---
description: Incident shortcut — a fast flow with the Owner synchronous (containment → diagnosis → fix through the pipeline → a post-mortem that becomes the spec). Nothing straight to production (H1); the gates are compressed, but the human ones are still the Owner's.
argument-hint: <what happened> [SEV1|SEV2|SEV3]
---

# /faber-incident

You are the CTO (CLAUDE.md). Incident reported by @@FABER_OWNER_NAME@@: **$ARGUMENTS**

The type is already classified as `incident` (§14) — **a fast flow, with the
Owner synchronous** (this command ignores `FABER_INTERACTION`: an incident is
always synchronous). The golden rule: **no fixing straight in production** (H1) —
containment and the fix both go through the pipeline. Do this in order (the
mechanics belong to the scripts, never to hand):

1. **Severity** (SEV1 total · SEV2 degraded · SEV3 localised) + a **short title**
   (≤ 70 chars). SEV1/SEV2 → align with @@FABER_OWNER_NAME@@ **now**.
2. Create the demand: `faber/scripts/new-task.sh incident "<title>"`
3. **Immediate containment** — stop the bleeding. Any operational action that
   touches **production** (rollback, feature flag, revert) **belongs to the
   Owner** — H1 stops the agent; you **record the evidence**:
   `faber/scripts/evidence.sh TASK-XXX containment -- <the containment command or check>`
   Containment is **not** the fix — it stops the bleeding.
4. **Diagnosis (root cause)** — with evidence that confirms the cause (do not infer it).
5. **The real fix, through the pipeline** — on the demand's branch:
   `senior-developer` (+ `devsecops` if it is pipeline or infra, + `db-guardian`
   if it is data). The CTO's gates are **compressed** (a lean G3/G4/G5), but
   **G1/G6/G8 remain the Owner's** (synchronous, never skipped). Production only
   through CI or a merge.
6. **The post-mortem is the spec:** invoke the `spec-task` skill (template
   `spec-incident`): timeline, containment, diagnosis, fix, **post-mortem**,
   child demands. Fill it in as you go — the post-mortem is the heart of the spec.
7. **Child demands** for prevention (what stops the next one) through
   `/faber-task`, with `related_to: TASK-XXX`.
8. **Report** to @@FABER_OWNER_NAME@@: TASK-XXX, the severity, the containment
   applied (with evidence), the root cause, the plan for the fix, and the
   proposed child demands (a single block — §20).
