---
name: spec-task
description: Selects and fills the spec template proportional to the type of a factory demand (TASK-XXX). Use when creating, reviewing or completing a demand's spec.md — never write a spec from memory without a template.
---

# spec-task — proportional templates, by type

Source: `faber/ARCHITECTURE.md` §11 (the skill), §14 (types), §18 (the DoR for
G1). Templates live in `faber/templates/`. Language: `FABER_LANG`.

## Selecting the template (type → file)

| Type (slug from `_schema.types`) | Template |
|---|---|
| feature | `spec-feature.template.md` |
| design | `spec-feature.template.md` |
| bug | `spec-bug.template.md` |
| incident | `spec-incident.template.md` |
| tech-debt | `spec-technical.template.md` |
| infra | `spec-technical.template.md` |
| security | `spec-technical.template.md` |
| database | `spec-technical.template.md` |
| docs | `spec-technical.template.md` |
| spike | `spec-spike.template.md` |

The nuances per type are commented inside each template (e.g. `security` with no
exploit in a public issue; `database` with the db-guardian involved from the
refinement onward; `design` with the UX-impact section at its centre).

## How to fill it in

1. Copy the template to `faber/tasks/TASK-XXX/spec.md`.
2. Replace every `{{...}}`; **remove the `<!-- -->` comments** as you go (they
   are instructions, not content).
3. No `{{...}}` may survive — a leftover placeholder means an incomplete spec
   (it blocks the DoR and G1).
4. Acceptance criteria numbered (`AC-1`, `AC-2`…) and testable: they are the
   basis of QA's requirement × test matrix and of the G5 validation.
5. Proportionality (§11): the spec must sit **at the level of the type's
   template** — do not bloat a simple bug with feature sections, and do not
   thin out a large feature. A section that does not apply gets an explicit
   "none" or "not applicable", and never keeps its placeholder.
6. An open critical doubt → state `clarification` and a question to
   @@FABER_OWNER_NAME@@; stopping always beats advancing with a doubt (§6.2).
   The PO never invents a business rule.
7. The spec is alive: changes during refinement or development are edited in
   `spec.md` itself, with a record in the demand's `history` / `decisions.md`.
