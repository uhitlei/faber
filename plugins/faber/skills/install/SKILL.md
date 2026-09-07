---
description: Install the Faber software factory into the current repository. Use when the user asks to install Faber, set up the software factory, add the gated agent workflow, or run /faber:install.
argument-hint: "[--mode existing-repo|spec-kit|prd|brainstorm|discovery|empty] [--profile node-web|node-supabase|python|generic]"
---

# /faber:install

Install Faber into the repository the user currently has open. Arguments (optional): **$ARGUMENTS**

Faber is not a plugin that runs the factory from the plugin cache. It is an
**installer**: the factory lives inside the user's repository, rendered with
their owner name, branches and validation commands. Nothing in the factory
works until this step completes — that is deliberate.

## 0. Locate the bundled installer

The payload ships with this plugin. Resolve its root, in this order:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$ROOT" ] && [ -f "$ROOT/install.sh" ] || \
  ROOT="$(find "$HOME/.claude/plugins" -maxdepth 4 -type d -name faber 2>/dev/null | while read -r d; do [ -f "$d/install.sh" ] && echo "$d" && break; done)"
echo "installer: $ROOT/install.sh"
```

If you cannot find `install.sh`, stop and tell the user the plugin payload is
missing — they should reinstall with `/plugin install faber@faber`. Do not try
to reconstruct the factory by hand.

## 1. Check prerequisites

Run and report, do not guess:

```bash
git --version; python3 --version; python3 -c "import yaml" 2>&1; gh --version 2>&1 | head -1
```

- `git` and `python3` are required. Stop if either is missing.
- PyYAML is required by `gate-check`, `board` and the hooks. If missing, tell
  the user to run `pip3 install pyyaml` and offer to continue anyway.
- `gh` is only needed when the demand ID should be a GitHub issue number.
  If it is absent, plan on `--gh off` (a local counter takes over).

## 2. Show the detected context, do not invent it

```bash
bash "$ROOT/install.sh" . --dry-run --interaction gates
```

Report the block the installer prints back: git state, code file count,
manifests, Spec Kit / PRD / brainstorm signals, and the bootstrap mode it
chose. This is deterministic detection with no model in the loop — present it
as fact, and say which mode it landed on and why.

## 3. Ask the user what only they can answer

Ask these together, with the installer's defaults pre-filled. Never answer
them on the user's behalf:

| Question | Default |
|---|---|
| Project name | the directory name |
| Human approver's name and slug (gates G1/G6/G8) | `git config user.name` |
| Production branch | detected `main`/`master` |
| Integration branch (task PRs target it) | detected `develop`, else the production branch |
| **Interaction mode** — `gates` (the CTO chains the flow and stops only at G1, G6, G8 and critical doubts) or `step-by-step` (stops after every phase) | `gates` |
| **Language** the agents work in — `en` or `pt-BR`; both packs are complete, and the machine contract (`state.yaml`, board columns, GitHub labels) is English either way | ask |
| GitHub issues for task IDs | `on` when `gh` is authenticated |
| Canonical specs folder | `specs` |
| Local Kanban dashboard (Flask, optional) | `off` |

The interaction mode and the language are the two questions the installer
refuses to answer by itself. Ask them explicitly.

## 4. Install

Pass every answer as a flag and add `--yes` so nothing is prompted twice:

```bash
bash "$ROOT/install.sh" . --yes \
  --interaction <gates|step-by-step> \
  --lang <en|pt-BR> \
  --project "<name>" --owner-name "<Full Name>" --owner <slug> \
  --main <branch> --trunk <branch> \
  --gh <on|off> --specs-dir <dir> --dashboard <on|off> \
  [--mode <mode>] [--profile <profile>] [--prd-guide <file.md>]
```

Report the installer's output verbatim where it warns. It writes
`CLAUDE.md`, `.claude/`, `faber/` and the specs skeleton, merges an existing
`.claude/settings.json` instead of overwriting it, preserves a previous
`CLAUDE.md` as section 9, and commits everything on the `faber/bootstrap`
branch. If the working tree was dirty it commits nothing and prints the
command for the user to run — pass that on rather than committing yourself.

## 5. Prove it works on this machine

```bash
bash .claude/hooks/test-h1-h2.sh | tail -1
bash faber/scripts/test-gate-check.sh | tail -1
```

Both must report `0 falha(s)`. If either fails, say so with the output — do
not describe the install as successful.

## 6. Hand over

Tell the user, in their language:

1. Restart Claude Code (or run `/reload-plugins`) so the 12 `faber-*` commands,
   9 agents and 10 skills that were just written into `.claude/` are loaded.
2. Run `/faber-init` — the bootstrap that reads the detected context and
   generates specs, architecture and backlog.
3. Merge the `faber/bootstrap` PR into the integration branch. That merge is
   the foundation gate and it is theirs to approve.
4. Then `/faber-task <first demand>` opens the first task.

Do not run `/faber-init` yourself in this session unless the user asks: the
commands are not loaded until Claude Code reloads.
