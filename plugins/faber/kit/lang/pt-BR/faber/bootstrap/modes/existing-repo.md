# Modo `existing-repo` — a fábrica entra num projeto que já existe

Objetivo: **descrever fielmente o que existe** (não propor) e ajustar a fábrica
à realidade do repositório. Tudo que vier do código é fato; o que for
interpretação leva `[PROPOSTA]`.

## Etapa 1 — Reconhecimento (com evidência)

Grave cada comando via `faber/scripts/evidence.sh faber/bootstrap <slug> -- <cmd>`:

1. `arvore` — árvore de diretórios até 3 níveis, ignorando `node_modules`, `.git`,
   `dist`, `build`, `vendor`, `.venv`, `target`.
2. `manifestos` — manifestos encontrados (`package.json`, `pyproject.toml`,
   `go.mod`, `Cargo.toml`, `pom.xml`, `composer.json`, `Gemfile`, `*.csproj`…):
   nome, versão, scripts/tarefas declaradas, dependências principais.
3. `ci` — workflows em `.github/workflows/` (ou equivalente): jobs, gatilhos,
   branches; onde rodam lint/build/test/e2e/deploy.
4. `database` — pasta de migrations (se houver), SGBD, ORM; contagem de migrations;
   presença de RLS/policies/GRANTs.
5. `testes` — frameworks de teste unitário e E2E; pastas; comandos.
6. `history` — `git log --oneline -30`, branches (`git branch -a`), convenção
   de commits observada, branch padrão real.
7. `env` — `.env.example` (só NOMES de variáveis; nunca abra `.env`/`.env.local`).

Use o subagente `Explore` (busca ampla, só conclusões) para mapear domínios,
rotas/endpoints, entidades e integrações externas — nunca despeje o repo no
contexto (§20).

## Etapa 2 — Configuração real (`faber/config/faber.env`)

Proponha ao Owner (e aplique após confirmação):
- `FABER_CMD_LINT/BUILD/TEST` com os comandos **que existem** nos manifestos;
  `FABER_E2E=on` + `FABER_CMD_E2E` + regex de sumário se houver suíte E2E;
- `FABER_MIGRATIONS_DIR` + `FABER_MIGRATION_CHECKS` se houver migrations
  (Postgres+RLS → `grant ,enable row level security,create policy,set search_path`);
- `FABER_PROTECTED_PATHS` para arquivos gerados (clients/tipos gerados,
  lockfiles de schema, snapshots de ORM);
- `FABER_SECRET_FILES` conforme os `.env*` observados;
- `FABER_REFS_DENY/CONFIRMAR` se identificar refs/IDs de ambientes
  remotos em configs versionadas (cite-os pelo NOME do arquivo, nunca copie
  segredos);
- `FABER_TRUNK`/`FABER_MAIN` conforme as branches reais.
- Labels: se `FABER_GH=on`, rode `faber/scripts/board.sh bootstrap-labels`.

## Etapa 3 — Specs globais (`@@FABER_SPECS_DIR@@/global/00–08`)

A partir dos templates em `faber/templates/specs-global/`, preencha com o que
foi lido: arquitetura (camadas, componentes, integrações, ADRs implícitos),
modelo de dados (entidades reais), design system (tokens/componentes reais ou
"não se aplica"), segurança (**seção 3 — invariantes intocáveis**: identifique
funções de papel, campos sensíveis, policies críticas; se não achar, deixe a
tabela com `[PROPOSTA]` e pergunta), deploy/CI (do que está nos workflows),
testes (comandos reais), convenções (observadas no código: naming, imports,
tratamento de erro), env (só nomes), playbook.

## Etapa 4 — Inventário de features (`@@FABER_SPECS_DIR@@/features/NN-nome/SPEC.md`)

Agrupe o código por domínio/funcionalidade visível ao usuário (rotas, telas,
comandos, endpoints). Para cada feature, preencha o template de 17 seções com o
que o código mostra (seções sem evidência: "não documentado — `[PROPOSTA]`" ou
Open question). Comece pelas 3–8 features principais; liste as demais no
README como "a documentar" (candidatas ao backlog, tipo `docs`).

## Etapa 5 — Backlog e fechamento

`faber/bootstrap/BACKLOG.md`: dívidas visíveis (TODO/FIXME, testes ausentes,
features sem spec, CI incompleto) como demandas candidatas com tipo §14.
Siga o "Encerramento" do `/faber-init`.
