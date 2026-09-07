---
name: e2e-runner
description: Runs the project's E2E suite (Playwright, Cypress or equivalent — always through the canonical command @@FABER_CMD_E2E@@) using the project's real patterns — selective execution by the affected spec, idempotent seeds, waiting on state — and captures the result as evidence. Use in QA's validation (state `validation`). Never runs a destructive seed or reset against a remote target — only against a confirmed LOCAL one.
---

# e2e-runner — running E2E with the project's patterns

Source: `@@FABER_SPECS_DIR@@/global/05-TESTING.md` (the suite, the runner, the
commands and the stability patterns) and the project's E2E test folder. Used by
QA (§7, §11) during validation. Module `FABER_E2E` in `faber/config/faber.env`
(G5 requires an executed E2E run when `FABER_E2E=on` and the demand has UI
impact). Language: `FABER_LANG`.

## The real suite and commands (do not invent flags)

- **Read the project's real E2E suite** in `05-TESTING.md` and in the test
  folder: which specs exist, what each one covers, which login/seed/navigation
  helpers already exist. Never invent flags, projects or paths.
- **Canonical command:** `@@FABER_CMD_E2E@@` (`FABER_CMD_E2E`). Execution that
  is **selective by the affected spec** = the canonical command followed by the
  spec's path, in the form the project's runner accepts (e.g.
  `@@FABER_CMD_E2E@@ <e2e-folder>/<feature>.spec.ts`).
- **Server:** if the runner's configuration brings the application server up on
  its own, do not start another by hand; if it does not, follow the procedure in
  `05-TESTING.md`. The URL and port are the project's — do not memorise them.
- **The runner's report** (HTML or equivalent), if there is one, complements the
  evidence; the gate's evidence is the log with its exit code.

## Evidence (it feeds G5 — §18)

A green E2E run is a G5 criterion. Always run it **through `evidence.sh`**,
calling the canonical command **DIRECTLY** — no `bash -c`, no pipe. The gate
recognises the command that ran by `FABER_E2E_CMD_REGEX` and the result by
`FABER_E2E_SUMMARY_REGEX` / `FABER_E2E_FAIL_REGEX`; a pipe hides both the exit
code and the summary:

```bash
faber/scripts/evidence.sh TASK-XXX e2e -- @@FABER_CMD_E2E@@ <e2e-folder>/<feature>.spec.ts
```

The runner or the local infra being unavailable = an explicit **"not executed"**,
never an inferred "passed" (§15).

## Stability patterns (05-TESTING — mandatory)

1. **Wait for state, not for time:** assertions that wait for the element or the
   state (`toBeVisible`, `waitFor…`, `expect.poll` or the runner's equivalents) —
   never a fixed sleep.
2. **Accessible selectors** (by role or label — `getByRole`/`getByLabel` or
   equivalent) beat CSS selectors (they survive refactors).
3. **Wait for the response** of critical mutations (e.g. `waitForResponse` on the
   mutation's endpoint) before asserting.
4. **Idempotence:** each test creates its own data, or uses seeds reset before
   the run; reuse the project's helpers, do not reimplement login.
5. A new spec: follow the naming and folder convention in `05-TESTING.md`, use
   the project's helpers, seed idempotently before `beforeAll`, and keep debug
   logs behind a debug environment variable.

## Safety rule — the E2E target

**A destructive seed or reset only against a confirmed LOCAL target; a remote
target → stop and escalate to the CTO.**

- **NEVER** run a destructive seed or reset against a remote target through this
  skill — a shared environment could be wiped. Need to seed or reset with
  writes? Use the **disposable local environment** (skill `local-env`, P4).
- Running the E2E suite (reads plus UI flows) is acceptable; if a test requires
  writing data, confirm the target is local **first** — when in doubt, **stop**.
  Production refs and environments (`FABER_REFS_DENY`) and remotes that require
  confirmation (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`): never through here
  (§19, H1).
