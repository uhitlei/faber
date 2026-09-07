---
description: Update an existing Faber installation to the version bundled with this plugin, preserving local configuration and task history. Use when the user asks to update or upgrade Faber, or runs /faber:update.
---

# /faber:update

Update the Faber installation in the current repository to the kit version
shipped with this plugin.

## 1. Refuse to update what was never installed

```bash
test -f faber/config/faber.env || { echo "Faber is not installed here"; }
```

If it is absent, do not "update" — that would silently install an unconfigured
factory. Point the user at `/faber:install` and stop.

## 2. Compare versions

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[ -n "$ROOT" ] && [ -f "$ROOT/VERSION" ] || \
  ROOT="$(find "$HOME/.claude/plugins" -maxdepth 4 -type d -name faber 2>/dev/null | while read -r d; do [ -f "$d/install.sh" ] && echo "$d" && break; done)"
echo "plugin ships: $(cat "$ROOT/VERSION")"
grep -m1 'kit_versao' faber/bootstrap/CONTEXT.md 2>/dev/null || echo "installed version unknown"
```

If they match, say so and stop. Do not rewrite files for nothing.

## 3. Require a clean tree and show the diff first

```bash
git status --porcelain
```

Refuse to proceed on a dirty tree — the user must commit or stash first, or
they cannot tell your changes from theirs.

Then show exactly what would change, without writing anything:

```bash
bash "$ROOT/install.sh" . --dry-run --yes --interaction "$(grep -oP '(?<=^FABER_INTERACTION=")[^"]*' faber/config/faber.env)"
```

## 4. Update

Re-running the installer keeps identical files, lists differing ones and
leaves them alone. `--force` overwrites the kit's own files but **preserves**
`faber/config/faber.env`, `faber/tasks/` and the specs folder.

```bash
bash "$ROOT/install.sh" . --yes --force \
  --interaction "$(grep -oP '(?<=^FABER_INTERACTION=")[^"]*' faber/config/faber.env)"
```

State clearly, before running it: `--force` discards any local edits the user
made to Faber's own agents, skills, commands or hooks. If they customised the
factory, list the files that differ and let them decide file by file instead.

## 5. Verify, then report

```bash
bash .claude/hooks/test-h1-h2.sh | tail -1
bash faber/scripts/test-gate-check.sh | tail -1
git diff --stat
```

Report what changed, what was preserved, and whether both suites are green.
Tell the user to restart Claude Code so the updated commands and agents load.
