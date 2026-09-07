# faber/bootstrap — initialising the factory in this repository

This folder is the **channel between the installer (`install.sh`, no LLM) and
the CTO (`/faber-init`, with an LLM)**.

| File | Who writes it | Contents |
|---|---|---|
| `CONTEXT.md` | `install.sh` (creates it) · `/faber-init` (completes it) | the detected mode, the signals, the input files, the interaction mode, `status: pending|done` |
| `modes/<mode>.md` | the kit | the playbook the CTO follows in each mode |
| `PERGUNTAS.md` | `/faber-init` | the doubts, grouped for the Owner (one round) |
| `BACKLOG.md` | `/faber-init` | candidate demands (title · type · priority · origin) |
| `evidence/` | `/faber-init`, through `evidence.sh faber/bootstrap …` | the commands executed during the bootstrap |

## The six modes

| Mode | Signal detected | What the CTO generates |
|---|---|---|
| `existing-repo` | source code + git history | global specs read out of the code, a feature inventory, the real config (lint/build/test, migrations, protected paths) |
| `spec-kit` | `.specify/`, `memory/constitution.md`, `specs/NNN-*/spec.md` | constitution → rules; each spec-kit feature → a SPEC RFC; plan.md → architecture; tasks.md → backlog |
| `prd` | `PRD*.md` / `BRD*.md` (root or `docs/`) | a `[PROPOSED]` architecture, feature specs derived from the functional and non-functional requirements, a prioritised backlog |
| `brainstorm` | `*brainstorm*.md` / `ideias.md` / `braindump.md` | PRD + BRD following `faber/templates/prd-brd-guide.md` → **a stop for approval** → continues as `prd` |
| `discovery` | chosen explicitly (`--mode discovery`) | the BA extracts evidence and requirements from transcripts and notes, produces the BRD/PRD, and resolves the gaps |
| `empty` | none of the above | asks the Owner which input they will bring (or a description) and falls into one of the modes above |

Precedence when more than one signal is present: `existing-repo` > `spec-kit` >
`prd` > `brainstorm` > `empty` (the richest input wins; the others are cited in
CONTEXT and used as secondary sources). Override: `install.sh --mode <x>` or
`/faber-init --mode <x>`.

## The foundation gate

The bootstrap ends in a `faber/bootstrap → <trunk>` pull request. **The Owner's
merge is the approval** of the knowledge base. After it, the first demand is
born with `/faber-task`.
