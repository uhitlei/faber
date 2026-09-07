# PRD/BRD guide — how the factory turns a brainstorm into a PRD and a BRD

> **This file is a SLOT.** Replace it with YOUR PRD/BRD guide (the `.md` your
> organisation uses): the `/faber-init` command in `brainstorm` mode **follows
> to the letter whatever is here** — structure, sections, completeness criteria
> and tone. The installer accepts `--prd-guide <file.md>` to drop your guide
> into this place. What follows is the DEFAULT guide, used only when you do not
> supply your own.

## 1. Principles

1. **Nothing invented:** every requirement must trace back to a line of the
   brainstorm or to an explicit decision by the Owner. Whatever is not in the
   brainstorm becomes an **open question**, never an assumption.
2. **Problem before solution:** the PRD describes the problem, the audience and
   the expected outcome; the technical solution belongs to the specs (the next
   phase).
3. **Measurable:** goals with a metric and a target; requirements with a
   verifiable acceptance criterion.
4. **Proportional:** a short brainstorm produces a short PRD. Sections with no
   substance get an explicit "not applicable", never filler text.
5. **A human gate:** the generated PRD/BRD is a DRAFT until the Owner approves
   it (the bootstrap's `/faber-approve`). Only then are the specs born.

## 2. The PRD's structure (`docs/PRD.md`)

1. **Vision** — one sentence: for whom, what, why.
2. **Problem and opportunity** — the pains observed (cite the brainstorm), the
   context, the cost of not doing it.
3. **Audience and personas** — who uses it, in what context, how often.
4. **Goals and success metrics** — a table of goal × metric × target × deadline.
5. **MVP scope** — what goes into the first delivery (a numbered list).
6. **Out of scope** — what explicitly does NOT go in now (and why).
7. **Functional requirements** — `RF-NN`, one per line, each with a testable
   acceptance criterion.
8. **Non-functional requirements** — `RNF-NN`: performance, security and
   privacy, accessibility, availability, compliance.
9. **Main journeys** — 2–5 end-to-end flows in numbered steps.
10. **Dependencies, risks and assumptions** — a table with the mitigation and
    the owner.
11. **High-level roadmap** — phases and milestones (no invented dates: "to be
    defined" when there are none).
12. **Open questions** — everything the brainstorm does not answer; each with
    who decides.
13. **Traceability** — a table of `RF/RNF × the brainstorm excerpt` (a short
    quotation).

## 3. The BRD's structure (`docs/BRD.md`)

1. **Executive summary** — the business case in five lines.
2. **Business context** — the market or organisation, the motivation, the
   alternatives considered.
3. **Stakeholders** — role, interest, influence, the decision they make.
4. **Business goals and KPIs** — aligned with the PRD's goals.
5. **Expected benefits** — quantitative and qualitative.
6. **Costs and estimated effort** — an order of magnitude (or "to be estimated
   after the specs").
7. **Constraints** — deadline, budget, regulatory, imposed technology.
8. **Business risks** — likelihood × impact × mitigation.
9. **Project success criteria** — how we will know it worked.
10. **Approval** — who approves, and what changes once it is approved.

## 4. Completeness criteria (the CTO checks these before asking for approval)

- [ ] Every section present (or a justified "not applicable").
- [ ] Every RF/RNF with an acceptance criterion and a traceability line.
- [ ] No invented metric, deadline or cost — absence is declared.
- [ ] Open questions listed and addressed to whoever decides.
- [ ] Language: the one set by `FABER_LANG`.
