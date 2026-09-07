# 08 · Agent playbook (for local AIs)

> **Required** reading at the start of any session. It condenses what an agent
> needs to know in order to produce safe changes in this codebase.

## 1. The project's identity

- **Name:** @@FABER_PROJECT@@
- **Domain:** {{...}}
- **Stack:** {{...}}
- **Language of the code and UI:** {{...}}
- **User personas:** {{...}}

## 2. Recommended reading order

1. `00-ARCHITECTURE.md` · 2. `01-DATABASE.md` · 3. `03-SECURITY.md` ·
4. `06-CONVENTIONS.md` · 5. `02-DESIGN-SYSTEM.md` · 6. the SPEC of the feature
you are about to touch.
Then (CI and environments): `04-DEPLOYMENT.md` and `07-ENV-AND-SECRETS.md`.

## 3. Inviolable rules

1. Never edit: {{generated and protected files — FABER_PROTECTED_PATHS}}.
2. Never change an already-applied migration; always create a new one.
3. {{Authorization/RLS enabled on every new entity, plus explicit GRANTs}}.
4. The untouchable invariants in `03-SECURITY.md §3` only with
   @@FABER_OWNER_NAME@@'s review.
5. Zero secrets in code, logs or chat — always by name.
6. {{project-specific rules…}}

## 4. When you need to touch code

| Intended change | Read first | Watch out for |
|---|---|---|
| {{a new screen or endpoint}} | {{00, 02/03, the spec}} | {{...}} |
| {{a new entity}} | {{01, 03}} | {{migration-safe}} |
| {{an external integration}} | {{07}} | {{the secret, by name}} |

## 5. Everyday commands

```bash
@@FABER_CMD_LINT@@
@@FABER_CMD_BUILD@@
@@FABER_CMD_TEST@@
@@FABER_CMD_E2E@@
```

## 6. How to find out what exists

| Question | Where to look |
|---|---|
| Which entities exist? | `01-DATABASE.md` / `{{FABER_MIGRATIONS_DIR}}` |
| Which routes and endpoints? | {{path}} |
| How does auth work? | {{path}} + `03-SECURITY.md` |

## 7. The factory

Demands run as `TASK-<issue#>` under `faber/tasks/`, through gates G1–G9
(`faber/ARCHITECTURE.md`). Commands: `/faber-task`, `/faber-bug`,
`/faber-spike`, `/faber-incident`, `/faber-status`, `/faber-resume`,
`/faber-approve`, `/faber-develop`, `/faber-validate`, `/faber-pr`.
