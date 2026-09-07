# Spec — {{TASK-XXX}}: incident — {{title}}

<!-- Template: INCIDENT (ARCHITECTURE §14). A fast flow with
     @@FABER_OWNER_NAME@@ synchronous: containment → diagnosis → fix →
     post-mortem. THE POST-MORTEM BECOMES THE SPEC.
     NO fixing straight in PRODUCTION (H1): the fix follows the normal pipeline. -->

| Field | Value |
|---|---|
| Demand | {{TASK-XXX}} |
| Type | incident |
| Severity | {{SEV1 total \| SEV2 degraded \| SEV3 localised}} |
| Impact start / end | {{YYYY-MM-DDTHH:MM}} → {{...}} |

## 1. Timeline

<!-- Record it in real time, with timestamps. Facts, not assumptions. -->
| Time | Event |
|---|---|
| {{HH:MM}} | {{detection: how the problem was noticed}} |
| {{HH:MM}} | {{...}} |

## 2. Containment applied

<!-- The immediate action that stopped the bleeding (and its evidence).
     Containment is NOT the real fix. -->
{{...}}

## 3. Diagnosis (root cause)

<!-- What broke and why; evidence in evidence/. -->
{{...}}

## 4. The real fix

<!-- The scope of the permanent fix — it follows the pipeline (feature branch →
     PR → @@FABER_TRUNK@@ → @@FABER_MAIN@@). Compressed gates, with
     @@FABER_OWNER_NAME@@ synchronous (§14). -->
{{...}}

## 5. Post-mortem

<!-- Blameless; focused on process. This block is the heart of the spec. -->
- **What failed:** {{...}}
- **What worked:** {{...}}
- **Where we got lucky:** {{...}}
- **Preventive actions:** <!-- each becomes a child demand unless it is trivial -->
  - {{...}}

## 6. Child demands created

- {{TASK-YYY: … or "none"}}
