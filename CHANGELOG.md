# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Bypass mode for the hooks** (`FABER_BYPASS`, default `on`). A hook's `ask`
  opens a dialog even when the session runs in `bypassPermissions`, so an
  unattended session stalled on every confirmation. H1/H2 now read
  `permission_mode`: in bypass, `FABER_REFS_CONFIRM`/`FABER_CMDS_CONFIRM` go
  through, while shell writes to protected paths, workflow edits without a
  `workflow_unlock` and edits to the factory's guardrails become a deny. Every
  deny is unchanged, and recording G1/G6/G8 as `approved` still asks — the
  session stops only at the human gates. `FABER_BYPASS=off` restores the old
  behaviour. 36 new hook cases (82 in total).

### Fixed
- H1 asks before `workflow-unlock.sh` grants an unlock (revoking stays free).
  Nothing stopped the agent from authorising its own workflow edits with
  `--by <owner>`; in bypass mode that would have left workflows unguarded.
- H1 no longer treats `2>/dev/null`, `>&2` or `2>&1` as a shell write, so reading
  a protected path with stderr silenced stops asking for confirmation.

## [2.0.0] — Faber

### Added
- Distribution as a **Claude Code plugin and marketplace**: `/plugin marketplace add uhitlei/faber`
  then `/plugin install faber@faber`, exposing `/faber:install`, `/faber:update`
  and `/faber:doctor`.
- `bootstrap.sh` — one-line install straight from GitHub, with the terminal
  reattached so the installer stays interactive when piped into bash.
- `INSTALL.md` / `INSTALL.pt-BR.md` — a procedure written to be executed
  literally, by a person or by an agent.
- **Strict install guard**: `faber_require_install` in `lib/config.sh` plus an
  inline guard in the four scripts that do not source it. No operational script
  runs in a tree without `faber/config/faber.env` — previously they fell back to
  defaults silently and could approve gates against the wrong configuration.
  `FABER_SKIP_INSTALL_CHECK=1` releases it for the sandboxed test suites.
- Continuous integration running all 170 test cases plus `claude plugin validate`.

### Changed
- Renamed from *Fábrica de Software com Agentes* to **Faber**. The whole public
  contract is now English: the `faber/` folder, script and template filenames,
  and the six bootstrap modes (`existing-repo`, `empty`).
- Configuration keys renamed: `FABER_PROJETO` → `FABER_PROJECT`,
  `FABER_OWNER_NOME` → `FABER_OWNER_NAME`, `FABER_INTERACAO` → `FABER_INTERACTION`,
  `FABER_ARQUIVOS_SECRETS` → `FABER_SECRET_FILES`,
  `FABER_PATHS_PROTEGIDOS` → `FABER_PROTECTED_PATHS`,
  `FABER_REFS_PROIBIDOS` → `FABER_REFS_DENY`,
  `FABER_REFS_CONFIRMAR` → `FABER_REFS_CONFIRM`,
  `FABER_CMDS_PROIBIDOS` → `FABER_CMDS_DENY`,
  `FABER_CMDS_CONFIRMAR` → `FABER_CMDS_CONFIRM`,
  `FABER_GH_PROJECT_TITULO` → `FABER_GH_PROJECT_TITLE`,
  `FABER_E2E_SUMARIO_REGEX` → `FABER_E2E_SUMMARY_REGEX`,
  `FABER_E2E_FALHA_REGEX` → `FABER_E2E_FAIL_REGEX`, and
  `FABER_IDIOMA` → `FABER_LANG`.
- Installer flags renamed: `--mode`, `--interaction`, `--project`,
  `--owner-name`, `--profile`, `--prd-guide`, `--force`, `--yes`. `--sim` stays
  as a hidden alias for `--yes`. The interaction value `passo-a-passo` is now
  `step-by-step`, and the `generico` profile is `generic`.
- The twelve commands are now prefixed: `/faber-init`, `/faber-task`,
  `/faber-develop`, `/faber-approve`, `/faber-validate`, `/faber-resume`,
  `/faber-status`, `/faber-bug`, `/faber-spike`, `/faber-incident`,
  `/faber-pr`, `/faber-discovery`.
- Task IDs are `TASK-<n>`; task folders live in `faber/tasks/`.
- `FABRICA_IDIOMA` is now `FABER_LANG` (default `pt-BR`) and drives the language
  of what the factory writes, independently of the interface language.

### Fixed
- `install.sh` no longer runs a stray command substitution: an unquoted heredoc
  contained backticks around the word `valores`, so every install printed
  `line 290: valores: command not found`. Present since 1.0.0.
- Nine scripts pointed at `../demandas` after the task folder moved; they now
  resolve `../tasks`.

### Bilingual

- The payload is split into `kit/shared` (code plus the machine contract, one
  copy) and `kit/lang/{en,pt-BR}` (the prose). `install.sh --lang` chooses the
  pack and wires `FABER_LANG`; the installer asks when neither is given.
- Both packs are fully translated: `CLAUDE.md`, the 12 commands, the 9 agents,
  the 10 skills, the 6 bootstrap playbooks, the 20 templates and
  `faber/ARCHITECTURE.md`.
- Artifact filenames are part of the shared contract and are English in both
  packs: `refinement.md`, `tasks.md`, `db-analysis.md`, `validation-g6.md`,
  `.counter`.

### Not done yet

- Comments and log messages inside `kit/shared` (the scripts, the hooks and the
  optional dashboard) are still Portuguese, as are the dashboard's internal
  identifiers. None of it is the public contract, and none of it reaches the
  user's repository as prose an agent reads.
- The `discovery` mode has never been validated against a real meeting. Its 21
  test cases run on synthetic fixtures.

## [1.1.0] — requirements discovery

### Added
- `business-analyst` agent, `requirements-discovery` and
  `requirements-readiness` skills, and the `/faber-discovery` command.
- `discovery` bootstrap mode for new products built from transcripts and notes.
- Readiness ≥ 95 with zero blockers is required before PO, QA and refinement,
  and G1 is bound to the requirements review.

## [1.0.0]

- First portable release of the factory: 9 agents, 12 commands, 10 skills,
  7 hooks, 9 gates, and the context-detecting installer.
