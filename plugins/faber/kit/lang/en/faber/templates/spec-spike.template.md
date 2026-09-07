# Spec — {{TASK-XXX}}: spike — {{the short question}}

<!-- Template: SPIKE / investigation (ARCHITECTURE §14). NO production
     implementation — the output is a recorded TECHNICAL DECISION (a mini-ADR).
     It may spawn child demands. The timebox is set at intake and respected: if
     it runs out, stop and record what is known. -->

| Field | Value |
|---|---|
| Demand | {{TASK-XXX}} |
| Type | spike |
| Timebox | {{e.g. 4h \| 1 day}} |
| Date | {{YYYY-MM-DD}} |

## 1. The question to answer

<!-- ONE objective question. More than one question means more than one spike. -->
{{...}}

## 2. Context

<!-- Why the doubt exists; what is already known; the relevant specs and code. -->
{{...}}

## 3. Investigation

<!-- What was tried, measured or read, with real evidence in evidence/
     (disposable prototypes are allowed; production code is not). -->
- {{experiment → result → evidence/NN-*.log}}

## 4. Mini-ADR (the spike's output)

- **Context:** {{the problem in 2–3 sentences}}
- **Options considered:**
  | Option | Pros | Cons |
  |---|---|---|
  | {{A}} | {{...}} | {{...}} |
  | {{B}} | {{...}} | {{...}} |
- **Decision:** {{the option chosen, and why}}
- **Consequences:** {{what gets easier or harder from here}}
- **Author / date:** {{cto \| senior-developer}} · {{YYYY-MM-DD}}

<!-- Copy this mini-ADR into the demand's decisions.md; the doc-writer carries
     the relevant part into specs/ at G9 (§15). -->

## 5. Proposed child demands

- {{TASK-YYY: … or "none"}}
