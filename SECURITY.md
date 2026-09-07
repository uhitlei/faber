# Security Policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/uhitlei/faber/security/advisories/new)
rather than in a public issue. Include the affected file, what an attacker
gains, and a reproduction if you have one. Expect a first reply within a week.

## What Faber does to your machine

Faber is shell and Python. It has no telemetry and makes no network calls of
its own, except where you explicitly enable a module: `gh` for GitHub issues
and pull requests, and `curl` against your own SonarQube host when the Sonar
module is on.

The installer writes only inside the target repository and commits on a
`faber/bootstrap` branch. It never force-pushes and never touches your
production or integration branch.

## What Faber tries to prevent

The hooks are the security surface, and they are tested (`test-h1-h2.sh`,
46 cases). They deny pushes and merges involving the trunk or the production
branch, `gh pr merge`, writes to protected GitHub API endpoints, edits to
secret files, and changes to already-applied migrations. They require an
explicit human confirmation dialog before a human gate (G1/G6/G8) can be
approved — including via a raw `gate-set` call in Bash, which closes the
obvious forgery path.

These are guardrails against an agent's mistakes, not a sandbox against a
determined attacker with shell access to your machine.

## Piping the installer into bash

`bootstrap.sh` downloads a tarball from GitHub and executes the installer it
contains. If that is not acceptable in your environment, clone the repository,
read `plugins/faber/install.sh`, and run it yourself. Both paths are the same
code.
