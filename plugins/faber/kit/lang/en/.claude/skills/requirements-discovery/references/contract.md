# File contract — schema_version 1

Every path below is relative to the demand's or the bootstrap's folder. The four
input YAML files live in `requirements/`. IDs are stable, unique strings; use
SRC-NNN, EV-NNN, REQ-NNN, AC-NNN, Q-NNN, CF-NNN, ASM-NNN. Never renumber an
existing ID. Never reuse the ID of a deleted item.

## sources.yaml

`schema_version: 1`, `sources: []`. Each source carries:
`id`, `kind` (transcript/notes/document/decision/audio), `path`, `sha256`,
`required` (boolean), `coverage` (full/partial/pending/excluded),
`exclusion_reason` (mandatory when `required=false`).
The path is relative to the demand's folder, or absolute when it lives outside
the repository. When moving to another machine, relocate the paths and
regenerate the revision. Compute the hash with `python3 -c` and hashlib, or with
whatever SHA-256 tool is available.

Every source must be a readable file at validation time; a URL must come with a
local extract that is identified, dated by consultation, and carries the original
address. Do not import external files without authorisation to access them. Do
not send data to third-party services.

`full` means complete coverage of what is relevant to the explicitly defined
scope — never merely that the file was opened. Obligatory sources require `full`.
An obligatory audio source references `transcript_source: SRC-NNN` of a
transcript that is itself obligatory and `full`. Evidence points at the
transcript, never at audio bytes. Where only a note exists, do not present it as
a complete transcript.

## evidence.yaml

`schema_version: 1`, `evidence: []`. Each piece of evidence:
`id`, `source` (SRC), `locator`, `quote`, `kind` (statement/decision/inference).
Add speaker, timestamp and interpretation when they are known. The validator
checks referential integrity and the presence of a quotation and a location; the
faithfulness of the quotation and of the interpretation is the BA's
responsibility, and the review's.

## model.yaml

`schema_version: 1`, `revision` a positive integer. The business narratives live
in: `context`, `objectives`, `users`, `scope`, `out_of_scope`, `workflows`,
`business_rules`, `data_integrations`, `quality`, `risks`, `decisions`.
Reference EVs inside the narratives. Structure it proportionally to the project.

`requirements: []`, each item:

```yaml
id: REQ-001
type: functional
statement: The behaviour, stated with observable conditions.
status: proposed
evidence: [EV-001]
dependencies: []
acceptance_criteria:
  - id: AC-001
    statement: Initial condition, action, and observable result.
```

Types: business/stakeholder/functional/nonfunctional/transition.
Statuses: draft/proposed/validated/approved/rejected/deprecated. The last two
require a `reason` and are excluded from the active scope. Preserve their
historical origin. Active requirements need evidence and at least one acceptance
criterion. Dependencies point at active requirements; cycles must be resolved in
planning. For `approved` requirements, also record the human decision in the
evidence; the status alone does not prove authorisation. `approved` does not
approve G1.

`questions`, `conflicts`, `assumptions`: lists of objects with `id`, `statement`,
`severity` (blocker/high/medium/low), `status` and `resolution_evidence`. The
initial status is `open`; resolutions are `resolved` (questions and conflicts) or
`validated` (assumptions). A resolution requires an EV that exists. An open
blocker or high item blocks. Knowingly omitting a critical question is an
analysis failure, even when the score passes.

## assessment.yaml and readiness.json

`schema_version: 1`, `checks` carrying every key from the template. Each check:
`status`, `reason`, `evidence`. Statuses: missing/partial/verified/not-applicable.
Only `data` and `integrations` accept `not-applicable`, with evidence and a
reason. Not-applicable is a supported conclusion; not knowing is `missing`.
The script computes `readiness.json`: the score, the blockers, the revision and
the hash of the inputs. That report is a projection; never edit the score to make
the gate pass.

## delivery.json, approval and the source of truth

The `seal` command records the hashes of the inputs and of BRD, PRD,
`speckit/spec.md` and, on a demand, `spec.md` and `refinement.md`. Run it only
after the PO/QA review and the refinement. The seal is not an approval; G1 is
still the Owner's.

Before development, the gate recomputes the hashes and checks that G1 matches the
current seal. Changes to the sources, the requirements or the documents require a
review and a new seal; a change after approval requires renewing G1.

During bootstrap, the seal covers only the three projections. Record the seal's
hash alongside the PRD/BRD approval in `CONTEXT.md`. A demand born from the
backlog gets its own package with the relevant scope and sources, preserving the
IDs and the origin from the bootstrap, and goes through the normal G1.

`state.yaml` governs the workflow; `model.yaml` holds the requirements; the
demand's spec governs development; the global SPEC RFC is consolidated after the
merge. Updating a requirement requires updating its derivatives — never keep
competing versions.
