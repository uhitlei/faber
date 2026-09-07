# Mode `spec-kit` — a new repository with specifications in the Spec Kit format

Signals: `.specify/` (memory/constitution.md, templates/, scripts/) and/or
`memory/constitution.md` at the root, plus `specs/NNN-name/spec.md` (with
`plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`,
`tasks.md`). Spec Kit is an **input**, not a competitor: the factory consumes
what it produced and governs the cycle from here on.

## Step 1 — Read what is there (with evidence)

1. `speckit-inventory` — list the Spec Kit files found
   (`find . -path ./node_modules -prune -o \( -name constitution.md -o -path '*/specs/*/spec.md' -o -path '*/specs/*/plan.md' -o -path '*/specs/*/tasks.md' \) -print`).
2. Read all of `constitution.md`; read each `spec.md`/`plan.md`/`tasks.md`
   **by section**, on demand.

## Step 2 — The constitution → the factory's rules

- Principles from the constitution that are **inviolable rules** → `CLAUDE.md §2`
  (the "project rules" block, below the factory's own rules — without altering
  the factory's) and `@@FABER_SPECS_DIR@@/global/06-CONVENTIONS.md`.
- Quality and testing principles → `05-TESTING.md` (and, if they demand blocking
  coverage, record it in `ARCHITECTURE §18` as a formal exception to be decided).
- Security principles → `03-SECURITY.md §3` (the untouchable invariants).

## Step 3 — plan.md / research.md / data-model.md → the global specs

- The stack and structure declared in `plan.md` → `00-ARCHITECTURE.md` (mark
  `[PROPOSED]` whatever does not exist in code yet).
- `data-model.md` → `01-DATABASE.md`; `contracts/` → section 8 of the feature SPECs.
- Decisions in `research.md` → ADRs summarised in `00-ARCHITECTURE.md §5`.

## Step 4 — Each `specs/NNN-name/spec.md` → `@@FABER_SPECS_DIR@@/features/NN-name/SPEC.md`

Convert to the RFC pattern (17 sections) through
`faber/templates/spec-feature.template.md`: user stories → personas plus flows;
functional requirements → RF-NN (keeping the original IDs in parentheses for
traceability); acceptance scenarios → section 14 (tests) and the business rules;
edge cases → section 11; Spec Kit's `[NEEDS CLARIFICATION]` → **Open questions**
(section 16) and `PERGUNTAS.md`. Do not delete the Spec Kit files — they remain
as the historical origin; the canonical truth becomes the SPEC RFC (CHANGELOG:
"converted from Spec Kit").

## Step 5 — tasks.md → the backlog

Each `tasks.md` becomes candidate demands in `faber/bootstrap/BACKLOG.md` (group
small tasks into one `feature` demand; infra and CI → `infra`; database →
`database`). Preserve the declared order and dependencies. Do not create issues
yet.

## Step 6 — Configuration and closing

If `plan.md` declares the stack, propose a coherent `FABER_CMD_*`,
`FABER_MIGRATIONS_DIR` and `FABER_E2E` (for the Owner to confirm — there is no
code yet to prove them). If Spec Kit's `specs/` folder collides with
`FABER_SPECS_DIR`, `install.sh` has already chosen another canonical folder (see
`CONTEXT.md`) — do not mix them. Then follow the "Closing out" section of
`/faber-init`.

## Projections produced by discovery

A `requirements/speckit/spec.md` is a projection of the model, not a finished
technical package. Preserve its IDs and its origin when converting. The plan,
contracts and tasks, when used, belong to technical refinement. The active demand
governs implementation through G1; the SPEC RFC receives the consolidation. Do
not maintain two specs edited independently, and do not assume the CLI is
installed.
