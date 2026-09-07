# Modo `spec-kit` — repositório novo com especificações no formato Spec Kit

Sinais: `.specify/` (memory/constitution.md, templates/, scripts/) e/ou
`memory/constitution.md` na raiz, e `specs/NNN-nome/spec.md` (+ `plan.md`,
`research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`).
O Spec Kit é um **insumo**, não um concorrente: a fábrica consome o que ele
produziu e passa a governar o ciclo daqui em diante.

## Etapa 1 — Ler o que existe (com evidência)

1. `inventario-speckit` — liste os arquivos do Spec Kit encontrados
   (`find . -path ./node_modules -prune -o \( -name constitution.md -o -path '*/specs/*/spec.md' -o -path '*/specs/*/plan.md' -o -path '*/specs/*/tasks.md' \) -print`).
2. Leia `constitution.md` inteira; leia cada `spec.md`/`plan.md`/`tasks.md`
   **por seção**, sob demanda.

## Etapa 2 — Constituição → regras da fábrica

- Princípios da constituição que são **regras invioláveis** → `CLAUDE.md §2`
  (bloco "Regras do projeto", abaixo das regras da fábrica — sem alterar as da
  fábrica) e `@@FABER_SPECS_DIR@@/global/06-CONVENTIONS.md`.
- Princípios de qualidade/testes → `05-TESTING.md` (e, se pedirem cobertura
  bloqueante, registre em `ARQUITETURA §18` como exceção formal a decidir).
- Princípios de segurança → `03-SECURITY.md §3` (invariantes intocáveis).

## Etapa 3 — plan.md/research.md/data-model.md → globais

- Stack e estrutura declaradas no `plan.md` → `00-ARCHITECTURE.md` (marque
  `[PROPOSTA]` o que ainda não existe em código).
- `data-model.md` → `01-DATABASE.md`; `contracts/` → seção 8 das SPECs de feature.
- Decisões de `research.md` → ADRs resumidos em `00-ARCHITECTURE.md §5`.

## Etapa 4 — Cada `specs/NNN-nome/spec.md` → `@@FABER_SPECS_DIR@@/features/NN-nome/SPEC.md`

Converta para o padrão RFC (17 seções) via `faber/templates/spec-feature.template.md`:
user stories → personas + fluxos; requisitos funcionais → RF-NN (mantendo os
IDs originais entre parênteses para rastreabilidade); acceptance scenarios →
seção 14 (testes) e regras de negócio; edge cases → seção 11; `[NEEDS
CLARIFICATION]` do Spec Kit → **Open questions** (seção 16) e `PERGUNTAS.md`.
Não apague os arquivos do Spec Kit — eles ficam como origem histórica; a
verdade canônica passa a ser a SPEC RFC (CHANGELOG: "convertida do Spec Kit").

## Etapa 5 — tasks.md → backlog

Cada `tasks.md` vira demandas candidatas em `faber/bootstrap/BACKLOG.md`
(agrupe tarefas pequenas numa demanda `feature`; infra/CI → `infra`; banco →
`banco`). Preserve a ordem/dependências declaradas. Não crie issues ainda.

## Etapa 6 — Configuração e fechamento

Se o `plan.md` declara a stack, proponha `FABER_CMD_*`, `FABER_MIGRATIONS_DIR`,
`FABER_E2E` coerentes (a confirmar pelo Owner — ainda não há código para
provar). Se a pasta `specs/` do Spec Kit colide com `FABER_SPECS_DIR`, o
`install.sh` já escolheu outra pasta canônica (veja `CONTEXT.md`) — não misture.
Siga o "Encerramento" do `/faber-init`.

## Projeções produzidas pelo discovery

Um `requirements/speckit/spec.md` da versão 1.1.0 é uma projeção do modelo,
não um pacote técnico concluído. Preserve seus IDs e origem ao converter.
Plan/contracts/tasks, quando utilizados, pertencem ao refinamento técnico.
A demanda ativa governa implementação pelo G1; a SPEC RFC recebe consolidação.
Não mantenha duas specs editadas independentemente nem suponha CLI instalado.
