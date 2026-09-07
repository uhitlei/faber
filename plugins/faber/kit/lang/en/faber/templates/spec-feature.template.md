# Feature {{NN}} · {{Feature name}}

<!-- Template for the CANONICAL feature SPEC (RFC pattern, 17 sections) —
     destined for `@@FABER_SPECS_DIR@@/features/NN-name/SPEC.md`. Used by
     /faber-init (bootstrap) and by the doc-writer (spec-sync, G9).
     Proportional: include only the applicable sections; section 17 (CHANGELOG)
     is ALWAYS kept. Remove the comments as you fill it in; no {{...}} may
     survive. -->

- **Status:** {{Draft | Beta | Stable | Deprecated}}
- **Owners:** {{the responsible profiles or areas}}
- **Routes / entry points:** {{URLs, commands, endpoints}}
- **Key files:** {{the main paths in the code}}

## 1. Summary

{{An executive synthesis in 3–5 lines: what the feature does and for whom.}}

## 2. Problem

{{What pain it solves and why it exists.}}

## 3. Personas

| Persona | Context of use |
|---|---|
| {{profile}} | {{...}} |

## 4. Requirements

### 4.1 Functional
- **RF-01:** {{...}}

### 4.2 Non-functional
- **RNF-01:** {{performance, availability, accessibility, privacy and data protection…}}

## 5. Flows

```mermaid
flowchart LR
  A[{{start}}] --> B[{{step}}] --> C[{{end}}]
```

## 6. Architecture

{{Layers, dependencies, external integrations; a pointer to 00-ARCHITECTURE.}}

## 7. Data model

| Entity / table | Key fields | Authorization (RLS/ACL) |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

## 8. Contracts (APIs / RPCs / events)

| Operation | Input | Output | Errors |
|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} |

## 9. UI/UX

{{Routes, components, states (loading/empty/error/success), responsiveness, accessibility; a pointer to 02-DESIGN-SYSTEM.}}

## 10. Business rules

- **RN-1:** {{...}}

## 11. Edge cases

- {{the atypical scenario → how it is handled}}

## 12. Security

{{Specific risks and mitigations; the 03-SECURITY invariants this feature touches.}}

## 13. Performance

{{Limits, pagination, caches, costs.}}

## 14. Tests

| Type | Coverage | Where |
|---|---|---|
| unit | {{...}} | {{path}} |
| E2E | {{...}} | {{path}} |

## 15. Critical snippets

```{{language}}
{{the current critical excerpt, with path:line}}
```

## 16. Open questions

- {{a pending decision / technical debt — or "none"}}

## 17. CHANGELOG

<!-- Convention: `- <YYYY-MM-DD> · TASK-XXX — <what changed>`, newest at the top. -->
- {{YYYY-MM-DD}} · {{TASK-XXX | bootstrap}} — {{this spec was created}}
