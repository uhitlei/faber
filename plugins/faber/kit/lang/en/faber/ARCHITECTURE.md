# Faber — a software factory with agents · @@FABER_PROJECT@@

> **Kit version:** 2.0.0 · A portable reference architecture, derived from a
> factory operated in production and generalised.
> **This project's configuration:** `faber/config/faber.env`. Human approver:
> **@@FABER_OWNER_NAME@@** (`@@FABER_OWNER@@`). Trunk: `@@FABER_TRUNK@@` ·
> production: `@@FABER_MAIN@@`.
>
> The section numbering is **stable** — agents, skills, commands and hooks cite
> it (`§N`). When adapting this document to your project, edit the content,
> never the numbering.

---

## 1. Executive summary

The factory turns a request in plain language into a pull request ready to
merge, passing through specification, double refinement, development, review,
parallel validations and local acceptance — with **verifiable evidence at every
gate** and the human approver kept at three decision points: **Ready for
Development (G1)**, **My Review (G6)** and **Merge (G8)**.

Implemented with Claude Code's native mechanisms:

- **1 orchestrator (the CTO)** = the main session, governed by `CLAUDE.md`.
- **9 specialised subagents** (6 in the standard flow + 3 conditional), each with an isolated context, and tools and a model chosen by risk.
- **10 skills** of operational knowledge (evidence, specs, migrations, the local environment, E2E, static analysis, the design system, consolidation, discovery, readiness).
- **12 commands** (`/faber-init`, `/faber-discovery`, `/faber-task`, `/faber-bug`, `/faber-spike`, `/faber-incident`, `/faber-status`, `/faber-resume`, `/faber-approve`, `/faber-develop`, `/faber-validate`, `/faber-pr`).
- **7 deterministic hooks** that enforce the inviolable rules in code, parameterised by `faber/config/faber.env`.
- **GitHub Issues (plus an optional Projects v2 board)** as visible tracking; **files versioned on the demand's branch** as the source of truth; **`@@FABER_SPECS_DIR@@/`** as the canonical destination.

Principles: minimum context per agent · evidence before conclusion · separation
of planning from execution · templates proportional to the risk · mechanics
without an LLM wherever a script will do.

---

## 2. Understanding the scenario

<!-- Filled in by /faber-init with facts about the project (stack, branches, CI,
     the specs base, operations, the Owner's decisions). Until then, the
     configuration stands. -->

- **Product:** @@FABER_PROJECT@@ — {{domain, stage, user personas}}.
- **Stack:** {{...}}.
- **Git/CI:** `feature/* → PR → @@FABER_TRUNK@@ → @@FABER_MAIN@@`; CI: {{jobs}}.
- **Canonical base:** `@@FABER_SPECS_DIR@@/` (globals 00–08 + features).
- **Operation:** @@FABER_OWNER_NAME@@ is the single approver; the interaction mode is `FABER_INTERACTION`.

## 3. Assumptions

- **P1** — The Projects v2 board (when `FABER_BOARD=on`) has a Status field with the 9 macro columns (§6.1); the factory only manages issues carrying the `faber` label.
- **P2** — Tokens for external tools arrive exclusively through environment variables, referred to by **name**; never versioned.
- **P3** — A demand's artifacts (spec, handoffs, evidence) are committed on its own feature branch. Evidence over 2 MB is referenced, not committed.
- **P4** — The local environment (skill `local-env`) is disposable: the agent has full autonomy in it, with no approval.
- **P5** — The baseline DoD is the pre-merge checklist in `04-DEPLOYMENT.md §10`, extended by the factory's gates.
- **P6** — `FABER_LANG` governs specs, issues, handoffs and gate messages.

---

## 4. General architecture

### 4.1 Layers

| Layer | Component | Role |
|---|---|---|
| **Orchestration** | The main session = the **CTO** (`CLAUDE.md` + the commands) | Single entry point, classification, flow, subagents, gates, consolidation, escalation |
| **Specialised execution** | Subagents in `.claude/agents/` | An isolated context per responsibility; restricted tools and model |
| **Operational knowledge** | Skills in `.claude/skills/` | Procedures loaded on demand |
| **Operating interface** | Commands in `.claude/commands/` | Standardised entry points |
| **Deterministic enforcement** | Hooks in `.claude/hooks/` + `faber/config/faber.env` | Inviolable rules applied in code |
| **State and audit** | `faber/tasks/TASK-XXX/` (on the branch) + the issue + the board | `state.yaml` is the machine source; the issue is the human mirror; the board is the kanban |
| **Canonical destination** | `@@FABER_SPECS_DIR@@/` | The doc-writer's final consolidation |

### 4.2 The name "CTO"

It communicates gate authority and delegation — exactly the behaviour wanted —
and it is short to type in commands.

### 4.3 Why the CTO is not a subagent

Subagents are invoked by the main session and **do not invoke other subagents**.
So the orchestrator has to be the main session: (a) `CLAUDE.md` is its
constitution; (b) all parallelism is fired by the CTO; (c) subagents return
handoffs in files and the CTO decides the next step. That eliminates, by
construction, loops between agents outside the orchestrator's control.

### 4.4 Git strategy

The recommended model: **GitHub Flow plus an integration branch**
(`@@FABER_TRUNK@@` = continuous staging; `@@FABER_MAIN@@` = production, only by
promotion). The factory's rules: production only receives merges coming from the
trunk; G7 verifies that the feature branch is up to date with the trunk before
the PR. If the project uses a single trunk (`FABER_TRUNK=main`), the flow is the
same with one step fewer.

---

## 5. The flow, as a diagram

```text
OWNER ──/faber-task──▶ CTO (main session, Opus)
                    │ 1. interprets + consults specs/ + classifies the type (§14)
                    │ 2. creates TASK-XXX: the issue (label faber) + the branch feature/TASK-XXX
                    │    (in its own worktree) + faber/tasks/TASK-XXX/{state.yaml, spec.md}
                    │ 3. selects the flow by type
                    ▼
     ┌── SPECIFICATION ─────────────────────────────────────────────┐
     │ product-owner (Sonnet)      → business spec, stories, ACs     │
     │   ∥ qa (Sonnet)             → testability, scenarios, matrix  │
     │   ∥ product-designer (Sonnet, if UX/UI) → flows, states, DS   │
     │ (a technical demand: the CTO or the senior-developer specs it)│
     └──────────────────────────────────────────────────────────────┘
                    ▼
     ┌── TECHNICAL REFINEMENT (double, independent) ────────────────┐
     │ CTO produces analysis A ∥ senior-developer (Opus) analysis B │
     │ CTO compares → divergences → at most 2 rounds of rebuttal    │
     │ consensus ≥ objective criteria OR escalate to the OWNER      │
     │ devsecops (Sonnet) → pipeline/secrets/infra impact → tasks   │
     │ db-guardian (Opus, if the database) → model/RLS pre-analysis │
     │ ui_impact declared in state.yaml                             │
     └──────────────────────────────────────────────────────────────┘
                    ▼
   ══ GATE G1 · READY FOR DEVELOPMENT ══ (OWNER — an objective DoR)
                    ▼
     senior-developer (Opus): implements only the approved scope,
     tests, lint/build/test locally → evidence → traceable commits
                    ▼
   ══ GATE G3 · DEVELOPED ══ (gate-check.sh inspects the evidence)
                    ▼
     code-reviewer (Opus, clean context — only the diff + the spec)
     → opinion → tasks → the CTO is the review's final gate (G4)
                    ▼
     ┌── PARALLEL VALIDATIONS ──────────────────────────────────────┐
     │ qa → E2E (if ui_impact) + ACs + regression + evidence        │
     │ db-guardian (if the database) → migration, RLS, GRANT, rollback │
     │ devsecops → static analysis (skill sonar-gate) or the CI     │
     └──────────────────────────────────────────────────────────────┘
                    ▼
   ══ GATE G5 · TECHNICAL VALIDATION ══ (all green, or a formal exception)
                    ▼
     /faber-validate → the local environment + build → a test script on the issue
                    ▼
   ══ GATE G6 · MY REVIEW ══ (the OWNER tests and approves)
                    ▼
     /faber-pr → the CTO checks the gates + the updated branch + the
     consolidated description (what/why/how to test/risk/rollback) → PR
                    ▼
   ══ GATE G8 · MERGE ══ (ALWAYS the OWNER, on GitHub)
                    ▼
     doc-writer (Sonnet): consolidates specs/ + the CHANGELOG + the diagrams
     → cleans up the drafts → GATE G9 · DONE → worktree.sh clean
```

At every point: transitions written to `state.yaml` + a comment on the issue +
the board's column moved by a script (`transition.sh`), with no LLM consumed.
With `FABER_INTERACTION=gates`, the CTO chains the stretches between human gates
without stopping; with `step-by-step`, it stops at the end of each command.

---

## 6. The state machine

### 6.1 Three projections of the same state

1. **`state.yaml`** — the machine source of truth: the state, timestamps, and the gates with their approver and evidence.
2. **The issue** — the human mirror: the label `state:<fine>` plus gate comments.
3. **The Projects v2 board** (optional) — a Status field with **9 macro columns**: `Backlog · Specification · Ready for Dev · In Development · Review & Validation · My Review · PR Open · Done · Blocked`.

### 6.2 Fine states and transitions

| # | State | Column | Responsible | Entry / required artifacts | Exit / evidence |
|---|---|---|---|---|---|
| 1 | `intake` | Backlog | CTO | The request received | The type classified; the ID issued; the issue + branch + folder |
| 2 | `clarification` | Backlog | CTO → Owner | A critical ambiguity | The answers recorded in the spec |
| 3 | `specifying` | Specification | PO (or the CTO/developer if technical) | The flow selected | `spec.md` at the template's level; clear ACs; doubts cleared or escalated |
| 4 | `refinement` | Specification | CTO + senior-developer (+ devsecops, db-guardian) | The spec is ready | `refinement.md` (A and B, divergences resolved and trade-offs); DevSecOps tasks; `ui_impact` |
| 5 | `ready-for-dev` | Ready for Dev | **Owner** (G1) | The DoR at 100% (§18) | The approval recorded (`/faber-approve`) |
| 6 | `in-development` | In Development | senior-developer | G1 approved | The scope implemented; tests; lint + build + test green (logs) |
| 7 | `developed` | In Development | gate-check.sh | The G3 evidence | The branch pushed |
| 8 | `code-review` | Review & Validation | code-reviewer + CTO | `developed` + the branch on the remote | An opinion with no critical blocker |
| 9 | `validation` | Review & Validation | qa ∥ db-guardian ∥ devsecops | G4 approved + `review.md` | E2E (if UI) + ACs + database + static analysis green |
| 10 | `my-review` | My Review | **Owner** (G6) | G5 green; the environment ready; the script on the issue | "TASK-XXX validated" |
| 11 | `ready-for-pr` | My Review | CTO (G7) | G6 approved | The branch updated with the trunk; the PR description |
| 12 | `pr-open` | PR Open | **Owner** (G8) | G7 + the `pr` field | The merge performed by the Owner on GitHub |
| 13 | `done` | Done | doc-writer (G9) | G1–G8 approved or n/a | The specs consolidated; the CHANGELOG; the issue closed; **the branch deleted** (`worktree.sh clean`) |
| 14 | `blocked` | Blocked | whoever blocked it | A mandatory reason | It returns to the state it came from |
| 15 | `cancelled` | — (the issue is closed) | **Owner** | An explicit decision (`--reason`) | The reason recorded |

**General rules:** no transition without `gate-check.sh`; a regression only with
a reason; reopening a `done` demand creates a **new linked demand**
(`related_to`); `blocked` remembers the state it came from; every transition = a
commit to `state.yaml` + a comment on the issue + the board.

### 6.3 The authoritative copy among divergent sources

A demand can exist in several copies of `state.yaml` (active worktrees and git
refs). **The authoritative copy is the one with the highest `updated_at`**,
sweeping every known source. A `state` outside the closed list of 15 is an
**invalid read**, never a state, and it never beats a valid copy. Every
aggregating reader (e.g. `faber/dashboard/`) implements this rule.

---

## 7. Mandatory agents

| Agent | Kind | Model | Core responsibility | Does not do | Reads | Writes |
|---|---|---|---|---|---|---|
| **CTO** | Main session | Opus | Single entry point; classification; the flow; subagents; double refinement (A); the gates; consolidation; escalation | Implement code; approve human gates | Everything | `faber/`, the issue and the board (through scripts) |
| **product-owner** | Subagent | Sonnet | The business spec: problem, value, scope, rules, stories, ACs | Invent a business rule; decide architecture | The specs, the demand's spec | `spec.md`, the handoff |
| **senior-developer** | Subagent | **Opus** | Analysis B; implementing the approved scope; tests; evidence; commits | Change the scope; touch applied migrations, CI or the trunk | The specs, the code, the spec + refinement | Code, new migrations, tests, evidence, the handoff |
| **code-reviewer** | Subagent | **Opus** | The clean-context review (the diff + the spec + the conventions) | Fix code; approve its own opinion | The diff, the spec, 06/03 | `review.md`, the tasks |
| **qa** | Subagent | Sonnet | Spec phase: testability, scenarios, the matrix. Validation: E2E, ACs, regression, evidence | Relax a criterion; validate without running it | The spec, 05-TESTING, the tests | Scenarios in the spec, E2E tests, evidence, the handoff |
| **devsecops** | Subagent | Sonnet | The impact on pipeline, secrets, infra, deployment and rollback; operates `sonar-gate` or reads the CI | Edit workflows without an approved task; handle secrets | The workflows, 04, 07 | Tasks in the spec, evidence, the handoff |
| **doc-writer** | Subagent | Sonnet | At Done: consolidates the spec into `@@FABER_SPECS_DIR@@/` (17 sections), the CHANGELOG, the diagrams | Change code; rewrite decisions | The demand's folder, the specs | The specs, the archiving |

**Why a separate `code-reviewer`:** the review's value comes from the clean
context — the reviewer does not carry the implementer's reasoning. **Why the
`doc-writer`:** the canonical base requires syncing on every change — a distinct
responsibility, with its own context, parallelisable after the merge.

## 8. Conditional agents

| Agent | Model | Triggered when | Responsibility |
|---|---|---|---|
| **business-analyst** | **Opus** | There are discovery or brainstorm sources, or new business evidence | Evidence, requirements, BRD/PRD, questions and readiness; before the PO (§21) |
| **db-guardian** | **Opus** | There is data or database impact | The pre-analysis during refinement; at validation: the migration (GRANT/RLS/policy/indexes/integrity), destructiveness, compatibility, rollback, improper exposure |
| **product-designer** | Sonnet | There is UX/UI impact | Reuse of the design system, flows, interface states, responsiveness, accessibility, semantic tokens |

## 9. Roles considered, and where they live

| Role | Verdict |
|---|---|
| Architect | A stage: the double CTO × developer refinement **is** the architecture function |
| Security engineer | A checklist and a skill: 03-SECURITY + devsecops + db-guardian + the reviewer |
| SRE / observability | The devsecops checklist |
| Incident commander | The `/faber-incident` command (a CTO mode) |
| Performance | The reviewer's checklist + the project's limits |
| Accessibility | The product-designer's checklist |
| Release manager | Human + CI (the merge is the Owner's) |

## 10. RACI matrix

| Activity | Owner | CTO | PO | Dev | Reviewer | QA | DevSecOps | DB-G | Designer | Doc |
|---|---|---|---|---|---|---|---|---|---|---|
| Classification and triage | I | **R/A** | — | — | — | — | — | — | — | — |
| Business spec | C | A | **R** | — | — | C | — | — | C | — |
| Test scenarios | I | A | C | — | — | **R** | — | — | — | — |
| UX/UI design | C | A | C | — | — | — | — | — | **R** | — |
| Technical refinement | C* | **R/A** | — | **R** | — | — | C | C | — | — |
| G1 | **A** | R | I | I | — | I | I | I | I | — |
| Implementation | I | A | — | **R** | — | — | — | — | — | — |
| Code review | I | **A** | — | I | **R** | — | — | — | — | — |
| E2E / AC validation | I | A | — | I | — | **R** | — | — | — | — |
| Database validation | I | A | — | I | — | — | — | **R** | — | — |
| Static-analysis gate | I | A | — | I | — | — | **R** | — | — | — |
| G6 | **R/A** | I | — | — | — | — | — | — | — | — |
| PR (G7) | I | **R** | — | C | — | — | — | — | — | — |
| Merge (G8) | **R/A** | I | — | — | — | — | — | — | — | — |
| Consolidation (G9) | I | A | — | — | — | — | — | — | — | **R** |

\* Consulted only when consensus is not reached in 2 rounds.

---

## 11. Skills

| Skill | Used by | The problem it solves | Module |
|---|---|---|---|
| `requirements-discovery` | BA, CTO | Evidence, elicitation and traceable documents | discovery |
| `requirements-readiness` | BA, CTO, QA | Verifiable completeness and the revision seal | discovery |
| `spec-task` | CTO, PO | Proportional templates by type + the filling rules | core |
| `evidence` | everyone | Runs the real command and records stdout/stderr + exit code + timestamp | core |
| `spec-sync` | doc-writer | RFC consolidation (17 sections), the CHANGELOG, the diagrams, without duplicating | core |
| `migration-safe` | dev, db-guardian | The migration template, destructiveness, the reverse rollback | `FABER_MIGRATIONS_DIR` |
| `local-env` | dev, qa | The disposable local environment; validates the target is local before destroying anything | `FABER_LOCAL_ENV` |
| `e2e-runner` | qa | E2E execution with the project's patterns, and qualifiable evidence | `FABER_E2E` |
| `sonar-gate` | devsecops, CTO | Per-demand static analysis (the mirror project) with a Critical ∪ High verdict and a ratchet | `FABER_SONAR` |
| `design-system-check` | designer, reviewer | The hardcoded-colour grep + the manual checklist | `FABER_DESIGN_SYSTEM` |

Board sync is a script (`board.sh`), not a skill: zero LLM.

## 12. Commands

| Command | What it does |
|---|---|
| `/faber-init` | Bootstrap: reads `faber/bootstrap/CONTEXT.md` (the mode `install.sh` detected) and generates the specs, config and backlog |
| `/faber-discovery TASK-XXX <sources>` | Discovery on an existing demand; clarification, BRD/PRD and the handoff to the PO |
| `/faber-task <description>` | The standard entry point: classifies, creates TASK-XXX (issue + branch + folder, in a worktree) and starts the flow |
| `/faber-bug <description>` | A shortcut: requires a **reproduction** before the spec |
| `/faber-incident <description>` | The fast flow: containment → diagnosis → fix → post-mortem (the Owner synchronous) |
| `/faber-spike <topic>` | A timeboxed investigation; the output is a mini-ADR |
| `/faber-status [TASK-XXX]` | The consolidated state, read from disk and from `gh` |
| `/faber-resume TASK-XXX` | Rebuilds the context from disk in its own worktree and continues |
| `/faber-approve TASK-XXX <gate>` | Records the Owner's approval (G1/G6/G8) and unlocks the transition |
| `/faber-develop TASK-XXX` | Post-G1: implementation → G3 → review → G4 → validations → G5 |
| `/faber-validate TASK-XXX` | Prepares G6: the environment + the build + the script on the issue |
| `/faber-pr TASK-XXX` | Post-G6: G7 (the gates, the trunk merge, sanity) and opens the PR |

## 13. Hooks (deterministic enforcement)

| # | Event | Rule enforced |
|---|---|---|
| H1 | `PreToolUse` (Bash) | **Deny**: push/merge/commit involving the trunk or production · `gh pr merge` · a writing `gh api` against merges, protected refs or workflows · tokens from `FABER_REFS_DENY` · regexes from `FABER_CMDS_DENY`. **Ask**: tokens from `FABER_REFS_CONFIRM` · regexes from `FABER_CMDS_CONFIRM` · shell writes to H2's paths · a `gate-set` marking G1/G6/G8 as `approved` (the confirmation IS the Owner's approval) |
| H2 | `PreToolUse` (Write/Edit) | **Deny**: `FABER_SECRET_FILES` · `FABER_PROTECTED_PATHS` · a migration whose timestamp is already in the history. **Allow/Ask**: `.github/workflows/*` (allow with the Owner's `workflow_unlock`; otherwise ask). **Ask**: `.claude/settings.json`, `.claude/hooks/*`, `faber/config/faber.env` |
| H3 | `PostToolUse` (a Write in migrations) | Validates the placeholders and the statements in `FABER_MIGRATION_CHECKS`; warns and notes the pending item in the demand's log |
| H4 | `PostToolUse` (git commit) | `type(scope): description` + a `TASK-XXX` reference on a demand's branch |
| H5 | `SubagentStop` | A handoff in the §17 format, with evidence that exists; records the invocation (anti-loop) |
| H6 | `SessionStart` | The minimum context: active demands, the interaction mode, reminders; or a warning that the bootstrap is pending |
| H7 | `PreCompact` | A checkpoint: warns about uncommitted demand artifacts |

## 13-bis. Integrations

| Integration | Use | Module |
|---|---|---|
| The `gh` CLI | Issues, labels, comments, Projects v2, PRs, CI checks | `FABER_GH` / `FABER_BOARD` |
| The local environment (Docker or the project's CLI) | `local-env.sh` delegates to `FABER_CMD_LOCAL_*` | `FABER_LOCAL_ENV` |
| Static analysis (the SonarQube API) | `sonar-task.sh` + `sonar-gate.sh` (the token by name) | `FABER_SONAR` |
| CI (GitHub Actions or equivalent) | Consumed as evidence (`gh run`) | — |
| The local dashboard (Flask) | A kanban plus telemetry from the transcripts | `FABER_DASHBOARD` |

---

## 14. Flows by demand type

| Type | Variations on the standard flow | Agents |
|---|---|---|
| `feature` (new functionality / evolution) | The full flow | Everyone (the conditional ones by impact) |
| `bug` | **Reproduction is mandatory before the spec**; a reduced spec (repro + root cause + fix + regression) | CTO, dev, qa, reviewer |
| `incident` | Containment → diagnosis → fix → **the post-mortem becomes the spec**; compressed gates with the Owner synchronous; nothing straight to production | CTO, dev, devsecops (+ db-guardian) |
| `tech-debt` | The PO is skipped — the CTO or the developer specifies it; QA is proportional | CTO, dev, reviewer, qa |
| `security` | DevSecOps leads the spec; db-guardian if data is involved; handled discreetly (no exploit in a public issue) | devsecops, dev, db-guardian, reviewer |
| `infra` | DevSecOps leads; **every workflow diff requires the Owner's review** | devsecops, CTO |
| `database` | db-guardian **from the refinement onward**; `migration-safe` is mandatory | db-guardian, dev, reviewer |
| `docs` | Straight to the doc-writer; the only gate is the CTO's review | doc-writer, CTO |
| `spike` | A timebox at intake; **the output is a mini-ADR**, with no implementation; it may spawn children | CTO, dev |
| `design` | The designer leads; the developer only at implementation | designer, dev, reviewer |

**The demand's ID is the issue number** (`TASK-<issue#>`); with no GitHub
(`FABER_GH=off`), a local counter in `faber/tasks/.counter`.

## 15. The harness — anti-failure mechanisms

| Problem | Mechanism |
|---|---|
| Loops between agents | Subagents do not invoke each other, and H5 counts invocations: **at most 2 of the same subagent for the same task without a change of input** → the 3rd becomes `blocked` + escalation; refinement with ≤ 2 rebuttals |
| Circular approval | G1/G6/G8 only accept the approver in `_schema.owner`; `gate-check.sh` rejects self-approval; H1 asks for human confirmation on a `gate-set` of those gates |
| Loss of context | `state.yaml` + `spec.md` + `decisions.md` + the handoffs on disk; `/faber-resume`; H7 |
| Scope creep | The refinement declares the likely files; the diff is checked against the scope; the reviewer checks the diff against the spec |
| Agents overwriting each other | Only the senior-developer edits code in `in-development`; each agent writes to its own files |
| A false claim of execution | `evidence.sh` records the real output; the gates inspect the file; E2E only counts with 5 conditions in the same log |
| Advancing with no evidence | A deterministic `gate-check.sh` on every transition |
| Redundant files | A fixed naming convention; `spec-sync` is a merge, never duplication |
| Excess tokens | Handoffs by path; the minimum contract; scripts with no LLM; progressive disclosure |
| Unrecorded decisions | `decisions.md` per demand (mini-ADRs); trade-offs persisted |

## 16. Directory structure

```text
CLAUDE.md                      # The CTO's constitution (lean)
.claude/
├── settings.json              # permissions + the hooks' registration
├── agents/                    # 9 subagents
├── skills/                    # 10 skills (<name>/SKILL.md)
├── commands/                  # 12 commands
└── hooks/                     # H1–H7 + faber_config.py + test-h1-h2.sh
faber/
├── ARCHITECTURE.md            # this document
├── config/faber.env           # the configuration (a single source, read by scripts and hooks)
├── bootstrap/                 # CONTEXT.md, modes/*.md, PERGUNTAS.md, BACKLOG.md
├── templates/                 # state.template.yaml · spec-*.template.md · migration · handoff · PRD/BRD · specs-global/ · requirements/
├── scripts/                   # gate-check · transition · gate-set · new-task · worktree · evidence · board · workflow-unlock · local-env · sonar-* · design-system-check · monitor.py · the test suites
├── dashboard/                 # (optional) a local web kanban + telemetry
└── tasks/
    └── TASK-052/              # travels on the feature branch
        ├── state.yaml · spec.md · refinement.md · decisions.md · tasks.md · review.md
        ├── handoffs/          # NN-<agent>-para-cto.md
        └── evidence/          # NN-*.log (≤ 2 MB per file)
@@FABER_SPECS_DIR@@/
├── README.md · global/00–08 · features/NN-name/SPEC.md · assets/diagrams/
```

## 17. Handoff contracts

Every subagent finishes by writing `handoffs/NN-<agent>-para-cto.md` (H5
validates it):

```yaml
task: TASK-052
from_agent: senior-developer
to_agent: cto
suggested_state: developed
inputs_consumed: [spec.md, refinement.md]          # paths, never content
outputs_produced: [src/..., migrations/...]
evidence: [evidence/03-test-run.log, evidence/04-lint.log]
open_issues: []
new_risks: []
suggested_next_action: "code-review"
```

**A handoff with no evidence referenced is invalid** (gate-check rejects the
transition). Template: `faber/templates/handoff.template.md`.

## 18. Quality gates

| Gate | Name | Approver | Objective criterion |
|---|---|---|---|
| G1 | Ready for Development (DoR) | **Owner** | The DoR checklist at 100% |
| G2 | Technical consensus | CTO | No critical divergence; risks handled; ACs achievable; trade-offs recorded — or escalated |
| G3 | Developed | gate-check | Lint + build + test green (logs in `evidence/`); commits in the convention; the diff against the scope |
| G4 | Code review | CTO | An opinion with no critical blocker; the corrections closed |
| G5 | Technical validation | CTO | E2E green **when `ui_impact: true`** (5 conditions in the log) + the ACs + the database (where applicable) + static analysis with no **new** Critical/High (Medium/Low recorded; an exception only when documented) |
| G6 | My review | **Owner** | The environment validated by the Owner ("TASK-XXX validated") |
| G7 | Ready for PR | CTO | The earlier gates OK; the branch updated with the trunk; the description consolidated |
| G8 | Merge | **Owner** | Manual, on GitHub |
| G9 | Done | CTO | The specs consolidated + the CHANGELOG + the issue closed + the branch deleted |

**DoR (G1):** the spec at the level of its type's template · testable ACs ·
scenarios defined · design decisions (where applicable) · a refinement with
consensus or with trade-offs · risks and dependencies · DevSecOps tasks ·
`ui_impact` declared · zero open critical doubts.

**DoD:** the pre-merge checklist (`04-DEPLOYMENT §10`) + G1–G9 recorded in
`state.yaml` with their evidence.

**E2E at G5:** a log from `evidence.sh` only proves execution when **five**
conditions hold together: (i) the `# comando:` line matches
`FABER_E2E_CMD_REGEX` and is not `--list`/`--dry-run`; (ii) `# exit code: 0`;
(iii) the runner's real summary in the body (`FABER_E2E_SUMMARY_REGEX`); (iv) no
`|` in the command; (v) no failure summary (`FABER_E2E_FAIL_REGEX`). A filename
containing "e2e", or a `bash script.sh` wrapper, is not proof.

**Static analysis at G5:** servers with no multi-branch analysis require a
**mirror project per demand** (`<PROJECT_KEY>-TASK-XXX`, `sonar-task.sh`); the
verdict (`sonar-gate.sh`) blocks on the union of Critical ∪ High, treats the
Quality Gate as informational, applies a **ratchet** (only an issue that is new
relative to the trunk's baseline) and ties the verdict to the commit evaluated.
The mirror is deleted at G9.

## 19. Security and autonomy rules

| Action | Regime |
|---|---|
| A `feature/*` branch, commits, pushing the feature branch, a PR to the trunk | **Autonomous** |
| The disposable **local** environment | **Autonomous** (P4) |
| Reading specs, code, issues, CI checks, analysis APIs | **Autonomous** |
| Creating, moving and commenting on `faber` issues | **Autonomous** |
| Commands and refs in `FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM` | **The Owner's confirmation, per execution** |
| Editing `.github/workflows/` | **An approved task on the demand** (H2 / `workflow-unlock.sh`) |
| Editing the factory's hooks, settings or config | **The Owner's confirmation** |
| An exception to a gate (Medium/Low, coverage) | **A documented CTO decision; Critical/High never** |
| Merging; pushing or committing to the trunk or production; tokens in `FABER_REFS_DENY`; secrets; applied migrations; protected paths; the 03-SECURITY §3 invariants | **Forbidden — enforced by H1/H2** |

Secrets: agents never read or record values; they refer to them by **name**,
through an environment variable.

## 20. Context and efficiency strategy

1. **Model by risk:** Opus for the CTO, the developer, the reviewer and db-guardian; Sonnet for the PO, QA, DevSecOps, the designer and the doc-writer; **zero LLM** for the board, the evidence and gate-check.
2. **Minimum context per invocation:** paths plus quoted excerpts; a lean `CLAUDE.md` pointing at the specs (read by section).
3. **Progressive disclosure:** skills only when triggered.
4. **Aggressive persistence:** everything to disk immediately; sessions are disposable.
5. **Real parallelism:** specification (PO ∥ QA ∥ designer) and validation (QA ∥ DB ∥ devsecops).
6. **Batched approvals:** a single request per human gate.

## 21. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | Quota consumption with Opus | The items in §20; downgrade the conditional agents to Sonnet if it gets tight |
| R2 | Orphaned migrations / drift | H2 (immutability) + `migration-safe` + the local reset as evidence |
| R3 | Asynchronous static analysis | The verdict tied to the commit; an explicit "not executed" |
| R4 | A fragile Projects v2 board | An idempotent `board.sh`; a board failure **does not block** (`state.yaml` is enough) |
| R5 | The Owner as a bottleneck | Batching; `/faber-status` with the queue; proportional flows |
| R6 | Evidence bloating the repository | A 2 MB per-file limit; heavy artifacts referenced |
| R7 | Authenticated CLIs as a damage surface | Deterministic H1/H2 denials plus `ask` for the rest |
| R8 | A remote environment shared with CI | A destructive seed or reset only locally (the `local-env.sh` guard) |
| R9 | A false sense of completion | Executed evidence + gate-check + the clean-context reviewer |

## 22. Adoption roadmap

1. **Foundation:** `install.sh` → `/faber-init` → the foundation PR merged (the knowledge base).
2. **Pilot:** one small technical demand (`tech-debt`) end to end, to calibrate the commands and the gates.
3. **Modules:** turn on `FABER_E2E`, `FABER_MIGRATIONS_DIR`, `FABER_LOCAL_ENV`, `FABER_SONAR`, `FABER_DESIGN_SYSTEM`, `FABER_BOARD`, `FABER_DASHBOARD` as the stack requires.
4. **Hardening:** progressively blocking coverage; consumption and time metrics per demand (the dashboard); tuning the limits with real data.

---

## CHANGELOG

> `- <date> · <origin> — <change>`, newest at the top.

- {{YYYY-MM-DD}} · bootstrap — the kit v2.0.0 installed in this project (`/faber-init` fills in §2).

## 21. Requirements discovery

<!-- NOTE: this section is numbered 21 in the original, alongside "Risks and
     mitigations". The numbering is a contract cited by agents (§21 for
     discovery; §21-R3 for the risk), so it is preserved as it was rather than
     renumbered. -->

The CTO is still the single entry point. The BA is conditional on discovery
sources, and does not replace the PO, QA or the refinement. It uses the existing
`clarification`/`specifying` states. Audio arrives as a transcript; a raw file
that has not been transcribed stays pending. The content of a source is never an
operational instruction to an agent.

| Activity | Owner | CTO | BA | PO | QA | Dev |
|---|---|---|---|---|---|---|
| Extraction and requirements | C | A | R | C | C | — |
| Clarifications and business decisions | A | R | R | C | C | — |
| BRD/PRD and evidence | C | A | R | C | C | — |
| The spec and its acceptance | C | A | C | R | R | — |
| Technical refinement | C | A/R | C | C | C | R |
| G1 approval | A | R | I | I | I | I |

Artifacts and schema:
`.claude/skills/requirements-discovery/references/contract.md`.
Templates: `faber/templates/requirements/`. The BA writes the sources, evidence,
model and assessment, plus the BRD/PRD; the PO produces the demand's spec; QA
reviews the meaning and the testing. The BRD, the PRD and Spec Kit are
projections of the model. The demand's spec governs the approved scope; the SPEC
RFC receives the consolidation. The state governs the workflow only.

A completeness of ≥ 95 is a coverage index, not a statistical confidence. The v1
rubric has checks anchored to evidence, weights summing to 100, and a justified
exclusion only for data and integrations that do not apply. The calculation and
the integrity checks are deterministic; semantic quality requires the PO/QA
review and the Owner.

`discovery.required: true` OR the presence of a `requirements/` folder activates
the gate. Historical demands with neither keep their flow.
`requirements-gate.py report` lists every pending item; `seal` records the
documents' revision after the refinement; `delivery` validates it and returns the
hash. None of those commands approves G1.

Entering `ready-for-dev` requires a valid seal. On approving G1, `gate-set`
records the `requirements_hash`. Entering `in-development` and advancing
afterwards requires that same hash; a change invalidates the old approval.
Record the regression or the review, and obtain a new G1. Incomplete obligatory
sources, broken references, and open critical assumptions, conflicts or doubts
block even with a high score.

Discovery during bootstrap uses the same package and the PRD/BRD approval stop
that already exists; it records the hash alongside the decision in CONTEXT.
Brainstorm is one input into that flow. Spec Kit is a business projection; plans
and tasks belong to the refinement when that workflow is in use. No tool is
installed automatically.
