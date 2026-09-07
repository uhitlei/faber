# Mode `empty` — no input detected

The repository has no relevant code, no specs, no PRD/BRD and no brainstorm. The
factory is installed, but it has nothing to start from.

## What to do

1. Ask @@FABER_OWNER_NAME@@ (one round, closed options):
   - **(a)** they will bring a brainstorm file (`docs/brainstorm.md`) → mode `brainstorm`;
   - **(b)** they will bring a PRD/BRD (`docs/PRD.md`) → mode `prd`;
   - **(c)** they will bring specs in the Spec Kit format → mode `spec-kit`;
   - **(d)** they want to **dictate the product idea now, in the chat**, in a few
     sentences → you write it down **literally** in `docs/brainstorm.md` (without
     interpreting it) and follow mode `brainstorm`;
   - **(e)** the repository will receive code from elsewhere first → stop; run
     `/faber-init --mode existing-repo` afterwards.
2. Once the input arrives, update `faber/bootstrap/CONTEXT.md` (the `modo`, the
   input files) and follow the matching playbook.
3. If the Owner only wants to open a first demand with no knowledge base:
   explain that the factory works better with specs, but that it is possible —
   mark the bootstrap as `done (minimal)` and leave the global specs as a
   skeleton with `[TO BE DEFINED]`; the first `feature` demand will then demand a
   much larger clarification effort from the PO (§6.2).
