# Guia de generalização — como o kit remove as amarrações do projeto de origem

Este guia é a **fonte única de vocabulário** do kit. Tudo que era específico do
projeto de origem (nome do produto, nome do aprovador, branches, stack, paths)
vira **placeholder `@@CHAVE@@`** (renderizado pelo `install.sh` a partir de
`faber/config/faber.env`) ou **leitura em runtime** da mesma configuração
(scripts e hooks). Os spec-templates usam `{{...}}` para o AUTOR da spec — os
dois delimitadores nunca se misturam.

## Placeholders renderizados pelo install.sh (arquivos .md)

| Antes (projeto de origem) | Depois (kit) |
|---|---|
| `Uhitlei` (nome de exibição) | `@@FABER_OWNER_NAME@@` |
| `uhitlei` (slug em `--por uhitlei`, `aprovador: uhitlei`) | `@@FABER_OWNER@@` |
| `Jurisprudência em Questões`, `do Jurisprudência em Questões` | `@@FABER_PROJECT@@` |
| `Develop` (branch de integração), `origin/Develop` | `@@FABER_TRUNK@@`, `origin/@@FABER_TRUNK@@` |
| `main` (quando significa branch de produção) | `@@FABER_MAIN@@` |
| `Develop/main` | `@@FABER_TRUNK@@/@@FABER_MAIN@@` |
| `specs/PT-BR/` | `@@FABER_SPECS_DIR@@/` (globais em `global/NN-*.md`, features em `features/NN-nome/SPEC.md` — mesmos nomes 00–08) |
| `npm run lint` · `npm run build` · `npm run test:run` | `@@FABER_CMD_LINT@@` · `@@FABER_CMD_BUILD@@` · `@@FABER_CMD_TEST@@` |
| `npx playwright test …` | `@@FABER_CMD_E2E@@` |
| `supabase/migrations/` | `@@FABER_MIGRATIONS_DIR@@/` |
| `Jurisprudencia-Em-Questoes/jurisprudencia-boost-git` | nunca literal — use `faber/scripts/board.sh comentar-arquivo <issue#> <path>` ou `$(faber/scripts/board.sh repo)` |

## Conceitos que viram texto genérico (sem placeholder)

| Antes | Depois |
|---|---|
| `client.ts`/`types.ts` (arquivos gerados do Supabase) | "arquivos gerados/protegidos do projeto (`FABER_PROTECTED_PATHS`)" |
| `has_role`, policies de `is_correta` | "invariantes de segurança declaradas em `03-SECURITY.md` (seção *Invariantes intocáveis*)" |
| ref do projeto de PROD (string do project-ref), "qualquer ação em PROD" | "refs/ambientes de produção (`FABER_REFS_DENY`) — nunca por agente" |
| ref do projeto de HML, `supabase db push` em HML | "ambientes remotos que exigem confirmação (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`)" |
| "Supabase local (Docker)", Skill `supabase-local`, `local-env.sh` | "ambiente local descartável" · Skill **`local-env`** · `faber/scripts/local-env.sh` (mesmos subcomandos) |
| Perfis `aluno`/`gestor`/`admin` | "perfis de usuário do produto (ver `00-ARCHITECTURE.md`)" |
| shadcn/ui, TanStack Query, date-fns, Tailwind | "dependências já instaladas do projeto" (Design System: só onde a Skill `design-system-check` é citada, mantendo-a como módulo opcional `FABER_DESIGN_SYSTEM`) |
| Lista fixa de specs E2E (`auth.spec.ts`…), `playwright.config.ts`, porta 8080 | "leia a suíte E2E real do projeto em `05-TESTING.md` e na pasta de testes; nunca invente flags" |
| Incidente TASK-77 (E2E == HML) | lição genérica: "seed/reset destrutivo só contra alvo LOCAL confirmado; alvo remoto → pare e escale" |
| Referências a demandas históricas (TASK-77/91/101/105/106/110/118/120…) e revisões (`Rev N`, "revisão do item 9", achados A-1/B-9) | remover; manter só a REGRA resultante, em uma frase |
| Comentários HTML de histórico no fim dos arquivos (`<!-- Rev … -->`) | remover |
| Sonar: projeto `JQ`, espelho `JQ-TASK-XXX`, `.env.admin` | `$FABER_SONAR_PROJECT_KEY`, espelho `<PROJECT_KEY>-TASK-XXX`, `SONAR_ENV_FILE` (módulo opcional `FABER_SONAR`) |
| Modelos por agente (Opus/Sonnet) | manter — decisão de risco genérica |
| `faber/ARQUITETURA.md §N` | manter a numeração (o ARQUITETURA genérico preserva as seções) |

## Invariantes que NÃO mudam

- Prefixo de demanda `TASK-<issue#>`, branch `feature/TASK-XXX`, pasta `faber/tasks/TASK-XXX/`.
- Nomes dos 15 estados, dos 9 gates, dos 10 tipos e dos artefatos (`state.yaml`, `spec.md`, `refinamento.md`, `decisions.md`, `review.md`, `handoffs/`, `evidence/`).
- Formato do handoff (§17) e a regra "handoff sem evidência = inválido".
- Idioma PT-BR dos artefatos (configurável em `FABER_LANG`, mas o kit nasce em PT-BR).
