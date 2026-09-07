# Modos de bootstrap

O `install.sh` detecta o modo; o `/faber-init` executa o playbook
correspondente (`faber/bootstrap/modes/<modo>.md`). Todos terminam numa PR
`faber/bootstrap → <trunk>`, cujo merge (seu) é o **gate de fundação**.

## Precedência

`existing-repo` > `spec-kit` > `prd` > `brainstorm` > `empty`. O insumo mais
rico manda; os demais aparecem em `CONTEXT.md` como fontes secundárias.
Override: `install.sh --mode X` ou `/faber-init --mode X`.

## `existing-repo`

**Sinal:** ≥ 10 arquivos de código e (manifesto ou ≥ 3 commits).
**Gera:** specs globais 00–08 lidas do código (fatos) · inventário de features
(`features/NN-nome/SPEC.md`, 17 seções) · ajustes propostos em
`faber.env` (comandos reais, migrations, paths protegidos, refs de ambientes,
E2E) · backlog de dívidas visíveis.
**Para em:** perguntas agrupadas (uma rodada) + PR de fundação.

## `spec-kit`

**Sinal:** `.specify/`, `memory/constitution.md` ou `specs/NNN-*/spec.md`.
**Gera:** constituição → regras do projeto no `CLAUDE.md` (seção própria) e
`06-CONVENTIONS` · `plan.md`/`research.md`/`data-model.md` → globais · cada
`spec.md` → SPEC RFC com rastreabilidade aos IDs originais · `[NEEDS
CLARIFICATION]` → Open questions · `tasks.md` → backlog. Os arquivos do Spec Kit
ficam como origem histórica.
**Atenção:** se `specs/` já é do Spec Kit, a pasta canônica da fábrica vira
`docs/specs` (o instalador propõe).

## `prd`

**Sinal:** `PRD*.md`, `BRD*.md`, `prd.md`, `brd.md`, `requisitos*.md`,
`requirements*.md` (raiz ou `docs/`).
**Gera:** `MAPA-PRD.md` (extração com IDs `RF-NN`/`RNF-NN`) · arquitetura
`[PROPOSTA]` com tabela de opções × trade-offs · globais derivadas · features
agrupadas por capacidade com rastreabilidade ao PRD · backlog priorizado
(fundação → MVP → spikes para propostas arriscadas).
**Para em:** perguntas agrupadas + PR de fundação.

## `brainstorm`

**Sinal:** `*brainstorm*.md`, `ideias.md`, `ideas.md`, `braindump.md`,
`notas.md`, `notes.md` (raiz ou `docs/`).
**Gera:** `MAPA-BRAINSTORM.md` (ideias numeradas `B-NN`) → **`docs/PRD.md` +
`docs/BRD.md` seguindo `faber/templates/prd-brd-guide.md`** (o seu guia, se
você o forneceu com `--prd-guide`; senão o padrão do kit), com rastreabilidade
`RF ↔ B-NN` e perguntas abertas em vez de suposições.
**Para em (obrigatório, em qualquer modo de interação):** aprovação do PRD/BRD
("PRD aprovado"). Depois continua como `prd`.

## `empty`

**Sinal:** nenhum dos anteriores.
**Faz:** pergunta (opções fechadas) qual insumo você vai trazer — ou grava
literalmente o que você ditar no chat em `docs/brainstorm.md` e segue o modo
`brainstorm`.

## Regras comuns

- Nada inventado: fato lido → afirmação; inferência → `[PROPOSTA]`; lacuna → pergunta.
- Evidência executada de tudo que for verificável (`evidence.sh faber/bootstrap …`).
- Nenhum `{{...}}` sobra em documento entregue.
- `gates`: uma rodada de perguntas + a PR. `step-by-step`: ok ao fim de cada etapa.

## discovery (1.1.0)

Sexto modo, selecionado explicitamente por `--mode discovery`, para
transcrições/notas/documentos. Usa business-analyst e requirements/ antes do PO,
completude >=95 e aprovação do PRD/BRD antes das specs. Brainstorm passa a usar
esse mecanismo. Não há transcrição de áudio nem instalação de Spec Kit automática.
