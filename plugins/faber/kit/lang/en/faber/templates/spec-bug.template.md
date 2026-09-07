# Spec — {{TASK-XXX}}: {{the bug's title}}

<!-- Template: BUG (ARCHITECTURE §14). A reduced spec ON PURPOSE (§11):
     reproduction + root cause + fix + regression test. Do not pad it.
     GOLDEN RULE: with no reproduction recorded with evidence, the spec does
     not advance (§14 — "reproduction is mandatory before the spec"). -->

| Field | Value |
|---|---|
| Demand | {{TASK-XXX}} |
| Type | bug |
| Severity | {{critical \| high \| medium \| low}} |
| Date | {{YYYY-MM-DD}} |

## 1. Reproduction (mandatory)

<!-- The exact steps executed, with REAL evidence recorded in evidence/
     (a log, a screenshot). Narrated evidence is invalid (§15). -->
- Environment: {{local/staging + browser/device}}
- Persona / user: {{the product persona}}
- Steps:
  1. {{...}}
- **Reproduction evidence:** {{evidence/NN-repro.log}}

## 2. Expected behaviour × observed behaviour

- **Expected:** {{...}}
- **Observed:** {{...}}

## 3. Root cause

<!-- The technical diagnosis: file, function, query. "I do not know yet" →
     investigate before closing the spec, or convert it into a spike (§14). -->
{{...}}

## 4. Proposed fix

<!-- The minimum scope of the fix. A behaviour change beyond the fix is a
     different demand. -->
{{...}}

## 5. Regression test

<!-- Mandatory (§14): a test that FAILS before the fix and PASSES after it.
     Name the test file and both runs, as evidence. -->
- Test: {{path to the unit test | path to the E2E test}}
- Evidence "fails before": {{evidence/NN-test-before.log}}
- Evidence "passes after": {{evidence/NN-test-after.log}}

## 6. Risks and collateral impact

- {{... or "none identified"}}

## 7. Open questions

- {{... or "none"}}
