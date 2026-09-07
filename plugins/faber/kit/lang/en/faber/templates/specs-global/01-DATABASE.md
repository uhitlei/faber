# 01 · Database / data model

<!-- If the project has no persistence of its own, write "not applicable" in
     section 1 and remove the rest. Source: the migrations in
     FABER_MIGRATIONS_DIR (an existing repo) or the PRD/specs (a proposal). -->

## 1. Overview

- **DBMS / service:** {{Postgres, MySQL, SQLite, Mongo, DynamoDB…}}
- **Migrations:** `{{FABER_MIGRATIONS_DIR}}` — immutable once applied (H2); a fix is a new migration.
- **Authorization in data:** {{row-level (RLS) | ACL in the application | n/a}}

## 2. ER diagram

```mermaid
erDiagram
  {{ENTITY_A}} ||--o{ {{ENTITY_B}} : "{{relationship}}"
```

## 3. Entities

| Entity / table | Purpose | Key fields | Indexes | Authorization |
|---|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} | {{...}} |

## 4. Functions / procedures / RPCs

| Name | Input → Output | Security (invoker/definer) | Notes |
|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} |

## 5. Integrity rules and triggers

- {{...}}

## 6. Conventions

- Names: {{snake_case…}}; timestamps: {{timestamptz}}; ids: {{uuid}}.
- Every new entity: {{RLS/ACL enabled + minimum GRANTs + an index on the foreign keys}}.

## 7. Test data / seeds

- {{how the seeds are generated; idempotence; where they live}}
