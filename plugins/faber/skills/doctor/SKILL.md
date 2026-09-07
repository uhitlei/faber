---
description: Diagnose a Faber installation in the current repository - what is present, what is missing, whether the guardrails actually fire. Use when the user asks whether Faber is installed, why a command or hook is not working, or runs /faber:doctor.
---

# /faber:doctor

Diagnose Faber in the repository the user has open. Report findings as facts
from commands you actually ran — never infer a component works because the
file exists.

## 1. Is it installed at all

```bash
test -f faber/config/faber.env && echo "installed" || echo "NOT installed"
```

If it is not installed, stop here and say so plainly: no Faber command,
script or hook operates in this tree, by design. Offer `/faber:install`.

## 2. Inventory against what the kit ships

```bash
echo "commands: $(ls .claude/commands/faber-*.md 2>/dev/null | wc -l) (expected 12)"
echo "agents:   $(ls .claude/agents/*.md 2>/dev/null | wc -l) (expected 9)"
echo "skills:   $(ls -d .claude/skills/*/ 2>/dev/null | wc -l) (expected 10)"
echo "hooks:    $(ls .claude/hooks/h?-*.sh 2>/dev/null | wc -l) (expected 7)"
echo "scripts:  $(ls faber/scripts/*.sh faber/scripts/*.py 2>/dev/null | wc -l)"
```

## 3. Configuration actually in force

```bash
grep -E '^FABER_(PROJETO|OWNER|OWNER_NOME|TRUNK|MAIN|INTERACAO|GH|SPECS_DIR|LANG|CMD_LINT|CMD_BUILD|CMD_TEST|E2E|MIGRATIONS_DIR)=' faber/config/faber.env
```

Check the branches exist and the validation commands are real:

```bash
git show-ref --verify --quiet refs/heads/$(grep -oP '(?<=^FABER_TRUNK=")[^"]*' faber/config/faber.env) && echo "trunk ok" || echo "trunk MISSING"
git show-ref --verify --quiet refs/heads/$(grep -oP '(?<=^FABER_MAIN=")[^"]*' faber/config/faber.env) && echo "main ok" || echo "main MISSING"
```

Flag any `FABER_CMD_*` that still carries the installer's `# (script não
encontrado — ajuste)` marker: those gates would run a command that does not
exist.

## 4. Are the hooks registered and wired

```bash
python3 -c "import json;h=json.load(open('.claude/settings.json'))['hooks'];print('\n'.join(f'{k}: {len(v)}' for k,v in h.items()))"
grep -c 'CLAUDE_PROJECT_DIR' .claude/settings.json
```

Hooks are registered in `.claude/settings.json`, not in the plugin. If the
user merged Faber into a repo that already had hooks, confirm Faber's are
still present.

## 5. Do the guardrails actually fire

This is the only evidence that matters. Run both suites:

```bash
bash .claude/hooks/test-h1-h2.sh | tail -1
bash faber/scripts/test-gate-check.sh | tail -1
```

Then prove H1 denies a push to the trunk in this specific repository:

```bash
echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"git push origin $(git symbolic-ref --short HEAD)\"},\"cwd\":\"$PWD\"}" \
  | bash .claude/hooks/h1-bash-guard.sh
```

## 6. Bootstrap and task state

```bash
head -12 faber/bootstrap/CONTEXT.md 2>/dev/null
ls -d faber/tasks/TASK-* 2>/dev/null | wc -l
```

If `status: pendente`, the factory is installed but not bootstrapped — the
next step is `/faber-init`, not a task.

## 7. Report

One short table: component, expected, found, verdict. Then the specific next
action. If everything passes, say so in one line without hedging.
