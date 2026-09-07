---
name: spec-sync
description: Consolidates a finished demand's spec into @@FABER_SPECS_DIR@@/ in the RFC pattern (17 sections) — updates the feature's SPEC.md, the CHANGELOG and the .mmd diagrams, without duplicating content. Use in the doc-writer, at Done (G9). A merge, never a copy.
---

# spec-sync — canonical consolidation into @@FABER_SPECS_DIR@@/

Source: `faber/ARCHITECTURE.md` §11, §15 (a merge, **never** duplication); the
canonical structure `@@FABER_SPECS_DIR@@/features/NN-name/SPEC.md`
(`FABER_SPECS_DIR`). Language: `FABER_LANG`.

## Where to consolidate

| The demand's impact | Canonical destination |
|---|---|
| An existing feature | `@@FABER_SPECS_DIR@@/features/NN-name/SPEC.md` |
| Database / security / deployment… | the matching global spec in `@@FABER_SPECS_DIR@@/global/` |
| A flow or model that changed | the `.mmd` source in `@@FABER_SPECS_DIR@@/assets/diagrams/` (plus the `.png` render) |

## The RFC pattern (canonical order — proportional)

Use this order; **include only the applicable sections** (the project's most
complete feature might use the first 16; a bug or a technical demand uses far
fewer). **Section 17 (CHANGELOG) is always created or updated** when a demand
touches the feature.

1. Summary · 2. Personas · 3. Functional requirements · 4. Non-functional
requirements · 5. Flows · 6. Data model · 7. RPCs · 8. UI/UX · 9. Detailed
business rules · 10. Edge cases · 11. Security · 12. Performance · 13. Tests ·
14. Critical snippets · 15. Open questions · 16. References · **17. CHANGELOG**.

## How to consolidate (a merge, never duplication — §15)

1. Read the demand's `spec.md`, `decisions.md` and evidence, plus the feature's
   current SPEC.md.
2. **Update the affected sections** of the canonical SPEC.md — rewrite the part
   that changed, do **not** append a new parallel block. A business rule that
   became a new truth **replaces** the old one.
3. **CHANGELOG (section 17):** add an entry
   `- <date> · TASK-XXX — <what changed>` (newest at the top). It is the
   feature's traceable history.
4. **Diagrams:** if a flow or model changed, update the matching `.mmd` (the
   source); do **not** edit the `.png` by hand (it is a render). A new diagram →
   `assets/diagrams/NN-name.mmd`.
5. **Glossary / Open questions:** promote new terms; **close** the open questions
   the demand resolved.
6. Consolidate **only what is recorded** (decisions, evidence) — a doubt goes to
   Open questions, and is never filled in from memory.
