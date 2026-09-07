---
description: Bootstraps the factory in this repository — reads the context install.sh detected (existing repo · spec-kit · PRD/BRD · brainstorm · empty), generates the specs and ARCHITECTURE, and readies the factory for its first demand
argument-hint: "[--mode existing-repo|spec-kit|prd|brainstorm|discovery|empty] [--interaction gates|step-by-step]"
---

# /faber-init

Arguments (optional): **$ARGUMENTS**

You are the CTO (CLAUDE.md). This command **initialises the factory** in this
repository. It runs **once** (or again, deliberately, with `--mode`), and
produces the knowledge base (`@@FABER_SPECS_DIR@@/`) that every demand starts
from. You do **not** implement product code here — only knowledge, configuration
and backlog.

## 0. Read the context (from disk, not from memory)

1. `faber/bootstrap/CONTEXT.md` — written by `install.sh`: the detected `modo`,
   the signals it found, the input files, `interacao`, `status`.
   If `status: done` and no `--mode` was passed → say the bootstrap has already
   been done, and stop.
2. `faber/config/faber.env` — the configuration (owner, trunk, commands,
   modules). If `FABER_INTERACTION` is empty, or `--interaction` was not given
   and CONTEXT says `interacao: perguntar`, **ask now**:
   *"Do you want to be involved only at the validation gates (G1/G6/G8 and
   critical doubts), or step by step?"* Write the answer into
   `FABER_INTERACTION` (editing `faber/config/faber.env` triggers an H2
   confirmation — the Owner's answer is that confirmation).
3. The mode's playbook: `faber/bootstrap/modes/<mode>.md`. **Follow it.**

## 1. Bootstrap rules (they hold for every mode)

- Work on the `faber/bootstrap` branch (created by `install.sh`). Small commits,
  `chore(faber): …`. Never on the trunk or production (H1).
- **Invent nothing.** A fact read from the code or a document → a statement. An
  inference → marked `[PROPOSED]`. A gap → a **question** in
  `faber/bootstrap/PERGUNTAS.md` (grouped; one round only, §20).
- Use the templates: `faber/templates/specs-global/*.md` (globals 00–08 plus the
  README), `faber/templates/spec-feature.template.md` (features, 17 sections),
  `faber/templates/prd.template.md` / `brd.template.md` plus the guide
  `faber/templates/prd-brd-guide.md` (brainstorm). No `{{...}}` survives into a
  delivered document.
- **Executed evidence** for everything verifiable (the detected lint/build/test
  commands, counts, the directory tree):
  `faber/scripts/evidence.sh faber/bootstrap <slug> -- <command>`
  (the `faber/bootstrap/evidence/` folder works exactly like a demand's).
- Adjust `faber/config/faber.env` to what you find (the real lint/build/test
  commands, the migrations directory, protected paths, E2E) — always listing the
  proposed changes for the Owner to confirm (H2 asks for confirmation).
- Update `faber/ARCHITECTURE.md §2` (the scenario) and `CLAUDE.md §6` (pointers)
  with whatever is specific to this project — without changing rules or numbering.
- Language: `FABER_LANG`.

## 2. Closing out (every mode)

1. `@@FABER_SPECS_DIR@@/README.md` with the real map (globals plus features).
2. An **initial backlog** in `faber/bootstrap/BACKLOG.md`: candidate demands
   (title, type §14, priority, origin in the source document). Do **not** create
   the issues yet — the Owner chooses where to start (`/faber-task`).
3. `faber/bootstrap/CONTEXT.md` → `status: done` plus a summary of what was generated.
4. Push the branch and open the `faber/bootstrap → @@FABER_TRUNK@@` PR with the
   summary (merging it is the **foundation gate**, and it is the Owner's). With
   `FABER_GH=off`: leave the branch ready and explain how to merge it.
5. Report in a single block: what was generated (with paths), the `[PROPOSED]`
   items that need confirmation, the open questions, and the next step
   (`/faber-task <the first demand from the backlog>`).

## 3. Interaction

- **`gates`**: run everything without stopping; doubts go to `PERGUNTAS.md` and
  are asked **once**, at the end (or at the start, if the input is too thin to
  begin). The only stopping point is the foundation PR — except in
  `brainstorm`/`discovery` mode, which have one extra mandatory stop: **the
  PRD/BRD approval before any specs are generated** (see the playbook).
- **`step-by-step`**: stop at the end of each playbook step and ask for an ok.
