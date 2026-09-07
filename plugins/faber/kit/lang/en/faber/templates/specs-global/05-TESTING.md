# 05 · Testing

## 1. Strategy (the pyramid)

| Level | Tool | Command | Where |
|---|---|---|---|
| unit | {{...}} | `@@FABER_CMD_TEST@@` | {{path}} |
| integration | {{...}} | {{...}} | {{path}} |
| E2E | {{Playwright / Cypress / n/a}} | `@@FABER_CMD_E2E@@` | {{path}} |

## 2. How to run them

```bash
@@FABER_CMD_LINT@@
@@FABER_CMD_BUILD@@
@@FABER_CMD_TEST@@
@@FABER_CMD_E2E@@
```

## 3. The E2E suite

- {{the list of specs and what each one covers}}
- Server / environment: {{how it comes up; the target is ALWAYS local for seeds and resets}}
- Evidence for G5: `faber/scripts/evidence.sh TASK-XXX e2e -- @@FABER_CMD_E2E@@`
  (the command called directly, with no pipe).

## 4. Stability patterns

1. Wait for **state**, not for time.
2. Accessible selectors (role/label) beat CSS selectors.
3. Idempotence: each test creates its own data, or uses seeds that were reset.
4. No `console.log` outside debug mode.

## 5. Test data

- {{seeds, factories, test users — how to create and reset them locally}}

## 6. Coverage

- Current targets: {{informational | blocking, per directory}}
- Coverage exceptions only with a documented CTO decision (§18).

## 7. How to write a new test

- {{naming and folder conventions, the helpers to reuse}}
