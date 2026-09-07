# Modo `prd` — só existe um PRD e/ou BRD

Sinais: `PRD*.md`, `BRD*.md`, `prd.md`, `brd.md`, `docs/PRD*.md`,
`docs/BRD*.md`, `docs/requisitos*.md`. Não há código nem specs técnicas: a
fábrica **deriva** a base de conhecimento do documento de produto/negócio e
marca tudo que for decisão técnica como `[PROPOSTA]`.

Quando chamado pelo discovery/brainstorm 1.1.0, consuma BRD/PRD de
`faber/bootstrap/requirements/`, verifique o selo e o hash aprovado no
CONTEXTO e prossiga à etapa 2. Preserve IDs do modelo, sem novo MAPA divergente.
A importação direta de PRD legado continua nas etapas abaixo.

## Etapa 1 — Ler e mapear (com evidência)

1. `inventario-prd` — liste os documentos de entrada e o tamanho de cada um.
2. Leia o PRD/BRD por seção. Extraia para `faber/bootstrap/MAPA-PRD.md`:
   visão · personas · objetivos/métricas · escopo MVP e fora de escopo ·
   requisitos (RF/RNF com IDs; se não houver IDs, atribua `RF-NN` citando o
   trecho) · jornadas · restrições · riscos · perguntas abertas.
3. Tudo que o PRD **não** responde e que impede decidir arquitetura ou escopo
   → `PERGUNTAS.md` (uma rodada).

## Etapa 2 — Proposta de arquitetura (`00-ARCHITECTURE.md` `[PROPOSTA]`)

Com base em RNFs, restrições e integrações citadas, proponha stack, camadas e
integrações — **em uma tabela de opções × trade-offs**, com a recomendação
marcada. Nada é decidido sem o Owner; o documento nasce inteiro `[PROPOSTA]`.
Se o PRD já fixa tecnologia, registre como restrição (fato).

## Etapa 3 — Globais derivadas

- `01-DATABASE.md`: entidades inferidas dos requisitos (ER `[PROPOSTA]`).
- `02-DESIGN-SYSTEM.md`: "a definir" + princípios de acessibilidade do PRD, ou
  "não se aplica".
- `03-SECURITY.md`: dados sensíveis e papéis citados no PRD; invariantes
  `[PROPOSTA]`.
- `04-DEPLOYMENT.md`, `05-TESTING.md`, `06-CONVENTIONS.md`, `07-ENV-AND-SECRETS.md`:
  esqueleto com o que o PRD impõe (ambientes, compliance) e o resto "a definir
  na primeira demanda técnica".
- `08-AGENT-PLAYBOOK.md`: identidade do produto (fatos do PRD) + regras.

## Etapa 4 — Features (`features/NN-nome/SPEC.md`)

Agrupe RF/RNF por capacidade de produto (uma feature = um conjunto coeso de
requisitos e jornadas). Para cada uma, o template de 17 seções com: resumo,
problema, personas, requisitos (com rastreabilidade ao PRD), fluxos (das
jornadas), regras de negócio, edge cases, testes (critérios de aceite do PRD),
open questions. Seções técnicas (dados, contratos, arquitetura) ficam
`[PROPOSTA]` ou "a definir no refinamento".

## Etapa 5 — Backlog priorizado

`BACKLOG.md`: uma demanda `feature` por feature do MVP (ordem: dependências →
valor → risco), demandas `infra`/`database` de fundação (repo, CI, banco) antes
das features, e `spike` para cada `[PROPOSTA]` arquitetural que precisa de
prova. Siga o "Encerramento" do `/faber-init`.
