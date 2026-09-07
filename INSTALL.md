# Installing Faber

Three ways in. They all end at the same place: the factory rendered inside
your repository, on a `faber/bootstrap` branch, waiting for `/faber-init`.

> **Português:** [INSTALL.pt-BR.md](INSTALL.pt-BR.md)

---

## A. Claude Code plugin (recommended)

```
/plugin marketplace add uhitlei/faber
/plugin install faber@faber
```

Then, inside the repository you want the factory in:

```
/faber:install
```

The plugin gives you exactly three commands — `/faber:install`,
`/faber:update`, `/faber:doctor`. It does **not** give you the factory. The
factory is written into your repository, rendered with your approver name,
your branches and your validation commands, and nothing in it runs before
that. That is the point: a half-installed factory would approve gates against
someone else's configuration.

## B. Ask Claude to do it

In any Claude Code session, in the repository you want:

> Install Faber in this repository, following
> `https://github.com/uhitlei/faber/blob/main/INSTALL.md`

Claude fetches this file and follows section D below.

## C. One line of shell

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh | bash
```

Non-interactive (CI, scripts) — `--interaction` is mandatory because it is the
one thing the installer will not decide for you:

```bash
curl -fsSL https://raw.githubusercontent.com/uhitlei/faber/main/bootstrap.sh \
  | bash -s -- --yes --interaction gates --owner-name "Ana Silva" --lang en --trunk develop --main main --gh on
```

Or clone and run it yourself, if piping the internet into bash is not your
habit:

```bash
git clone https://github.com/uhitlei/faber.git && cd faber
./install.sh /path/to/your/repo
```

---

## D. The procedure, step by step

This section is written to be executed literally — by a person or by an agent.

### D.1 Prerequisites

```bash
git --version
python3 --version
python3 -c "import yaml" && echo "PyYAML ok" || echo "PyYAML MISSING"
gh --version | head -1
```

- `git` and `python3` are **required**. Stop if either is missing.
- **PyYAML** is required by `gate-check`, `board.sh` and the hooks:
  `pip3 install pyyaml`.
- `gh` is optional. With it, a task's ID is its GitHub issue number. Without
  it, pass `--gh off` and a local counter takes over.

### D.2 Get the payload

```bash
TMP="$(mktemp -d)"
curl -fsSL https://codeload.github.com/uhitlei/faber/tar.gz/main | tar -xz -C "$TMP" --strip-components=1
INSTALLER="$TMP/plugins/faber/install.sh"
```

### D.3 See what it detects before it writes anything

```bash
bash "$INSTALLER" /path/to/your/repo --dry-run --interaction gates
```

The installer uses **no model**. It counts source files, reads manifests and
looks for Spec Kit, PRD/BRD and brainstorm signals, then picks a bootstrap
mode by precedence:

| Repository looks like | Mode | What the bootstrap will produce |
|---|---|---|
| has code and history | `existing-repo` | global specs read out of the code (architecture, data, security, CI, testing, conventions), a feature inventory, and the real config (lint/build/test, migrations, protected paths) |
| new, with **Spec Kit** specs | `spec-kit` | constitution → rules; each `specs/NNN/spec.md` → a 17-section SPEC RFC; `plan.md` → architecture; `tasks.md` → backlog |
| only a **PRD/BRD** | `prd` | `[PROPOSED]` architecture, feature specs derived from the requirements, prioritised backlog |
| only a **brainstorm** | `brainstorm` | generates PRD + BRD following your own guide, stops for your approval, then continues as `prd` |
| meeting transcripts and notes (explicit choice) | `discovery` | the business analyst extracts evidence and requirements, produces BRD/PRD, resolves gaps, hands over to the PO |
| nothing | `empty` | asks which input you will bring |

Force one with `--mode <mode>` if the detection is wrong.

### D.4 Answer the questions

Defaults come from the repository. The one question with no default is the
**interaction mode**:

- `gates` — the CTO chains the whole flow and stops only at **G1**
  (ready-for-dev), **G6** (your evaluation), **G8** (merge) and on critical
  doubts. Recommended.
- `step-by-step` — the CTO stops at the end of every command and asks.

And the **language** the agents work in: `--lang en` or `--lang pt-BR`. Both
packs are complete; the machine contract (`state.yaml`, the board's columns,
the GitHub labels) is English either way.

### D.5 Install

```bash
bash "$INSTALLER" /path/to/your/repo --yes \
  --interaction gates \
  --project "My Product" \
  --owner-name "Ana Silva" --owner ana-silva \
  --main main --trunk develop \
  --gh on --specs-dir specs --dashboard off
```

Useful extras: `--mode <mode>` · `--profile node-web|node-supabase|python|generic`
· `--prd-guide my-guide.md` (your own PRD/BRD guide) · `--labels` (create the
`faber` and `estado:*` GitHub labels) · `--force` (overwrite the kit's own
files; **never** touches `faber/config/faber.env`, `faber/tasks/` or your specs).

What lands in your repository:

```text
CLAUDE.md              # the CTO's constitution (a previous one is preserved as section 9)
.claude/
  settings.json        # permissions + hooks (merged, not overwritten, if one existed)
  agents/   (9)        # business-analyst · product-owner · senior-developer · code-reviewer
                       # qa · devsecops · doc-writer · db-guardian · product-designer
  skills/   (10)       # requirements-discovery · requirements-readiness · spec-task · evidence
                       # spec-sync · migration-safe · local-env · e2e-runner · sonar-gate · design-system-check
  commands/ (12)       # /faber-init /faber-task /faber-bug /faber-spike /faber-incident /faber-discovery
                       # /faber-status /faber-resume /faber-approve /faber-develop /faber-validate /faber-pr
  hooks/    (H1–H7)    # guardrails parameterised by faber/config/faber.env
faber/
  ARCHITECTURE.md       # the architecture (stable numbering — agents cite §N)
  config/faber.env     # the configuration: owner, branches, commands, modules, protected refs
  bootstrap/           # CONTEXT.md (detected mode) + the playbooks for the six modes
  scripts/             # gate-check · transition · gate-set · new-task · worktree · evidence · board
  templates/           # state.yaml · specs by type · SPEC RFC · migration · handoff · PRD/BRD · globals
  tasks/               # one folder per TASK-XXX, travelling on the task's branch
<specs>/               # canonical base: README + global/00–08 + features/
```

### D.6 Verify — evidence, not promises

```bash
cd /path/to/your/repo
bash .claude/hooks/test-h1-h2.sh          # 46 cases: what the hooks deny, confirm and allow
bash faber/scripts/test-gate-check.sh     # 43 cases: transitions the gate lets through and blocks
bash faber/scripts/test-sonar-gate.sh     # 20 cases (Sonar module, curl stubbed)
python3 faber/scripts/test-monitor.py     # 40 cases (state monitor)
python3 faber/scripts/test-requirements.py # 21 cases (requirements readiness)
```

All five must be green. They build throwaway sandboxes and never touch your
repository. If one fails, the factory is not ready — read the output, do not
proceed.

Then prove the guardrail fires in *your* repository:

```bash
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git push origin $(git symbolic-ref --short HEAD)\"},\"cwd\":\"$PWD\"}" \
  | bash .claude/hooks/h1-bash-guard.sh
```

It must answer `"permissionDecision": "deny"`.

### D.7 Finish the bootstrap

1. Restart Claude Code (or `/reload-plugins`) so the new commands, agents and
   skills load.
2. `/faber-init` — generates specs, architecture and backlog from the detected
   context.
3. Merge the `faber/bootstrap` PR into your integration branch. **That merge is
   the foundation gate, and it is yours.**
4. `/faber-task <your first demand>`.

---

## Updating

```
/faber:update
```

or re-run the installer: identical files are skipped, differing ones are kept
and listed. `--force` overwrites the kit's files but preserves your config,
your tasks and your specs.

## Uninstalling

Remove `CLAUDE.md` (or restore `CLAUDE.md.bak-faber`), `.claude/agents`,
`.claude/skills`, `.claude/commands`, `.claude/hooks`, Faber's hooks and
permissions from `.claude/settings.json`, and the `faber/` folder. The specs
folder is yours — keep it.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Faber nao esta instalado nesta arvore` | a script ran where `faber/config/faber.env` does not exist | run `/faber:install`, or `cd` to the repository root |
| `/faber-*` commands do not appear | Claude Code has not reloaded since the install | restart, or `/reload-plugins` |
| `gate-check` fails with a YAML error | PyYAML missing | `pip3 install pyyaml` |
| `new-task.sh` cannot find the repo | `gh` absent or unauthenticated with `FABER_GH=on` | `gh auth login`, or set `FABER_GH="off"` |
| placeholders `@@FABER_*@@` still visible | rendering did not run for that file | re-run the installer with `--force` and report it as a bug |
