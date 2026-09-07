# Requirements discovery

Turning meeting transcripts, notes and documents into evidence, requirements,
a BRD/PRD and a business specification the factory can act on.

> **Português:** [pt-BR/REQUISITOS-DISCOVERY.md](pt-BR/REQUISITOS-DISCOVERY.md)
> — the original specification, with the full file-by-file inventory.

> **Status:** implemented and covered by 21 technical test cases against
> synthetic fixtures. Validation against a real meeting is a later step and has
> not been done. Nothing here claims 95% accuracy of extraction; the score
> measures declared completeness with verified structure.

## Scope

Raw audio can be inventoried but is never interpreted as if it were
transcribed. **Transcription is an external input** — Faber ships no audio
service, no credentials and no upload.

The CTO still coordinates. The business analyst extracts and clarifies; the
product owner writes the spec; QA judges testability; CTO and developer refine;
the owner approves G1. No extra states and no extra human gates are introduced
per task.

## Entry points

| Command | When |
|---|---|
| `/faber-discovery TASK-XXX <sources>` | resumes an existing task in its worktree |
| `/faber-task` | routes to the business analyst when the input contains discovery material |
| `/faber-init --mode discovery` | product foundation, using `faber/bootstrap/requirements/` |

## The flow

1. Inventory the sources, their limits, and a content revision by SHA-256.
2. Extract evidence with its location, distinguishing a **statement** from an
   **inference** from a **decision**.
3. Record context, goals, users, scope, flows, rules and requirements.
4. Produce a preliminary BRD/PRD and record the gaps. What is absent is never
   invented.
5. Compute completeness; the priority questions go back through the CTO to the
   owner.
6. Fold the answers in as new sources and recompute.
7. PO and QA produce and review the spec and acceptance criteria; technical
   refinement proceeds as usual.
8. Seal the reviewed artifacts, check G1, and wait for the human approval that
   already existed.

With no new information, the loop stops: it will not repeat questions or
re-invoke agents indefinitely. One meeting can cover several features — during
bootstrap that becomes a candidate backlog; inside an existing task it is
limited to that task's scope, and the rest is recorded as out of scope.

## Artifacts

Each task (or the bootstrap) gets a `requirements/` folder with four inputs —
`sources.yaml`, `evidence.yaml`, `model.yaml`, `assessment.yaml` — and produces
`BRD.md`, `PRD.md`, `speckit/spec.md`, `readiness.json` and `delivery.json`.
Sources stay where they are, at the registered paths; nothing is copied by
force. The detailed schema lives in the skill's reference file rather than
being duplicated here.

## The readiness score

Weights: problem and goals 15 · users 10 · scope 15 · flows and rules 15 ·
requirements 15 · acceptance 15 · data and integrations 5 · quality 5 ·
traceability 5.

Every dimension has explicit checks in the rubric, in code and in the template.
Each check scores 0 (missing), 0.5 (partial) or 1 (verified), and a `verified`
check needs a justification and references that exist. **There is no free field
for an agent to type a final grade into.**

Data and integrations may be `not-applicable` with a justification and
evidence; that dimension then leaves the denominator and the remaining weights
are normalised. Absence of information never justifies non-applicability.

The gate requires a real value **≥ 95** — 94.99 does not round up.

These block regardless of the score: an obligatory source not covered · a file
missing or altered · a broken reference · an active requirement with no
evidence or acceptance · a requirement still in draft or proposed · an open
critical question or conflict · an unvalidated critical assumption. Rejected
and deprecated requirements are preserved but do not count as active scope.

## Source of truth

- `state.yaml` — states, gates, workflow.
- `model.yaml` — the requirements register and their origins.
- BRD/PRD and Spec Kit — projections carrying the same IDs.
- The task's spec governs the approved implementation; the global SPEC RFC is
  consolidated at G9.

These responsibilities do not overlap. Editing a derived document requires
reconciling the model, regenerating or reviewing the projections, and sealing
again. The seal hashes the inputs, the sources and the output files. A change
after G1 invalidates its binding and requires a new G1 before development
resumes. A hash proves the bytes were reviewed — not that the meaning is right.

## Spec Kit

The business analyst prepares **only** `speckit/spec.md` — the what and the
why. The plan, the contracts and the tasks belong to technical refinement.
Where Spec Kit is installed, its real templates are used and its version
recorded. Faber does not install Spec Kit and does not pretend to support its
CLI: without an installation, the output is a Markdown SDD projection, not
something validated by the Spec Kit tooling.

## Compatibility

Older tasks without discovery keep their previous gates. The check activates on
the presence of `requirements/`, on `discovery.required: true`, or on a G1
binding from before; setting the flag to false does not deactivate a package
that already exists and was approved.

Do not apply discovery indiscriminately to bugs, incidents or technical tasks
that carry no business discovery. The discovery *mode* is explicit for the same
reason — so that no stray `.txt` gets classified as a meeting.

Updating a factory that is already installed means applying the reviewed diff
and preserving customisations. `--force` is not a migration strategy.
