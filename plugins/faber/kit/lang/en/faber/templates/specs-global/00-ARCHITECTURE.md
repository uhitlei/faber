# 00 · Architecture

<!-- Generated and filled in by /faber-init from the detected context (an
     existing repo: read from the code; spec-kit/PRD/brainstorm: proposed and
     marked [PROPOSED] until the Owner confirms). No {{...}} may survive. -->

> **Stack:** {{languages · frameworks · database · infra · CI/CD}}
> **User personas:** {{e.g. user, manager, admin — or "n/a" for libraries and CLIs}}

## 1. Context view (C4 level 1)

```mermaid
flowchart LR
  U[{{User}}]:::user --> App[{{System}}]
  App --> Ext[{{External integrations}}]:::ext
  classDef user fill:#0ea5e9,stroke:#0369a1,color:#fff
  classDef ext fill:#475569,stroke:#1e293b,color:#fff
```

## 2. Layers and code organisation

```text
{{an annotated directory tree — what lives in each folder}}
```

## 3. Components and responsibilities

| Component | Responsibility | Depends on |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

## 4. Main flows

{{2–4 end-to-end flows (as sequences) — a Mermaid `sequenceDiagram` where it helps.}}

## 5. Architectural decisions (summarised ADRs)

| # | Decision | Reason | Consequences |
|---|---|---|---|
| ADR-1 | {{...}} | {{...}} | {{...}} |

## 6. Limits and constraints

- {{platform limits, quotas, latency, payload size…}}

## 7. Glossary

- **{{term}}:** {{definition}}
