# Handoff — {{TASK-XXX}} · {{agent}} → cto

<!-- Template for the handoff contract (ARCHITECTURE §17). Every subagent ends
     by writing faber/tasks/TASK-XXX/handoffs/NN-<agent>-para-cto.md
     (NN = the highest existing numeric prefix + 1). Hook H5 validates the YAML
     block below: the mandatory fields, plus every piece of evidence existing
     and non-empty. Paths are RELATIVE to the demand's folder (product files:
     relative to the repository root). Never paste file content — paths only. -->

```yaml
task: {{TASK-XXX}}
from_agent: {{product-owner | senior-developer | code-reviewer | qa | devsecops | db-guardian | product-designer | doc-writer}}
to_agent: cto
suggested_state: {{a state from §6.2 — a suggestion; the CTO decides}}
inputs_consumed: [{{spec.md, refinement.md, ...}}]
outputs_produced: [{{spec.md | review.md | src/... | ...}}]
evidence: [{{evidence/NN-slug.log, https://... (a CI or Sonar URL)}}]
open_issues: []            # doubts and deviations → they force a CTO decision (or an escalation to the Owner)
new_risks: []
suggested_next_action: "{{...}}"
```

<!-- Golden rule: a handoff with no evidence referenced is an invalid handoff
     (gate-check rejects the transition). Your final message in the chat is only
     a pointer to this file plus the suggested_state, in one line. -->
