# Mode `discovery` — transcripts, notes and client documents

Chosen explicitly: `/faber-init --mode discovery`, or `--mode discovery` at
install time. The CTO identifies the paths the user supplied and only confirms
the scope it cannot infer from them. Installing the kit never requires a real
meeting.

1. Use `faber/bootstrap/requirements/`. Invoke the business-analyst with the
   sources and the product's scope; it uses the two requirements skills. State
   and pending items live in `CONTEXT.md` / `PERGUNTAS.md`, without inventing a
   TASK.
2. Produce the BRD/PRD and the SDD projection; record the sources' coverage.
   Blocking gaps become questions before any technical specification.
3. The PO and QA review the business specification and the BA reconciles the
   model. A score ≥ 95 with zero blockers: seal it with
   `requirements-gate.py seal`.
4. The PRD/BRD approval stop that the bootstrap already has: present the paths,
   the remaining non-critical doubts and the completeness. Record the Owner's
   decision, the date and the hash from `requirements-gate.py delivery` in
   `CONTEXT.md`. Before continuing, verify that the hash still matches what was
   approved.
5. Continue with steps 2–5 of mode `prd`, consuming the projections in
   `requirements` (do not create divergent copies under `docs`). Preserve the
   REQ/AC IDs in the features and in the backlog. Future demands import only the
   relevant subset, keep the IDs and the origin, and produce their own seal and G1.
6. Follow the closing steps of `/faber-init`. Do not create issues automatically
   during bootstrap.

Raw audio is inventory awaiting transcription, not an analysed textual source.
Do not configure a transcription service and do not install Spec Kit in this flow.
