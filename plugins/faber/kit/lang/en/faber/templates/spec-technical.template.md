# Spec — {{TASK-XXX}}: {{title}}

<!-- Template: TECHNICAL (types: tech-debt, infra, security, database,
     docs — ARCHITECTURE §14). The PO is skipped: the CTO or the
     senior-developer specifies it. Proportionality (§11): fill it to the level
     of the real risk — simple documentation can have short sections; database
     and security work never can.
     Notes by type:
     · security — handle it discreetly: do NOT detail an exploit in a public
       issue; devsecops leads; db-guardian joins if data is involved.
     · database — db-guardian participates FROM the refinement onward;
       migration-safe is mandatory; migrations are immutable (H2).
     · infra — EVERY diff in .github/workflows/ requires an explicit review by
       @@FABER_OWNER_NAME@@ (H2/§19).
     · docs — straight to the doc-writer; the only gate is the CTO's review. -->

| Field | Value |
|---|---|
| Demand | {{TASK-XXX}} |
| Type | {{tech-debt \| infra \| security \| database \| docs}} |
| Author | {{cto \| senior-developer \| devsecops}} |
| Date | {{YYYY-MM-DD}} |

## 1. Motivation

<!-- Why this technical work needs to happen; the cost of NOT doing it. -->
{{...}}

## 2. Current state → desired state

- **Today:** {{...}}
- **After:** {{...}}

## 3. Technical plan

<!-- Objective steps; the likely files and modules (the final diff is compared
     against this — §15). For the database: the migrations foreseen, the RLS and
     GRANTs affected. -->
1. {{...}}

## 4. Validation criteria

<!-- Numbered AC-1… and verifiable by a command or a test. The basis of G5. -->
- **AC-1:** {{command / test → expected result}}

## 5. Impact and security

| Area | Affected? | Detail |
|---|---|---|
| Pipeline / workflows (@@FABER_OWNER_NAME@@'s review if `.github/workflows/`) | {{yes/no}} | {{...}} |
| Secrets (always by NAME, e.g. `API_TOKEN`) | {{yes/no}} | {{...}} |
| Database / RLS (db-guardian; `01-DATABASE`) | {{yes/no}} | {{...}} |
| Security surface (`03-SECURITY`) | {{yes/no}} | {{...}} |

## 6. Risks and rollback

- **Risks:** {{...}}
- **Rollback:** {{how to undo it safely; for the database, the migration's
  reverse plan (migration-safe)}}

## 7. Open questions

- {{... or "none"}}
