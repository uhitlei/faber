# Discovery de requisitos — especificação da reestruturação 1.1.0

Status: implementado no kit local; validação com reunião real fica para a próxima etapa.
Base: faber-kit 1.0.0. Nome adotado: `business-analyst`.

## 1. Objetivo e escopo

Transformar transcrições, anotações e documentos em evidências, requisitos,
BRD/PRD e uma especificação de negócio para a fábrica. Áudio bruto pode ser
inventariado, mas não é interpretado como transcrito. A transcrição é uma
entrada externa nesta versão; não há serviço de áudio, credenciais ou upload.

O CTO continua coordenando. BA extrai e esclarece; PO escreve a spec;
QA avalia testabilidade; CTO e developer refinam; Owner aprova G1.
Não são criados estados nem gates humanos adicionais por demanda.
O bootstrap mantém sua aprovação de PRD/BRD antes das specs.

## 2. Fluxo

`/faber-discovery TASK-XXX <fontes>` retoma uma demanda existente no seu worktree.
`/faber-task` encaminha ao BA quando a entrada contém material de discovery.
`/faber-init --mode discovery` usa `faber/bootstrap/requirements/`.

1. Inventariar fontes, seus limites e a revisão de conteúdo por SHA-256.
2. Extrair evidências com localização e distinguir declaração, inferência e decisão.
3. Registrar contexto, objetivos, usuários, escopo, fluxos, regras e requisitos.
4. Produzir BRD/PRD preliminares e registrar lacunas; nada ausente é inventado.
5. Calcular completude; perguntas prioritárias voltam pelo CTO ao Owner.
6. Incorporar respostas como novas fontes e recalcular.
7. PO e QA produzem/revisam spec e critérios de aceite; refinamento técnico segue o kit.
8. Selar os artefatos revisados, verificar G1 e aguardar a aprovação humana existente.

Sem nova informação, não repetir perguntas nem reinvocar agentes indefinidamente.
Uma reunião pode abranger várias features: no bootstrap, gerar backlog candidato;
em demanda existente, limitar ao escopo dela e registrar demais ideias fora dele.

## 3. Arquivos novos e contratos

| Arquivo relativo à raiz instalada | Responsabilidade |
|---|---|
| `.claude/agents/business-analyst.md` | Papel, entrada mínima, limites e handoff do BA |
| `.claude/skills/requirements-discovery/SKILL.md` | Extração, perguntas e geração de documentos |
| `.claude/skills/requirements-discovery/references/contract.md` | Schema e governança dos artefatos |
| `.claude/skills/requirements-discovery/references/spec-kit.md` | Projeção SDD e responsabilidade técnica |
| `.claude/skills/requirements-readiness/SKILL.md` | Rubrica, interpretação e comandos do validador |
| `.claude/commands/faber-discovery.md` | Entrada operacional, delegada pelo CTO |
| `faber/bootstrap/modes/discovery.md` | Discovery antes da fundação do produto |
| `faber/templates/requirements/*.template.yaml` | Fontes, evidências, modelo e avaliação |
| `faber/scripts/lib/requirements.py` | Validação, pontuação, hashes e selo |
| `faber/scripts/requirements-gate.py` | Interface de linha de comando |
| `faber/scripts/test-requirements.py` | Verificações técnicas com fixtures sintéticas, sem reunião real |

Por demanda ou bootstrap, uma pasta `requirements/` contém quatro entradas:
`sources.yaml`, `evidence.yaml`, `model.yaml`, `assessment.yaml`.
As saídas são `BRD.md`, `PRD.md`, `speckit/spec.md`, `readiness.json` e
`delivery.json`. Fontes permanecem nos paths registrados, sem cópia compulsória.
O contrato detalhado vive na referência da skill, evitando schemas duplicados.

## 4. Arquivos existentes alterados

| Arquivo | Mudança |
|---|---|
| `CLAUDE.md`, `faber/ARCHITECTURE.md` | Papel do BA, responsabilidades e fonte de verdade |
| `.claude/commands/faber-task.md`, `faber-resume.md`, `faber-develop.md` | Roteamento, retomada e verificação antes de implementar |
| `.claude/agents/product-owner.md`, `qa.md`, `doc-writer.md` | Consumo e revisão dos requisitos, preservação dos IDs |
| `faber/templates/state.template.yaml` | Metadado opcional `discovery.required` |
| `faber/scripts/gate-check.sh` | Checagem em ready-for-dev e nos avanços a partir de in-development |
| `faber/scripts/gate-set.sh` | G1 vinculado ao hash dos artefatos aprovados |
| `install.sh`, `.claude/commands/faber-init.md` | Novo modo explícito discovery |
| `faber/bootstrap/modes/brainstorm.md`, `prd.md`, `spec-kit.md` | Integração e precedência documental |
| `README.md`, docs de instalação/bootstrap, `VERSION` | Inventário e uso da versão 1.1.0 |

## 5. Pontuação de completude

Pesos: problema/objetivos 15, usuários 10, escopo 15, fluxos/regras 15,
requisitos 15, aceite 15, dados/integrações 5, qualidade 5, rastreabilidade 5.
Cada dimensão tem verificações explícitas na rubrica do código e no template.
Cada verificação vale 0 (missing), 0,5 (partial) ou 1 (verified).
Uma verificação `verified` precisa de justificativa e referências existentes.
Não há campo livre para o agente digitar uma nota final.

Dados/integrações podem ser `not-applicable` com justificativa e evidência.
Essa dimensão é excluída do denominador; os demais pesos são normalizados.
Ausência de informação nunca justifica não aplicabilidade.
O gate exige valor real >=95, sem arredondar 94,99 para aprovação.

Bloqueiam independentemente da nota: fonte obrigatória não coberta, arquivo
ausente/alterado, referência quebrada, requisito ativo sem evidência/aceite,
requisito ainda em draft/proposed, pergunta ou conflito crítico aberto e
hipótese crítica não validada. Requisitos rejected/deprecated são preservados
mas não contam como escopo ativo. Nota é completude declarada com estrutura
verificada, não probabilidade de verdade; PO, QA e Owner revisam o significado.

## 6. Fonte de verdade e revisões

`state.yaml`: estados, gates, workflow. `model.yaml`: registro dos requisitos
e suas origens. BRD/PRD e Spec Kit: projeções com os mesmos IDs. A spec da
demanda rege a implementação aprovada; a SPEC RFC global recebe consolidação
no G9. Essas responsabilidades não se sobrepõem.

Editar documentos derivados exige reconciliar o modelo, regenerar/revisar as
projeções e selar novamente. O selo inclui hash das entradas, fontes e arquivos
de saída. Alteração após G1 invalida seu vínculo; requer novo G1 para voltar ao
desenvolvimento. Hash comprova revisão de bytes, não correção semântica.

Spec Kit: o BA prepara somente `speckit/spec.md` (o quê/por quê). O plano,
contratos e tarefas pertencem ao refinamento técnico. Quando houver Spec Kit
instalado, usar seus templates reais e registrar a versão; não instalar nem
inventar suporte a comandos. Sem instalação, a saída é uma projeção Markdown
de SDD, sem afirmar validação pelo CLI do Spec Kit.

## 7. Compatibilidade e implantação

Demandas antigas sem discovery continuam com os gates anteriores. A presença
de `requirements/`, `discovery.required: true` ou um vínculo de G1 anterior
ativa a checagem; definir false não desativa um pacote existente/aprovado.
Não aplicar o discovery indiscriminadamente
a bugs/incidentes ou a demandas técnicas sem descoberta de negócio.

O modo discovery é explícito para evitar classificar qualquer .txt como reunião.
Brainstorm passa a usar o mesmo modelo de evidências. PRD/Spec Kit importados
mantêm seus modos existentes; não há migração automática de demandas históricas.

Entregar kit completo e inventário de alterações; a atualização de uma fábrica
já instalada deve aplicar o diff revisado, preservando personalizações. Não
executar `install.sh --force` no projeto original como parte desta entrega.

## 8. Aceite técnico e validação posterior

Verificar estrutura, YAML, sintaxe e invariantes de gate: vazios não aprovam,
fontes parciais e hashes antigos bloqueiam, referências precisam existir,
aprovação humana não é substituída e demandas legadas preservam seu fluxo.
Na próxima etapa: executar uma reunião real, comparar evidências extraídas com
as fontes, revisar utilidade das perguntas e calibrar a rubrica com o usuário.
Nenhuma afirmação de precisão de 95% decorre dessas verificações técnicas.
