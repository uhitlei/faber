# Contrato de arquivos — schema_version 1

Todos os paths abaixo são relativos à pasta da demanda ou bootstrap. Os quatro
YAML de entrada ficam em `requirements/`. IDs são strings estáveis e únicos;
use SRC-NNN, EV-NNN, REQ-NNN, AC-NNN, Q-NNN, CF-NNN, ASM-NNN. Nunca renumere
IDs existentes. Não reutilize IDs de itens excluídos.

## sources.yaml

`schema_version: 1`, `sources: []`. Cada fonte contém:
`id`, `kind` (transcript/notes/document/decision/audio), `path`, `sha256`,
`required` booleano, `coverage` (full/partial/pending/excluded),
`exclusion_reason` (obrigatório se required=false).
Path relativo à pasta da demanda, ou absoluto quando externo ao repositório.
Ao mover para outro computador, relocalize os paths e regenere a revisão.
Calcule hash por `python3 -c` com hashlib ou ferramenta SHA-256 disponível.

Toda fonte deve ser um arquivo legível na validação; URL deve ser acompanhada
de extrato local identificado, data de consulta e endereço original. Não
importe arquivos externos sem autorização de acesso. Não envie dados a serviços.

`full` significa cobertura integral relevante ao escopo explicitamente definido,
nunca apenas que foi aberto o arquivo. Fontes obrigatórias precisam de full.
Áudio obrigatório referencia `transcript_source: SRC-NNN` de transcrição também
obrigatória e full. Evidências apontam para a transcrição, não para bytes de áudio.
Ao existir só anotação, não a apresente como transcrição integral.

## evidence.yaml

`schema_version: 1`, `evidence: []`. Cada evidência:
`id`, `source` (SRC), `locator`, `quote`, `kind` (statement/decision/inference).
Adicione speaker, timestamp e interpretação quando conhecidos. O validador
confere integridade de referências e presença de citação/localização; a
fidelidade da citação e da interpretação é responsabilidade do BA e da revisão.

## model.yaml

`schema_version: 1`, `revision` inteiro positivo. Narrativas de negócio em:
`context`, `objectives`, `users`, `scope`, `out_of_scope`, `workflows`,
`business_rules`, `data_integrations`, `quality`, `risks`, `decisions`.
Referencie EVs nas narrativas. Estruture de forma proporcional ao projeto.

`requirements: []`, cada item:

```yaml
id: REQ-001
type: functional
statement: Enunciado do comportamento com condições observáveis.
status: proposed
evidence: [EV-001]
dependencies: []
acceptance_criteria:
  - id: AC-001
    statement: Condição inicial, ação e resultado observável.
```

Tipos: business/stakeholder/functional/nonfunctional/transition.
Status: draft/proposed/validated/approved/rejected/deprecated. Os dois últimos
exigem `reason` e são excluídos do escopo ativo. Preserve sua origem histórica.
Requisitos ativos precisam de evidências e pelo menos um aceite. Dependências
apontam a requisitos ativos; ciclos devem ser resolvidos no planejamento.
Para requisitos approved, registre também a decisão humana nas evidências;
o status sozinho não comprova autorização. `approved` não aprova G1.

`questions`, `conflicts`, `assumptions`: listas de objetos com `id`, `statement`,
`severity` (blocker/high/medium/low), `status` e `resolution_evidence`.
Status inicial open; resoluções são resolved (questions/conflicts) ou validated
(assumptions). Resolução exige EV existente. Blocker/high aberto bloqueia.
Omissão conhecida de questão crítica é falha de análise, mesmo se a nota passar.

## assessment.yaml e readiness.json

`schema_version: 1`, `checks` com todas as chaves do template. Cada check:
`status`, `reason`, `evidence`. Status: missing/partial/verified/not-applicable.
Somente data e integrations aceitam not-applicable, com evidência e motivo.
Não applicable é conclusão sustentada; desconhecimento é missing.
O script calcula `readiness.json`: nota, bloqueios, revisão e hash de entradas.
Esse relatório é uma projeção; nunca edite a nota para fazer o gate passar.

## delivery.json, aprovação e fonte de verdade

O comando seal registra hashes das entradas e de BRD, PRD, speckit/spec.md e,
em demandas, spec.md/refinement.md. Execute somente após revisão PO/QA e
refinamento. O selo não é aprovação; G1 continua sendo do Owner.

Antes do desenvolvimento, o gate recalcula hashes e verifica se G1 corresponde
ao selo atual. Mudanças nas fontes, requisitos ou documentos exigem revisão e
novo selo; mudança após aprovação exige renovar G1.

No bootstrap, o selo cobre somente as três projeções. Registre o hash do selo
com a aprovação do PRD/BRD em CONTEXT.md. Uma demanda originada do backlog
recebe seu próprio pacote com escopo e fontes relevantes, preservando IDs e
origem do bootstrap, e passa pelo G1 normal.

`state.yaml` governa workflow; `model.yaml` registra requisitos; spec da demanda
governa desenvolvimento; SPEC RFC global é consolidada após merge. Atualizar
requisito exige atualizar seus derivados, nunca manter versões concorrentes.
