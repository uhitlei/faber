# 06 · Code conventions

## 1. Language and configuration

- {{the language version; strict mode; the linter/formatter and its config}}

## 2. Naming

| Item | Convention |
|---|---|
| Files | {{...}} |
| Functions / methods | {{...}} |
| Types / classes | {{...}} |
| Constants | {{...}} |
| Database (tables, columns) | {{...}} |
| Events / telemetry | {{...}} |

## 3. Module structure

- {{where each kind of code lives; import rules; size limits}}

## 4. Mandatory patterns

- {{error handling; logging; input validation; data access}}

## 5. Forbidden patterns

- {{`any` without justification; secrets in code; hardcoded colours; …}}

## 6. Commits and branches

- Commits: `type(scope): description`
  (`feat|fix|chore|docs|test|refactor|perf|style|ci|build|revert`), referencing
  `TASK-XXX` when on a demand's branch (hook H4).
- Branches: `feature/TASK-XXX` (demands) · `docs/TASK-XXX-specs` (the
  post-merge consolidation).

## 7. Code review — what the reviewer checks

- Adherence to the spec (AC by AC) · security (03) · conventions (this document)
  · minimum code (the ladder of laziness: repo → standard library → installed
  dependency → new code) · tests · edge cases · performance · regression.
