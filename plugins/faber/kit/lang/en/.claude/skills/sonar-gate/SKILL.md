---
name: sonar-gate
description: Optional module (FABER_SONAR=on). Publishes the demand branch's analysis to a Sonar mirror project (sonar-task.sh) and queries its Critical/High issues (sonar-gate.sh, through SONAR_TOKEN/SONAR_HOST_URL by name) to form the evidence for G5. Use during validation (devsecops/CTO). An unavailable API, a project with no analysis, or an analysis of a different commit becomes "not executed", never inferred. Critical/High is never exceptable.
---

# sonar-gate — Sonar's Critical/High as evidence

Source: `faber/ARCHITECTURE.md` §11, §18-G5, §21-R3; `07-ENV-AND-SECRETS` §4.
Deterministic mechanics: `faber/scripts/sonar-task.sh` +
`faber/scripts/sonar-gate.sh` (zero LLM). **Optional module:** it only applies
with `FABER_SONAR=on` and `FABER_SONAR_PROJECT_KEY` filled in
`faber/config/faber.env`; with it off → record "Sonar not configured — not
executed" (devsecops validates through the branch CI). Language: `FABER_LANG`.

## How to use it (two steps)

Running the scanner for a feature branch against the trunk's project
(`$FABER_SONAR_PROJECT_KEY`) **would overwrite the trunk** with unmerged code
(on servers with no multi-branch analysis). So the demand is measured in a
**mirror project** `<PROJECT_KEY>-TASK-XXX`, published **locally**: CI keeps
analysing only the trunk, on pushes to `@@FABER_TRUNK@@`/`@@FABER_MAIN@@`.

```bash
# 1. publish the branch's analysis to the mirror (generates coverage, scans and
#    WAITS for the server to process it; fails closed on any error)
faber/scripts/evidence.sh TASK-XXX sonar-analysis -- \
  faber/scripts/sonar-task.sh TASK-XXX

# 2. the verdict on the mirror, with the ratchet against the trunk
faber/scripts/evidence.sh TASK-XXX sonar -- \
  faber/scripts/sonar-gate.sh --project "${FABER_SONAR_PROJECT_KEY}-TASK-XXX" \
    --branch feature/TASK-XXX --baseline "$FABER_SONAR_PROJECT_KEY"

# 3. at G9, delete the mirror (cleanup)
faber/scripts/sonar-task.sh delete TASK-XXX
```

Step 1 is mandatory before step 2: the gate **refuses** (exit 3) an analysis
whose `revision` is not the local commit being evaluated — a verdict only holds
for the code that was analysed.

Direct use on the trunk: `sonar-gate.sh @@FABER_TRUNK@@` — it measures the
branch of the project `$FABER_SONAR_PROJECT_KEY` and requires the local ref
`refs/heads/@@FABER_TRUNK@@` to be the analysed commit.

## Parseable output

`PROJECT`, `BRANCH`, `MODE`, `ANALYSIS`, `REVISION`, `REVISION_CHECKED`,
`QUALITY_GATE`, `CRITICAL_LEGACY`, `HIGH_IMPACT`, `CRITICAL_HIGH`,
`BASELINE_*`, `NEW_VS_BASELINE`, `NEW=` (one per new issue), `RATCHET`,
`REASON`, `VERDICT` (`approved` | `rejected` | `not-executed`) plus the exit
code (`0` | `2` | `3`).

- `CRITICAL_LEGACY` = the **legacy** model (`BLOCKER,CRITICAL`);
  `HIGH_IMPACT` = the **impact** model (`BLOCKER,HIGH`);
  `CRITICAL_HIGH` = the **union** of the two (by issue key — not a sum, not a max).

## Interpretation (§18-G5)

- **approved** (exit 0) = `CRITICAL_HIGH=0`, or `NEW_VS_BASELINE=0` when the
  ratchet is on (inherited debt, all of it already in the trunk).
  `QUALITY_GATE` is **informational**: it fails on unreviewed hotspots and on an
  undefined New Code Period, which is not the rule being asked for — it does not
  block G5.
- **rejected** (exit 2) = there is a **new** Critical/High (the `NEW=` lines give
  `rule|file|hash`), or any Critical/High when there is no ratchet → **never
  exceptable** (§2, §19). Medium/Low → recorded; an exception only with a
  **documented CTO decision** in `decisions.md`.
- **not-executed** (exit 3) = a missing token or host, the API down, a project
  with no analysis, **an analysis of a different commit**, inconsistent data (the
  union smaller than the API's counts), a non-standard parameter → record an
  explicit "not executed"; **never** infer "passed" (§15). G5 stays pending on
  the Sonar axis.

## Rules

1. `SONAR_TOKEN` and `SONAR_HOST_URL` arrive **by name**, through the session's
   environment or the unversioned local file pointed at by `SONAR_ENV_FILE` (P2);
   never in a versioned file, never logged. Neither script ever prints either
   value.
2. The skill only **queries and publishes an analysis**; it does **not**
   configure the pipeline. Changing the Sonar job in `.github/workflows/`
   requires an approved DevSecOps task (H2).
3. Scope and coverage come from `sonar-project.properties` (`sonar-task.sh` only
   overrides the mirror's identity). The scanner's version is **pinned** in the
   script and appears in the evidence (`SCANNER=`).
4. The ratchet's baseline is the trunk (`$FABER_SONAR_PROJECT_KEY`), **read at
   the time** — never a number written by hand. It goes stale if the trunk's CI
   stops running.
