# Personalização — `faber/config/faber.env` e módulos

A configuração é **uma só** (`faber/config/faber.env`), lida em runtime
pelos scripts (`faber/scripts/lib/config.sh`) e pelos hooks
(`.claude/hooks/faber_config.py`). Os textos dos agentes/comandos são
renderizados uma vez pelo `install.sh` (placeholders `@@FABER_*@@`); se mudar
owner/branches depois, ajuste o `.env` e faça um `grep` pelos textos antigos em
`.claude/` e `CLAUDE.md`.

## Núcleo

| Chave | Efeito |
|---|---|
| `FABER_OWNER` / `FABER_OWNER_NAME` | quem aprova G1/G6/G8 (`gate-set --by <slug>`); também em `_schema.owner` do `state.template.yaml` (renderizado) |
| `FABER_TRUNK` / `FABER_MAIN` | branches protegidas pelo H1; base das demandas; alvo das PRs |
| `FABER_INTERACTION` | `gates` (para só em G1/G6/G8 e dúvidas críticas) ou `step-by-step` |
| `FABER_BYPASS` | `on` (padrão): em sessão `bypassPermissions` H1/H2 nunca abrem diálogo de confirmação — confirmações passam livres ou viram deny; só G1/G6/G8 ainda pedem o Owner. `off`: os hooks ignoram o modo da sessão |
| `FABER_WORKTREES` | `on` = cada demanda em `.claude/worktrees/TASK-XXX` |
| `FABER_GH` / `FABER_GH_REPO` | issues como ID da demanda; `off` = contador local |
| `FABER_BOARD` / `FABER_GH_PROJECT_TITLE` | Projects v2 (opções do campo Status = 9 colunas de §6.1) |
| `FABER_SPECS_DIR` | pasta canônica de specs |
| `FABER_CMD_LINT/BUILD/TEST` | o G3 exige evidência dos três |
| `FABER_SECRET_FILES` | H2 nega edição; H1 pede confirmação em escrita via shell |
| `FABER_PROTECTED_PATHS` | paths/prefixos que nenhum agente edita (gerados, snapshots) |
| `FABER_REFS_DENY` | qualquer comando contendo um destes tokens é **negado** (ex.: ref do projeto de produção) |
| `FABER_REFS_CONFIRM` | comando contendo o token **pede confirmação** (ex.: ref de homologação); em sessão bypass passa livre — o que nunca pode rodar sem ninguém olhando vai em `FABER_REFS_DENY` |
| `FABER_CMDS_DENY` / `FABER_CMDS_CONFIRM` | regex (separadas por ` ;; `) para comandos perigosos da sua stack |

## Módulos opcionais

| Módulo | Chaves | Liga |
|---|---|---|
| **E2E** | `FABER_E2E=on`, `FABER_CMD_E2E`, `FABER_E2E_CMD_REGEX`, `_SUMMARY_REGEX`, `_FAIL_REGEX` | exigência de E2E executado no G5 quando `impacto_ui: true` (5 condições no log) |
| **Banco** | `FABER_MIGRATIONS_DIR`, `FABER_MIGRATION_CHECKS` | H2 (imutabilidade de migrations), H3 (termos obrigatórios), Skill `migration-safe`, db-guardian |
| **Ambiente local** | `FABER_LOCAL_ENV=on`, `FABER_CMD_LOCAL_UP/STATUS/RESET/SEED/STOP` | Skill `local-env` (`local-env.sh` com guard de alvo local) |
| **Análise estática** | `FABER_SONAR=on`, `FABER_SONAR_PROJECT_KEY` (+ `SONAR_TOKEN`/`SONAR_HOST_URL` por env ou `SONAR_ENV_FILE`) | Skill `sonar-gate` (`sonar-task.sh` publica espelho; `sonar-gate.sh` dá o veredito) |
| **Design System** | `FABER_DESIGN_SYSTEM=on` | Skill `design-system-check` (grep de cor hardcoded — Tailwind) |
| **Dashboard** | `FABER_DASHBOARD=on` (+ `install.sh --dashboard on`) | `faber/dashboard/dashboard.sh` (Kanban + telemetria, 127.0.0.1) |

## Adaptar a outra stack

1. Use um perfil de `profiles/` como ponto de partida (`--profile`).
2. Ajuste `FABER_CMD_*` para os comandos reais; o G3 só aceita evidência
   de lint/build/test **executados**.
3. Se o runner de E2E não for Playwright, ajuste os três regex: o do comando
   que executa, o do sumário verde e o do sumário de falha.
4. Se não houver banco, deixe `FABER_MIGRATIONS_DIR` vazio — H3, migration-safe
   e db-guardian ficam inertes.
5. Liste em `FABER_REFS_DENY` qualquer identificador que apareça em
   comandos contra produção (IDs de projeto, hosts). É a regra mais valiosa do H1.
6. Rode `bash .claude/hooks/test-h1-h2.sh` depois de mudar regras — ele usa
   uma config própria de sandbox, então adicione casos seus se quiser cobrir
   os tokens reais (sem colar segredos).

## O que NÃO personalizar

- Prefixo `TASK-`, os 15 estados, os 9 gates, os 10 tipos e a numeração `§N`
  de `faber/ARCHITECTURE.md`: scripts, hooks, agentes e comandos dependem deles.
- A regra "handoff sem evidência = inválido" e "gate humano só pelo owner".

## Onde cada coisa do projeto de origem foi parar

Veja [GUIA-GENERALIZACAO.md](GUIA-GENERALIZACAO.md).
