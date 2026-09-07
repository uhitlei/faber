# 08 · Agent Playbook (para IAs locais)

> Leitura **obrigatória** no início de qualquer sessão. Condensa o que um agente
> precisa saber para produzir mudanças seguras neste codebase.

## 1. Identidade do projeto

- **Nome:** @@FABER_PROJECT@@
- **Domínio:** {{...}}
- **Stack:** {{...}}
- **Idioma do código/UI:** {{...}}
- **Perfis de usuário:** {{...}}

## 2. Ordem de leitura recomendada

1. `00-ARCHITECTURE.md` · 2. `01-DATABASE.md` · 3. `03-SECURITY.md` · 4. `06-CONVENTIONS.md` · 5. `02-DESIGN-SYSTEM.md` · 6. a SPEC da feature que vai mexer.
Depois (CI/ambientes): `04-DEPLOYMENT.md` e `07-ENV-AND-SECRETS.md`.

## 3. Regras invioláveis

1. Nunca editar: {{arquivos gerados/protegidos — FABER_PROTECTED_PATHS}}.
2. Nunca alterar migrations já aplicadas; criar nova sempre.
3. {{Autorização/RLS habilitada em toda entidade nova + GRANTs explícitos}}.
4. Invariantes intocáveis de `03-SECURITY.md §3` só com revisão de @@FABER_OWNER_NAME@@.
5. Zero secrets em código/log/chat — sempre por nome.
6. {{regras específicas do projeto…}}

## 4. Quando precisar mexer em código

| Mudança pretendida | Ler antes | Atenção a |
|---|---|---|
| {{nova tela/endpoint}} | {{00, 02/03, spec}} | {{...}} |
| {{nova entidade}} | {{01, 03}} | {{migration-safe}} |
| {{integração externa}} | {{07}} | {{secret por nome}} |

## 5. Comandos de cabeceira

```bash
@@FABER_CMD_LINT@@
@@FABER_CMD_BUILD@@
@@FABER_CMD_TEST@@
@@FABER_CMD_E2E@@
```

## 6. Como descobrir o que existe

| Pergunta | Onde olhar |
|---|---|
| Quais entidades existem? | `01-DATABASE.md` / `{{FABER_MIGRATIONS_DIR}}` |
| Quais rotas/endpoints? | {{path}} |
| Como auth funciona? | {{path}} + `03-SECURITY.md` |

## 7. A fábrica

Demandas rodam como `TASK-<issue#>` em `faber/tasks/`, com gates G1–G9 (`faber/ARQUITETURA.md`). Comandos: `/faber-task`, `/faber-bug`, `/faber-spike`, `/faber-incident`, `/faber-status`, `/faber-resume`, `/faber-approve`, `/faber-develop`, `/faber-validate`, `/faber-pr`.
