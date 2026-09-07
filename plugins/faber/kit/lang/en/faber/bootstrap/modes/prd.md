# Mode `prd` — only a PRD and/or a BRD exists

Signals: `PRD*.md`, `BRD*.md`, `prd.md`, `brd.md`, `docs/PRD*.md`,
`docs/BRD*.md`, `docs/requisitos*.md`. There is no code and no technical specs:
the factory **derives** the knowledge base from the product or business document
and marks everything that is a technical decision as `[PROPOSED]`.

When called from discovery or brainstorm, consume the BRD/PRD from
`faber/bootstrap/requirements/`, verify the seal and the approved hash in
CONTEXT, and go straight to step 2. Preserve the model's IDs; do not create a
second, divergent map. Importing a legacy PRD directly continues through the
steps below.

## Step 1 — Read and map (with evidence)

1. `prd-inventory` — list the input documents and the size of each.
2. Read the PRD/BRD by section. Extract into `faber/bootstrap/MAPA-PRD.md`:
   the vision · personas · goals and metrics · MVP scope and out of scope ·
   requirements (functional and non-functional, with IDs; where there are no
   IDs, assign `RF-NN` and cite the passage) · journeys · constraints · risks ·
   open questions.
3. Everything the PRD does **not** answer and that blocks a decision about
   architecture or scope → `PERGUNTAS.md` (one round).

## Step 2 — Proposed architecture (`00-ARCHITECTURE.md`, `[PROPOSED]`)

Based on the non-functional requirements, the constraints and the integrations
cited, propose a stack, the layers and the integrations — **as a table of
options × trade-offs**, with your recommendation marked. Nothing is decided
without the Owner; the document is born entirely `[PROPOSED]`. If the PRD
already pins a technology, record that as a constraint (a fact).

## Step 3 — Derived global specs

- `01-DATABASE.md`: entities inferred from the requirements (an ER, `[PROPOSED]`).
- `02-DESIGN-SYSTEM.md`: "to be defined" plus the accessibility principles from
  the PRD, or "not applicable".
- `03-SECURITY.md`: the sensitive data and the roles the PRD cites; the
  invariants as `[PROPOSED]`.
- `04-DEPLOYMENT.md`, `05-TESTING.md`, `06-CONVENTIONS.md`,
  `07-ENV-AND-SECRETS.md`: a skeleton with whatever the PRD imposes
  (environments, compliance) and the rest "to be defined in the first technical
  demand".
- `08-AGENT-PLAYBOOK.md`: the product's identity (facts from the PRD) plus the rules.

## Step 4 — Features (`features/NN-name/SPEC.md`)

Group the requirements by product capability (one feature = one coherent set of
requirements and journeys). For each one, use the 17-section template with: the
summary, the problem, the personas, the requirements (traceable to the PRD), the
flows (from the journeys), the business rules, the edge cases, the tests (the
PRD's acceptance criteria) and the open questions. Technical sections (data,
contracts, architecture) stay `[PROPOSED]` or "to be defined during refinement".

## Step 5 — Prioritised backlog

`BACKLOG.md`: one `feature` demand per MVP feature (ordered by dependencies →
value → risk), foundation `infra` and `database` demands (repository, CI,
database) before the features, and a `spike` for every architectural
`[PROPOSED]` that needs proof. Then follow the "Closing out" section of
`/faber-init`.
