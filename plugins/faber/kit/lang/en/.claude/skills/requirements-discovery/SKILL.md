---
name: requirements-discovery
description: Extract evidence from transcripts and documents, structure requirements, and run the clarification round that produces the factory's BRD/PRD. Use before the PO in discovery, or when folding new sources into an existing package.
---

# Requirements discovery

Read [the contract](references/contract.md) before creating or updating a
package. Use the four templates in `faber/templates/requirements/`. Never copy a
template over existing work. Read sources in parts when you must, keeping a
record of the coverage; economising on context does not license omitting
passages silently.

1. Record the sources and the SHA-256 of each file. Preserve speaker and
   timestamp where they exist; for notes, use the section and line. Never invent
   a location.
2. Extract quotations and classify each as a statement, a decision or an
   inference. A statement is not automatically a verified fact; a suggested
   solution is not an approved requirement.
3. Structure the context, goals, users, scope, journeys, rules, data, qualities,
   requirements and dependencies. Every requirement gets a stable ID, its
   evidence and its acceptance criteria; assumptions and conflicts stay explicit.
4. Produce `requirements/BRD.md` and `requirements/PRD.md` following the
   project's PRD/BRD guide. The header carries the revision, the status (draft or
   validated) and the origin `model.yaml`. The PRD preserves every active ID.
   Gaps appear in the drafts.
5. Use `requirements-readiness`. Prioritise the questions that change a rule,
   the scope, access, an integration or an acceptance criterion. Each question
   states its origin, its impact and who can answer it. Group them, normally up
   to five; adjust to the context.
6. Answers you receive become decision sources in a file, with evidence; update
   the affected requirements and resolutions, and increment the revision.
7. When it is complete, hand it to the CTO for the PO and QA. For the SDD
   projection, read [Spec Kit](references/spec-kit.md). Do not do technical
   refinement.

Never fill in numbers, deadlines, rules or metrics by plausibility. An inferred
requirement stays `proposed` until it is confirmed or sufficiently supported by
explicit evidence. `validated` means reconciled with the sources and verifiable;
`approved` requires a referenced human decision. Approval to develop belongs to
G1, even when the requirements are validated.

If new sources contradict an approved version, record the divergence, preserve
the history in git, and reopen the clarification; never replace decisions
silently. With no new information, hand the pending item back to the CTO and
respect the existing anti-loop.
