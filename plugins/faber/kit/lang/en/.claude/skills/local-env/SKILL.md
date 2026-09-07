---
name: local-env
description: Operates the factory's disposable LOCAL environment — bring it up, reset it, apply migrations and synthetic seeds, always through faber/scripts/local-env.sh (which delegates to the FABER_CMD_LOCAL_* commands in faber.env). Optional module (FABER_LOCAL_ENV=on). Use for the senior-developer's, QA's and db-guardian's local validations; a disposable environment with full autonomy (P4). It never touches a remote target.
---

# local-env — the disposable local environment

Source: `faber/ARCHITECTURE.md` §11, P4 (full autonomy locally — and only
locally). Mechanics: `faber/scripts/local-env.sh` (never loose commands) — each
subcommand delegates to the command configured in `faber/config/faber.env`.
Optional module: `FABER_LOCAL_ENV=on`.

## Commands

| Action | Command | Delegates to |
|---|---|---|
| Bring the stack up | `faber/scripts/local-env.sh up` | `FABER_CMD_LOCAL_UP` |
| State | `faber/scripts/local-env.sh status` | `FABER_CMD_LOCAL_STATUS` |
| Recreate the database + every migration | `faber/scripts/local-env.sh reset` | `FABER_CMD_LOCAL_RESET` |
| Synthetic seeds | `faber/scripts/local-env.sh seed` | `FABER_CMD_LOCAL_SEED` |
| Stop | `faber/scripts/local-env.sh stop` | `FABER_CMD_LOCAL_STOP` |
| Consolidated report | `faber/scripts/local-env.sh report` | (produced by the script: state + the last actions) |

A validation that feeds a gate or a handoff: run it through `evidence.sh` —
`faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`

## Rules

1. **Local only.** The script has a structural guard (it refuses any target that
   is not `127.0.0.1`/`localhost`) and, from outside, H1 denies production refs
   and environments (`FABER_REFS_DENY`) and asks for confirmation on remote ones
   (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`). A remote database of any
   environment: **never** through this skill (§19).
2. **Tool unavailable = not executed.** `FABER_LOCAL_ENV=off`, an empty
   `FABER_CMD_LOCAL_*`, or infra that is down → the script fails with
   instructions; the failure log (through `evidence.sh`) is the evidence of the
   unavailability. Record an explicit **"not executed"** in the handoff — never
   infer that the migration or the seed would have applied (§15).
3. **Infra first.** A local dependency that is stopped (e.g. Docker) → `up`
   fails with instructions; ask @@FABER_OWNER_NAME@@ to start it — do not try to
   install or start it yourself.
4. **Seeds:** `seed` runs the configured command and assumes the prerequisites
   documented in `@@FABER_SPECS_DIR@@/global/05-TESTING.md` (e.g. the test users
   exist). Without them the error is expected, not "flaky".
5. **Genuinely disposable:** if it breaks, reset it (`reset`); never fix local
   state by hand — the environment's value is that the migrations reproduce it.
