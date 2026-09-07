---
name: migration-safe
description: Creates safe migrations in the factory's pattern for relational databases — a template carrying the statements hook H3 requires (FABER_MIGRATION_CHECKS; e.g. GRANT + RLS + policy + trigger + search_path), a mandatory destructiveness analysis, and a documented reverse rollback. Use WHENEVER a demand changes the database (type database, or a detected data impact). Applied migrations are immutable.
---

# migration-safe — safe, immutable migrations

Source: `faber/ARCHITECTURE.md` §11, §13-H2/H3, §19; specs
`@@FABER_SPECS_DIR@@/global/01-DATABASE.md` (the model and access rules — read
by section) and `03-SECURITY.md` (the *Untouchable invariants* section).
Template: `faber/templates/migration.template.sql` (Postgres with RLS as the
example — adapt it to your project's database). Migrations live in
`@@FABER_MIGRATIONS_DIR@@/` (`FABER_MIGRATIONS_DIR`; empty = the module is off).

## Procedure

1. **A new timestamp, always:** `date +%Y%m%d%H%M%S` →
   `@@FABER_MIGRATIONS_DIR@@/<timestamp>_<slug>.sql`. A timestamp that already
   exists in the history = H2 denies it (immutability); never edit an applied
   migration — a fix is a **new, corrective migration**.
2. **Start from the template** and fill every `{{...}}`; a section that does not
   apply (e.g. no trigger) is removed **and recorded in the header's analysis**.
3. **Destructiveness analysis (mandatory, in the header):**
   - Additive (`create table/index/policy`, `add column nullable`): safe.
   - Destructive (`drop`, `alter column type`, `rename`, `delete`, `truncate`,
     `add column not null` with no default): you must detail the data affected,
     the compatibility with the code in production (deployment is not atomic with
     CI) and the mitigation plan. When in doubt → `clarification`.
4. **Reverse rollback:** a commented block at the end of the file with the
   commands that undo the change — never executed there; it becomes a corrective
   migration if needed.
5. **The project's invariants** (hook H3 validates the presence of the statements
   listed in `FABER_MIGRATION_CHECKS`; §13-H3). In the Postgres/RLS example:
   - `search_path` pinned in every function (`set search_path = public`);
   - row-level access control (RLS) enabled on every new table, plus policies
     per persona;
   - minimum GRANTs (never `grant all`; the anonymous role only when the spec
     requires it);
   - **the security invariants declared in `03-SECURITY.md` (the *Untouchable
     invariants* section) do not change without an explicit review by
     @@FABER_OWNER_NAME@@** (§19).
6. **Test locally before the handoff** (skill `local-env`):
   `faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`
   (it applies every migration from scratch — the evidence of a green reset is
   the objective criterion that the migration applies; a local environment that
   is unavailable = an explicit "not executed").
7. **Applying to a remote belongs to CI** (the pipeline, on merge). Remote
   environments that require confirmation (`FABER_REFS_CONFIRM` /
   `FABER_CMDS_CONFIRM`): only with @@FABER_OWNER_NAME@@'s explicit
   confirmation, per execution; production refs and environments
   (`FABER_REFS_DENY`) — never by an agent (H1).
