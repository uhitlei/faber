# 04 · Deployment & CI/CD

## 1. Environments

| Environment | Branch / trigger | URL / ref | Who promotes |
|---|---|---|---|
| local | — | 127.0.0.1 | the agent (autonomous) |
| {{staging}} | `@@FABER_TRUNK@@` | {{...}} | CI |
| production | `@@FABER_MAIN@@` | {{...}} | @@FABER_OWNER_NAME@@ / CI |

## 2. Branching strategy

`feature/TASK-XXX → PR → @@FABER_TRUNK@@ → @@FABER_MAIN@@` (promotion). Merging
a PR is always human (G8).

## 3. Pipeline (CI)

| Job | Trigger | What it validates |
|---|---|---|
| {{build-and-test}} | {{push/PR}} | {{lint, build, tests}} |

Workflows live in `.github/workflows/` — editing them requires an approved
DevSecOps task (H2 / `workflow-unlock.sh`).

## 4. Deployment

- {{how the artifact is built and published; any manual steps}}

## 5. Migrations at deploy time

- {{who applies them, when, and what happens if one fails}}

## 6. Rollback

- {{the procedure per layer: application, database, infra}}

## 7. Observability

- {{logs, metrics, alerts, health checks}}

## 8. Secrets per environment

- Names (never values): `{{VAR_1}}`, `{{VAR_2}}` — see 07-ENV-AND-SECRETS.

## 9. Costs and limits

- {{quotas, plans, execution limits}}

## 10. Pre-merge checklist (the baseline DoD)

- [ ] `@@FABER_CMD_LINT@@` · `@@FABER_CMD_BUILD@@` · `@@FABER_CMD_TEST@@` green (evidence on the demand)
- [ ] E2E executed when `ui_impact: true`
- [ ] The migration reviewed (destructiveness + rollback), where there is one
- [ ] New environment variables declared in the affected environments
- [ ] The feature's CHANGELOG updated
