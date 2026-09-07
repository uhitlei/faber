# Configuration — `faber/config/faber.env` and the optional modules

There is exactly **one** configuration file, `faber/config/faber.env`. Scripts
read it at runtime through `faber/scripts/lib/config.sh`, and hooks through
`.claude/hooks/faber_config.py`.

Agent and command prose is a different matter: `install.sh` renders the
`@@FABER_*@@` placeholders **once**, at install time. If you change the owner
or the branches later, edit the `.env` **and** grep `.claude/` and `CLAUDE.md`
for the old values.

Without this file, nothing runs. `faber_require_install` fails loudly rather
than falling back to defaults, because a factory operating on someone else's
configuration would approve gates it has no business approving.

> **Português:** [pt-BR/PERSONALIZACAO.md](pt-BR/PERSONALIZACAO.md)

## Core keys

| Key | Effect |
|---|---|
| `FABER_OWNER` / `FABER_OWNER_NAME` | who approves G1/G6/G8 (`gate-set --por <slug>`); also lands in `_schema.owner` of `state.template.yaml` |
| `FABER_TRUNK` / `FABER_MAIN` | the branches H1 protects; the base of every task; the target of every PR |
| `FABER_INTERACTION` | `gates` (stops only at G1/G6/G8 and critical doubts) or `step-by-step` |
| `FABER_WORKTREES` | `on` puts each task in `.claude/worktrees/TASK-XXX` |
| `FABER_GH` / `FABER_GH_REPO` | GitHub issues as task IDs; `off` uses a local counter |
| `FABER_BOARD` / `FABER_GH_PROJECT_TITLE` | Projects v2 sync (the Status field's options are the 9 columns of §6.1) |
| `FABER_SPECS_DIR` | the canonical specs folder |
| `FABER_CMD_LINT` / `_BUILD` / `_TEST` | G3 demands executed evidence from all three |
| `FABER_LANG` | the language the factory *writes* in — specs, issues, handoffs, gate messages. Default `pt-BR` |
| `FABER_SECRET_FILES` | H2 denies editing these; H1 asks for confirmation on shell writes to them |
| `FABER_PROTECTED_PATHS` | paths or prefixes no agent may edit (generated files, snapshots) |
| `FABER_REFS_DENY` | any command containing one of these tokens is **denied** (e.g. your production project ref) |
| `FABER_REFS_CONFIRM` | a command containing the token **asks for confirmation** (e.g. a staging ref) |
| `FABER_CMDS_DENY` / `FABER_CMDS_CONFIRM` | regexes (separated by ` ;; `) for the dangerous commands of your stack |

## Optional modules

Each is off until you turn it on.

| Module | Keys | What it enables |
|---|---|---|
| **E2E** | `FABER_E2E=on`, `FABER_CMD_E2E`, `FABER_E2E_CMD_REGEX`, `_SUMMARY_REGEX`, `_FAIL_REGEX` | G5 requires an executed E2E run whenever `impacto_ui: true` — five conditions checked in the log |
| **Database** | `FABER_MIGRATIONS_DIR`, `FABER_MIGRATION_CHECKS` | H2 (migration immutability), H3 (required statements), the `migration-safe` skill, the db-guardian agent |
| **Local environment** | `FABER_LOCAL_ENV=on`, `FABER_CMD_LOCAL_UP/STATUS/RESET/SEED/STOP` | the `local-env` skill (`local-env.sh`, with a guard that refuses non-local targets) |
| **Static analysis** | `FABER_SONAR=on`, `FABER_SONAR_PROJECT_KEY` (plus `SONAR_TOKEN`/`SONAR_HOST_URL` in the environment or in `SONAR_ENV_FILE`) | the `sonar-gate` skill: `sonar-task.sh` publishes the mirror, `sonar-gate.sh` returns the verdict |
| **Design system** | `FABER_DESIGN_SYSTEM=on` | the `design-system-check` skill (hardcoded-colour grep, Tailwind-oriented) |
| **Dashboard** | `FABER_DASHBOARD=on` plus `install.sh --dashboard on` | `faber/dashboard/dashboard.sh` — a local Kanban with telemetry, bound to 127.0.0.1 |

## Adapting to another stack

1. Start from a preset in `profiles/` with `--profile`.
2. Point `FABER_CMD_*` at your real commands. G3 only accepts evidence of
   lint, build and test **actually executed**.
3. If your E2E runner is not Playwright, adjust all three regexes: the one that
   recognises the command, the one that recognises a green summary, and the one
   that recognises a failure.
4. With no database, leave `FABER_MIGRATIONS_DIR` empty — H3, `migration-safe`
   and db-guardian go inert.
5. List in `FABER_REFS_DENY` every identifier that shows up in commands
   aimed at production: project IDs, hostnames. This is the single most
   valuable rule in H1.
6. Run `bash .claude/hooks/test-h1-h2.sh` after changing any rule. It uses its
   own sandbox config, so add your own cases if you want the real tokens
   covered — without pasting secrets into the repository.

## What not to change

- The `TASK-` prefix, the 15 states, the 9 gates, the 10 task types, and the
  `§N` numbering of `faber/ARCHITECTURE.md`. Scripts, hooks, agents and commands
  all depend on them.
- The two invariants: *a handoff without evidence is invalid*, and *a human
  gate can only be approved by the owner*.
