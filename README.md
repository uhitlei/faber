<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/faber-mark.svg">
  <img src="docs/brand/faber-mark-light.svg" alt="Faber: a fox head cut into shifted slices" width="200">
</picture>

# Faber

**A gated software factory for Claude Code.**

Nine specialised subagents, twelve commands, ten skills and seven deterministic
hooks that enforce the rules **in code, not in prompts**.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-170%20cases-black.svg)](#verification--evidence-not-promises)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-black.svg)](https://code.claude.com/docs/en/plugins)

[Install](#install) · [How it works](#how-it-works) · [What gets installed](#what-gets-installed) · [Português](README.pt-BR.md)

</div>

---

*Faber* is Latin for the one who makes — the root of *fabricate*, and of
*fábrica*, the Portuguese word for factory.

Every demand enters as `TASK-<issue#>`, runs in its own git worktree, and
passes nine gates. Three of them are yours: **G1** ready-for-dev, **G6** your
evaluation, **G8** merge. Every gate requires **executed evidence** — a real
command, its real output, on disk.

The orchestrator (the CTO) runs in your main session. The specialists run as
subagents with clean context. Everything that matters is written to disk and
committed on the task's branch, so `/faber-resume TASK-42` rebuilds any
session from scratch. Sessions are disposable; the repository is the memory.

## Install

```
/plugin marketplace add uhitlei/faber
/plugin install faber@faber
```

then, in the repository you want the factory in:

```
/faber:install
```

<details>
<summary>Two other ways in</summary>

**Ask Claude.** In any Claude Code session, in your repository:

> Install Faber in this repository, following
> `https://github.com/uhitlei/faber/blob/main/INSTALL.md`

**One line of shell.**

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh | bash
```

Full procedure, flags and troubleshooting: **[INSTALL.md](INSTALL.md)**.

</details>

The plugin ships three commands — `/faber:install`, `/faber:update`,
`/faber:doctor` — and nothing else. The factory itself is written into *your*
repository, rendered with your approver, your branches and your validation
commands. Nothing in it runs before that, by design: a half-installed factory
would approve gates against someone else's configuration.

### Requirements

- **Claude Code**, authenticated.
- `git`, `bash ≥ 3.2`, `python3` with **PyYAML** (`pip3 install pyyaml`).
- `gh` CLI, if you want task IDs to be GitHub issue numbers (recommended).
  Without it, a local counter takes over.
- Optional modules, each toggled in `faber/config/faber.env`: SonarQube,
  Playwright/Cypress, a local environment runner, a Flask Kanban dashboard.

## The installer reads your repository first

No model is involved in detection. It counts source files, reads manifests and
looks for known signals, then picks a bootstrap mode:

| Your repository | Mode | What `/faber-init` produces |
|---|---|---|
| code and history | `existing-repo` | global specs read out of the code, a feature inventory, and the real config (lint/build/test, migrations, protected paths) |
| **Spec Kit** specs | `spec-kit` | constitution → rules; each `spec.md` → a 17-section SPEC RFC; `plan.md` → architecture; `tasks.md` → backlog |
| a **PRD/BRD** | `prd` | `[PROPOSED]` architecture, feature specs from the requirements, prioritised backlog |
| a **brainstorm** | `brainstorm` | PRD + BRD following *your* guide, stops for approval, continues as `prd` |
| meeting transcripts and notes | `discovery` | the business analyst extracts evidence and requirements, produces BRD/PRD, resolves gaps |
| nothing yet | `empty` | asks what you will bring |

It also asks the one question it refuses to answer for you: do you want to be
involved **only at the validation gates**, or **step by step**?

## How it works

```text
/faber-task → spec (PO ∥ QA ∥ designer) → double refinement (CTO × dev) → [G1 · you]
→ /faber-develop: implementation → G3 (lint/build/test with evidence) → clean-context review → G4
→ parallel validation (QA ∥ db-guardian ∥ devsecops) → G5 → /faber-validate → [G6 · you]
→ /faber-pr → G7 → PR → [G8 · you, on GitHub] → doc-writer consolidates specs → G9 · done
```

The hooks are what make this real rather than aspirational. They block pushes
and merges to the trunk and to production, edits to secrets, already-applied
migrations and protected paths; they require a human confirmation dialog to
approve a human gate; and they check that every handoff carries evidence that
actually exists and is non-empty.

## What gets installed

```text
CLAUDE.md              # the CTO's constitution (a previous one is preserved as section 9)
.claude/
  settings.json        # permissions + hooks (merged, not overwritten)
  agents/   (9)        # business-analyst · product-owner · senior-developer · code-reviewer
                       # qa · devsecops · doc-writer · db-guardian · product-designer
  skills/   (10)       # requirements-discovery · requirements-readiness · spec-task · evidence
                       # spec-sync · migration-safe · local-env · e2e-runner · sonar-gate · design-system-check
  commands/ (12)       # /faber-init /faber-task /faber-bug /faber-spike /faber-incident /faber-discovery
                       # /faber-status /faber-resume /faber-approve /faber-develop /faber-validate /faber-pr
  hooks/    (H1–H7)    # guardrails parameterised by faber/config/faber.env
faber/
  ARCHITECTURE.md       # the architecture (stable numbering — agents cite §N)
  config/faber.env     # owner, branches, commands, modules, protected refs
  bootstrap/           # CONTEXT.md (detected mode) + playbooks for the six modes
  scripts/             # gate-check · transition · gate-set · new-task · worktree · evidence · board
  templates/           # state.yaml · specs by type · SPEC RFC · migration · handoff · PRD/BRD · globals
  tasks/               # one folder per TASK-XXX, travelling on the task's branch
<specs>/               # canonical base: README + global/00–08 + features/
```

## Verification — evidence, not promises

The factory's own rules are tested. After installing, in your repository:

```bash
bash .claude/hooks/test-h1-h2.sh           # 82 cases: what the hooks deny, confirm, allow
bash faber/scripts/test-gate-check.sh      # 43 cases: transitions blocked and released
bash faber/scripts/test-sonar-gate.sh      # 20 cases (Sonar module, curl stubbed)
python3 faber/scripts/test-monitor.py      # 40 cases (state monitor)
python3 faber/scripts/test-requirements.py # 21 cases (requirements readiness)
```

206 cases. They build throwaway sandboxes and never touch your repository.
`/faber:doctor` runs them for you and reports what is missing.

## Language

Faber is bilingual. The installer asks which language the agents should work in,
or you pass `--lang en` / `--lang pt-BR`:

| Layer | Language |
|---|---|
| The agents', skills' and commands' prose · `CLAUDE.md` · `faber/ARCHITECTURE.md` · the templates | **the pack you chose** — `kit/lang/en` or `kit/lang/pt-BR`, both complete |
| Command names, folders, `FABER_*` keys, `state.yaml`, the board's columns, the GitHub labels | **English in both packs** |
| What the factory *writes* — specs, issues, handoffs, gate messages | follows `FABER_LANG` (set from `--lang`, changeable afterwards) |
| Scripts and hooks | language-neutral |

The machine contract is deliberately identical in both languages. A `state.yaml`
per language would make the scripts, the board and the dashboard speak two
dialects of the same data — so a Portuguese install still writes
`state: my-review`, and a Portuguese team reads Portuguese prompts.

## Documentation

- **[INSTALL.md](INSTALL.md)** — installation, flags, verification, troubleshooting.
- [docs/bootstrap-modes.md](docs/bootstrap-modes.md) — the six modes and what each produces.
- [docs/configuration.md](docs/configuration.md) — every `faber.env` key, and the optional modules.
- [docs/requirements-discovery.md](docs/requirements-discovery.md) — the business analyst and the readiness gate.
- `plugins/faber/kit/faber/ARCHITECTURE.md` — the full architecture.

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
The one hard rule: **a change to a guardrail or a gate ships with a test case
that fails without it.**

## License

MIT — see [LICENSE](LICENSE).
