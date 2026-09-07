---
name: evidence
description: Produces real, executed evidence (evidence/NN-*.log) for the factory's gates and handoffs — every validation command runs through faber/scripts/evidence.sh. Use whenever a command's result has to become evidence; narrated evidence is invalid.
---

# evidence — executed, never narrated

Source: `faber/ARCHITECTURE.md` §11 (the skill), §15 (anti "false claim of
execution"), §17 (a handoff with no evidence is invalid), R6 (2 MB).

## The golden rule

Evidence is the **file written by a real execution** — `gate-check.sh` inspects
the file, not your narrative. Output pasted from memory, an edited log, or one
created by hand, is invalid evidence.

## How to use it

```
faber/scripts/evidence.sh <TASK-XXX> <slug> -- <command> [args...]
```

- Pipelines and redirections: `... -- bash -c "@@FABER_CMD_LINT@@ 2>&1 | tail -50"`
  (the exception: the E2E command `@@FABER_CMD_E2E@@` is called **directly**,
  with no pipe — see the `e2e-runner` skill)
- The command's exit code is **propagated** — chain on it:
  `evidence.sh TASK-XXX test-run -- @@FABER_CMD_TEST@@ && <next step>`
- `NN` increments by itself; the log lands in `evidence/NN-<slug>.log` with a
  header (command, start, end, duration, exit code) plus the full output.

## Conventional slugs

`lint`, `build`, `test-run`, `e2e`, `repro`, `test-before`, `test-after`,
`sonar`, `db-validation` — descriptive and short. Gate G3 looks for
`*lint*`/`*build*`/`*test*` inside `evidence/` (gate-check).

## Supplementary rules

1. **Tool unavailable** (Sonar down, network out): run the command anyway
   through `evidence.sh` — the failure log IS the evidence of the
   unavailability. Declare "not executed" in the handoff; **never** infer a
   result (CLAUDE.md §4).
2. **A log over 2 MB** (R6): the script warns you — do not commit it; leave the
   file out of the commit and **reference the path** (or the report's URL) in
   the handoff.
3. One command, one piece of evidence. Distinct validations (lint, build, test)
   produce distinct logs — never group them into one.
4. Handoffs reference the logs' paths under `evidence:` (§17); a handoff with no
   evidence referenced is rejected by gate-check.
