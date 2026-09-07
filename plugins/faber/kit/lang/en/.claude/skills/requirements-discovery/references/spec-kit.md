# Projection to Spec-Driven Development

The business output is `requirements/speckit/spec.md`. Preserve the REQ/AC IDs.
Include the model's revision, the goal, the users, the prioritised journeys, the
requirements, the acceptance scenarios, the exceptions, the success criteria and
the remaining doubts. Use the real template `.specify/templates/spec-template.md`
when it exists. With no Spec Kit installed, use those sections in Markdown and
record in the header: `SDD projection — not executed or validated by the Spec Kit
CLI`.

The CTO records in the document which template and which version or commit were
used, where that is verifiable. Do not invent a version and do not assume the
commands of the latest release. The CLI's availability is checked in the project
at the point it is used.

The PO converts that projection into the spec for the demand's type, preserving
the IDs. If the project uses Spec Kit operationally, the CTO and the
senior-developer produce the plan, research, data model, contracts and tasks
after the clarification round, using the installed templates. Do not assign
architectural choices to the BA, and do not declare those files to exist before
they are created. Technical execution still runs through the kit's refinement and
G1. Do not run Spec Kit's automated implementation before G1, and do not install
tools as a side effect of discovery.

An approved revision corresponds to exactly one set of requirements. When the
PRD, the BRD or the spec changes, reconcile the model, redo the affected
projections and revalidate the seal. At the G9 consolidation, the doc-writer
preserves the IDs and the origin in the SPEC RFC; the discovery package remains
as the demand's historical trail.
