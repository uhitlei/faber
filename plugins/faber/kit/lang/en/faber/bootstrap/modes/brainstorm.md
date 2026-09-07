# Mode `brainstorm` — only a brainstorm file exists

## The current flow

Run the `discovery.md` playbook, using the brainstorm as the textual source.
Preserve any existing `B-NN` IDs as aliases in the evidence. The package and the
BRD/PRD live in `faber/bootstrap/requirements/`; do not create competing copies
under `docs`. Human approval is still mandatory. The steps below describe the
legacy flow, kept so that older projects can still be read — do not run both.

## The historical 1.0.0 flow

Signals: `*brainstorm*.md`, `ideias.md`, `ideas.md`, `braindump.md`,
`notas*.md`, at the root or under `docs/`. This is the rawest input: the factory
first **produces the PRD and the BRD**, following the Owner's guide, and only
continues as mode `prd` once they are approved.

## Step 1 — Read the guide and the brainstorm (with evidence)

1. `brainstorm-inventory` — list the input files and the guide in use.
2. Read **all of `faber/templates/prd-brd-guide.md`** — it is the Owner's guide
   (or the kit's default, if they did not bring their own). **It governs** the
   structure, the sections, the completeness criteria and the tone of the
   PRD/BRD. The `prd.template.md` / `brd.template.md` files are only the default
   skeleton: if the guide defines a different structure, use the guide's.
3. Read the whole brainstorm. Build `faber/bootstrap/MAPA-BRAINSTORM.md`: every
   idea or sentence numbered (`B-NN`) with a classification (problem · audience ·
   goal · requirement · constraint · risk · doubt · out of scope).

## Step 2 — PRD and BRD (drafts)

- `docs/PRD.md` and `docs/BRD.md` (create `docs/` if it does not exist),
  following the guide. **Traceability is mandatory:** every requirement cites the
  `B-NN` it came from. Whatever the brainstorm does not say becomes an **open
  question** (in the PRD and in `PERGUNTAS.md`), never an assumption — invented
  metrics, deadlines and costs are forbidden ("to be defined" is the honest
  answer).
- Check the guide's **completeness criteria** before delivering.
- Evidence: `faber/scripts/evidence.sh faber/bootstrap prd-complete --
  bash -c "! grep -qF '{{' docs/PRD.md docs/BRD.md && echo ok"`.

## Step 3 — MANDATORY STOP: the PRD/BRD approval

In **either** interaction mode, stop here. Commit and push the
`faber/bootstrap` branch, and make a single request to the Owner: read
`docs/PRD.md` and `docs/BRD.md`, answer the questions in `PERGUNTAS.md`, and say
**"PRD approved"** (or ask for changes). Record the approval in
`faber/bootstrap/CONTEXT.md` (`prd_aprovado_em`, `por`). Without that approval
there are no specs — a wrong PRD would contaminate everything that follows.

## Step 4 — Continue as `prd`

With the PRD/BRD approved, run Steps 2–5 of
`faber/bootstrap/modes/prd.md` (the `[PROPOSED]` architecture, the global specs,
the features, the backlog) and then the "Closing out" section of `/faber-init`.
