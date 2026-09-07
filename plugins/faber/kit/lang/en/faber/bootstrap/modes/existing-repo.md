# Mode `existing-repo` — the factory joins a project that already exists

The goal: **describe faithfully what is there** (not propose), and fit the
factory to the repository's reality. Anything that comes from the code is a
fact; anything that is interpretation is marked `[PROPOSED]`.

## Step 1 — Reconnaissance (with evidence)

Record every command through
`faber/scripts/evidence.sh faber/bootstrap <slug> -- <cmd>`:

1. `tree` — the directory tree, three levels deep, ignoring `node_modules`,
   `.git`, `dist`, `build`, `vendor`, `.venv`, `target`.
2. `manifests` — the manifests found (`package.json`, `pyproject.toml`,
   `go.mod`, `Cargo.toml`, `pom.xml`, `composer.json`, `Gemfile`, `*.csproj`…):
   name, version, declared scripts and tasks, main dependencies.
3. `ci` — the workflows in `.github/workflows/` (or the equivalent): jobs,
   triggers, branches; where lint/build/test/e2e/deploy run.
4. `database` — the migrations folder (if any), the DBMS, the ORM; the migration
   count; whether RLS, policies and GRANTs are present.
5. `tests` — the unit and E2E test frameworks; the folders; the commands.
6. `history` — `git log --oneline -30`, the branches (`git branch -a`), the
   commit convention observed, the real default branch.
7. `env` — `.env.example` (variable NAMES only; never open `.env`/`.env.local`).

Use the `Explore` subagent (a broad search that returns conclusions only) to map
domains, routes and endpoints, entities and external integrations — never dump
the repository into the context (§20).

## Step 2 — The real configuration (`faber/config/faber.env`)

Propose to the Owner (and apply after they confirm):
- `FABER_CMD_LINT/BUILD/TEST` with the commands that **actually exist** in the
  manifests; `FABER_E2E=on` + `FABER_CMD_E2E` + the summary regexes if there is
  an E2E suite;
- `FABER_MIGRATIONS_DIR` + `FABER_MIGRATION_CHECKS` if there are migrations
  (Postgres + RLS → `grant ,enable row level security,create policy,set search_path`);
- `FABER_PROTECTED_PATHS` for generated files (generated clients and types,
  schema lockfiles, ORM snapshots);
- `FABER_SECRET_FILES` matching the `.env*` files observed;
- `FABER_REFS_DENY` / `FABER_REFS_CONFIRM` if you identify refs or IDs of remote
  environments in versioned configuration (cite them by the FILE's NAME, never
  copy secrets);
- `FABER_TRUNK` / `FABER_MAIN` matching the real branches.
- Labels: with `FABER_GH=on`, run `faber/scripts/board.sh bootstrap-labels`.

## Step 3 — Global specs (`@@FABER_SPECS_DIR@@/global/00–08`)

Starting from the templates in `faber/templates/specs-global/`, fill them with
what you read: the architecture (layers, components, integrations, implicit
ADRs), the data model (the real entities), the design system (the real tokens
and components, or "not applicable"), security (**section 3 — the untouchable
invariants**: identify the role functions, the sensitive fields, the critical
policies; if you cannot find them, leave the table as `[PROPOSED]` plus a
question), deployment and CI (from what the workflows say), testing (the real
commands), conventions (as observed in the code: naming, imports, error
handling), env (names only), and the playbook.

## Step 4 — Feature inventory (`@@FABER_SPECS_DIR@@/features/NN-name/SPEC.md`)

Group the code by domain or by user-visible functionality (routes, screens,
commands, endpoints). For each feature, fill the 17-section template with what
the code shows (sections with no evidence: "undocumented — `[PROPOSED]`", or an
Open question). Start with the 3–8 main features; list the rest in the README as
"to be documented" (backlog candidates, type `docs`).

## Step 5 — Backlog and closing

`faber/bootstrap/BACKLOG.md`: the visible debt (TODO/FIXME, missing tests,
features with no spec, incomplete CI) as candidate demands with a §14 type.
Then follow the "Closing out" section of `/faber-init`.
