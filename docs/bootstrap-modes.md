# Bootstrap modes

`install.sh` detects the mode; `/faber-init` runs the matching playbook from
`faber/bootstrap/modes/<mode>.md`. All six end in a `faber/bootstrap → <trunk>`
pull request, and merging it is **the foundation gate** — yours to approve.

> **Português:** [pt-BR/MODOS-DE-BOOTSTRAP.md](pt-BR/MODOS-DE-BOOTSTRAP.md)

## Precedence

`existing-repo` > `spec-kit` > `prd` > `brainstorm` > `empty`. The richest
input wins; the others are recorded in `CONTEXT.md` as secondary sources.
Override with `install.sh --mode X` or `/faber-init --mode X`.

## `existing-repo`

**Signal:** at least 10 source files, plus either a manifest or 3+ commits.

**Produces:** global specs 00–08 read out of the code (facts, not guesses) · a
feature inventory (`features/NN-name/SPEC.md`, 17 sections) · proposed
adjustments to `faber.env` (the real lint/build/test commands, migrations
folder, protected paths, environment refs, E2E) · a backlog of the debt it can
see.

**Stops at:** one grouped round of questions, then the foundation PR.

## `spec-kit`

**Signal:** `.specify/`, `memory/constitution.md`, or `specs/NNN-*/spec.md`.

**Produces:** the constitution becomes project rules in `CLAUDE.md` (its own
section) and `06-CONVENTIONS` · `plan.md`, `research.md` and `data-model.md`
become globals · each `spec.md` becomes a SPEC RFC traceable to the original
IDs · every `[NEEDS CLARIFICATION]` becomes an open question · `tasks.md`
becomes the backlog. The original Spec Kit files stay as historical source.

**Watch out:** if `specs/` already belongs to Spec Kit, Faber's canonical specs
folder defaults to `docs/specs` so the two do not mix.

## `prd`

**Signal:** `PRD*.md`, `BRD*.md`, `prd.md`, `brd.md`, `requisitos*.md` or
`requirements*.md`, at the root or under `docs/`.

**Produces:** `MAPA-PRD.md` (extraction with `RF-NN`/`RNF-NN` identifiers) ·
a `[PROPOSED]` architecture with an options × trade-offs table · derived global
specs · features grouped by capability and traced back to the PRD · a
prioritised backlog (foundation → MVP → spikes for the risky proposals).

**Stops at:** one grouped round of questions, then the foundation PR.

## `brainstorm`

**Signal:** `*brainstorm*.md`, `ideias.md`, `ideas.md`, `braindump.md`,
`notas.md` or `notes.md`, at the root or under `docs/`.

**Produces:** `MAPA-BRAINSTORM.md` (ideas numbered `B-NN`) → **`docs/PRD.md` +
`docs/BRD.md` following `faber/templates/prd-brd-guide.md`** — your own guide
if you passed `--prd-guide`, otherwise the kit's default — with `RF ↔ B-NN`
traceability and open questions in place of assumptions.

**Stops at (mandatory, in either interaction mode):** your approval of the
PRD/BRD. Then it continues as `prd`.

## `discovery`

**Signal:** none. This mode is chosen explicitly, with `--mode discovery`.

For a new product built from meeting transcripts, notes and documents. The
`business-analyst` extracts evidence and requirements into `requirements/`
before the product owner sees anything, produces the BRD/PRD, and resolves the
gaps. Readiness must reach 95 with zero blockers before PO, QA and refinement
run, and G1 is bound to the requirements review. Audio transcription is not
included — bring text.

See [requirements-discovery.md](requirements-discovery.md).

## `empty`

**Signal:** none of the above.

Asks — with closed options — which input you will bring. Or it writes down
verbatim what you dictate in the chat into `docs/brainstorm.md` and continues
as `brainstorm`.

## Rules every mode obeys

- Nothing is invented. A fact read from the repository becomes a statement; an
  inference is marked `[PROPOSED]`; a gap becomes a question.
- Everything verifiable is verified by running it
  (`evidence.sh faber/bootstrap …`).
- No `{{...}}` placeholder survives into a delivered document.
- In `gates` mode: one round of questions and the PR. In `step-by-step`: an
  explicit ok at the end of every step.
