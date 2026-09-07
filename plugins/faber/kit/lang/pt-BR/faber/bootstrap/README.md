# faber/bootstrap — inicialização da fábrica neste repositório

Esta pasta é o **canal entre o instalador (`install.sh`, sem LLM) e o CTO
(`/faber-init`, com LLM)**.

| Arquivo | Quem escreve | Conteúdo |
|---|---|---|
| `CONTEXT.md` | `install.sh` (cria) · `/faber-init` (conclui) | modo detectado, sinais, arquivos de entrada, interação, `status: pendente|concluido` |
| `modes/<modo>.md` | kit | playbook que o CTO segue em cada modo |
| `PERGUNTAS.md` | `/faber-init` | dúvidas agrupadas para o Owner (uma rodada) |
| `BACKLOG.md` | `/faber-init` | demandas candidatas (título · tipo · prioridade · origem) |
| `evidence/` | `/faber-init` via `evidence.sh faber/bootstrap …` | comandos executados durante o bootstrap |

## Os cinco modos

| Modo | Sinal detectado | O que o CTO gera |
|---|---|---|
| `existing-repo` | código-fonte + histórico git | specs globais lidas do código, inventário de features, config real (lint/build/test, migrations, paths protegidos) |
| `spec-kit` | `.specify/`, `memory/constitution.md`, `specs/NNN-*/spec.md` | constituição → regras; cada feature spec-kit → SPEC RFC; plan.md → arquitetura; tasks.md → backlog |
| `prd` | `PRD*.md` / `BRD*.md` (raiz ou `docs/`) | arquitetura `[PROPOSTA]`, specs de feature derivadas dos RF/RNF, backlog priorizado |
| `brainstorm` | `*brainstorm*.md` / `ideias.md` / `braindump.md` | PRD + BRD seguindo `faber/templates/prd-brd-guide.md` → **parada para aprovação** → continua como `prd` |
| `empty` | nada acima | pergunta ao Owner qual insumo trazer (ou uma descrição) e cai num dos modos acima |

Precedência quando há mais de um sinal: `existing-repo` > `spec-kit` > `prd` >
`brainstorm` > `empty` (o insumo mais rico manda; os demais são citados no
CONTEXTO e usados como fonte secundária). Override: `install.sh --mode <x>` ou
`/faber-init --mode <x>`.

## Gate de fundação

O bootstrap termina numa PR `faber/bootstrap → <trunk>`. O **merge pelo
Owner é a aprovação** da base de conhecimento. Depois dela, a primeira
demanda nasce com `/faber-task`.
