# Contributing to Faber

Thanks for wanting to help. Faber is a factory that refuses to let unproven
work through a gate, so it holds itself to the same rule.

## The one hard rule

**A change to a guardrail or a gate ships with a test case that fails without
it.** Hooks live in `plugins/faber/kit/shared/.claude/hooks/`, the gate logic in
`plugins/faber/kit/shared/faber/scripts/gate-check.sh`, and their suites next to
them. A pull request that loosens a guardrail without a test is closed, however
reasonable it looks.

## Layout

```text
.claude-plugin/marketplace.json   # what /plugin marketplace add reads
plugins/faber/
  .claude-plugin/plugin.json      # the plugin manifest
  skills/{install,update,doctor}/ # the only three commands the plugin exposes
  install.sh                      # the real installer (no model in the loop)
  VERSION · profiles/             # version and configuration presets
  kit/                            # the payload written into the user's repo
    shared/                       # code + the machine contract — ONE copy
      .claude/{settings.json,hooks} · faber/{scripts,config,dashboard}
      faber/templates/{state.template.yaml,requirements}
    lang/en/ · lang/pt-BR/        # the prose — one copy per language
      CLAUDE.md · .claude/{agents,skills,commands}
      faber/{ARCHITECTURE.md,bootstrap,templates}
install.sh · bootstrap.sh         # thin entry points, same code path
bin/faber.js · package.json       # the npx entry point (@uhitlei/faber)
docs/ · INSTALL.md · README.md    # English, with pt-BR counterparts
```

Edit the payload under `plugins/faber/kit/`. Never edit a user's installed copy
and copy it back — the payload carries `@@FABER_*@@` placeholders that the
installer renders, and a rendered file committed here breaks every future
install.

**Which half does your change belong in?** If a script, a hook, the dashboard or
`state.yaml` reads it, it is the machine contract and lives in `shared/` — one
copy, English, identical for every language. If a human or an agent reads it as
prose, it lives in `lang/<lang>/` — and a change there means changing **both**
packs, keeping the contract keys byte-identical between them.

## Running the tests

```bash
cd plugins/faber/kit/shared
bash .claude/hooks/test-h1-h2.sh            # 82 cases
bash faber/scripts/test-gate-check.sh       # 43 cases
bash faber/scripts/test-sonar-gate.sh       # 20 cases
python3 faber/scripts/test-monitor.py       # 40 cases
python3 faber/scripts/test-requirements.py  # 21 cases
cd faber && python3 dashboard/testes/rodar.py   # optional module, needs flask
```

Every suite builds throwaway sandboxes. `FABER_SKIP_INSTALL_CHECK=1` is what
lets them run scripts in a tree that has no `faber/config/faber.env`; do not
remove that escape hatch, and do not widen it.

Then run an end-to-end install into a scratch repository and confirm it is
clean:

```bash
./install.sh /tmp/scratch-repo --yes --interaction gates --gh off --owner-name "Test User"
```

## Style

- Shell targets **bash 3.2** — macOS still ships it. No `declare -A`, no
  `${var^^}`, no `readarray`.
- Python is standard library only, except **PyYAML**, which is already a
  dependency. Do not add a third-party import to a hook: hooks run on every
  tool call and a missing module would break the session.
- Comments explain *why*, not *what*. Match the density of the file you are in.
- The `faber/ARCHITECTURE.md` numbering is a stable contract — agents cite `§N`.
  Add sections at the end; never renumber.

## Adding a bootstrap mode

1. A playbook in `plugins/faber/kit/lang/*/faber/bootstrap/modes/<mode>.md` (both packs).
2. Detection in `install.sh`, in the precedence chain, plus the `--mode`
   allowlist.
3. A row in `INSTALL.md`, `INSTALL.pt-BR.md` and both READMEs.
4. A case in the installer's dry-run output.

## Pull requests

Small and single-purpose. Say what you changed, why, and paste the test output
— the same evidence the factory demands of its own agents. If you changed the
payload, say whether an existing installation needs `--force` or a manual
diff, and add it to `CHANGELOG.md` under Unreleased.

## Code of conduct

Be decent. Assume good faith, argue about the code, and take the disagreement
to the evidence.
