# @@FABER_PROJECT@@ — Specs

The project's **canonical** knowledge base, in the RFC pattern (one dense
`SPEC.md` per feature, plus cross-cutting global documents). Designed to be
consumed by AI agents and by humans alike. Every new technical decision is
reflected here before (or immediately after) it is coded — the `doc-writer`
consolidates at G9.

## Structure

```text
@@FABER_SPECS_DIR@@/
├── README.md               # this map
├── global/                 # cross-cutting docs (00–08)
├── features/               # one folder per feature: NN-name/SPEC.md (17 sections)
└── assets/diagrams/        # .mmd (Mermaid) sources and their renders
```

## The globals — required reading for any agent

| # | Document | When to read it |
|---|---|---|
| 00 | [Architecture](./global/00-ARCHITECTURE.md) | Always, before any change |
| 01 | [Database / data model](./global/01-DATABASE.md) | Before touching data, migrations or persistence contracts |
| 02 | [Design system](./global/02-DESIGN-SYSTEM.md) | Before any visual change |
| 03 | [Security](./global/03-SECURITY.md) | Before creating an entity, a policy, an endpoint or an integration |
| 04 | [Deployment & CI/CD](./global/04-DEPLOYMENT.md) | Before touching workflows or environments |
| 05 | [Testing](./global/05-TESTING.md) | Before adding a critical feature |
| 06 | [Code conventions](./global/06-CONVENTIONS.md) | Whenever you write new code |
| 07 | [Env & secrets](./global/07-ENV-AND-SECRETS.md) | Initial setup and switching environments |
| 08 | [Agent playbook](./global/08-AGENT-PLAYBOOK.md) | **The first thing an AI or agent reads** |

## Features

<!-- Filled in by /faber-init (bootstrap) and maintained by the doc-writer. -->
| # | Feature | Personas | Status |
|---|---|---|---|
| 01 | [{{name}}](./features/01-{{slug}}/SPEC.md) | {{personas}} | {{Draft}} |

## How an agent should use this

1. Start with `global/00-ARCHITECTURE.md` and `global/08-AGENT-PLAYBOOK.md`.
2. To implement or change a feature, open `features/NN-<name>/SPEC.md` and
   follow the contracts before touching the code.
3. Data changes only through a new migration (they are immutable); the security
   invariants in `03-SECURITY.md` are untouchable without the Owner's review.
