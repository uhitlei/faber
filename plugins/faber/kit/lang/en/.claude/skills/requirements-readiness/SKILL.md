---
name: requirements-readiness
description: Assess how complete a discovery package is, list the blockers, and seal the artifacts' revision before G1. Use with a demand's or the bootstrap's requirements/ folder; it does not replace a semantic review or a human approval.
---

# Requirements readiness

Use `faber/templates/requirements/assessment.template.yaml` as the rubric. The
checks and their weights are defined in `faber/scripts/lib/requirements.py`.
`verified` needs a justification and evidence; `partial` is worth half;
`missing` is worth zero. N/A is only allowed on data/integrations, with a reason
and evidence, and it removes that weight from the denominator. **The script
computes the score, never the agent.**

```bash
python3 faber/scripts/requirements-gate.py report faber/tasks/TASK-XXX --write
```

Swap the folder for `faber/bootstrap` during bootstrap. Exit 1 means gaps or an
invalid structure; read every error. Record one run with the `evidence` skill,
preserving a non-zero exit when the package still fails. Never reclassify a gap
to raise the score without new information.

The gate: a real score ≥ 95, the obligatory sources covered, current hashes,
active requirements validated or approved, references and acceptance criteria
present, and zero open blocker/high items. The program verifies **structure** —
it does not prove that a quotation is faithful, that a rule is correct, or that
an acceptance criterion is good. The PO and QA review those.

After the PO, QA, the spec and the refinement are done:

```bash
python3 faber/scripts/requirements-gate.py seal faber/tasks/TASK-XXX
python3 faber/scripts/requirements-gate.py delivery faber/tasks/TASK-XXX
```

`seal` writes `requirements/delivery.json`; `delivery` recomputes it and returns
the seal's hash if it is valid. Never use `seal` to hide a divergence: reconcile
the inputs and the outputs first. `gate-check.sh` verifies the seal at
`ready-for-dev` and on the moves out of `in-development`; `gate-set.sh` binds G1
to the hash when the Owner approves it. During bootstrap, the hash is recorded
alongside the human approval of the PRD/BRD.

When reporting, say "completeness X/100 with N blockers". Do not say "an X%
chance of being correct". None of these commands approves G1, and none of them
modifies a human gate.
