# Handoff — {{TASK-XXX}} · {{agente}} → cto

<!-- Template do contrato de handoff (ARQUITETURA §17). Todo subagente encerra
     escrevendo faber/tasks/TASK-XXX/handoffs/NN-<agente>-para-cto.md
     (NN = maior prefixo numérico existente + 1). O hook H5 valida o bloco
     YAML abaixo: campos obrigatórios + cada evidência existente e não vazia.
     Paths RELATIVOS à pasta da demanda (arquivos de produto: relativos à raiz
     do repo). Nunca cole conteúdo de arquivo — só paths. -->

```yaml
task: {{TASK-XXX}}
from_agent: {{product-owner | senior-developer | code-reviewer | qa | devsecops | db-guardian | product-designer | doc-writer}}
to_agent: cto
suggested_state: {{estado do §6.2 — sugestão; quem decide é o CTO}}
inputs_consumed: [{{spec.md, refinamento.md, ...}}]
outputs_produced: [{{spec.md | review.md | src/... | ...}}]
evidence: [{{evidence/NN-slug.log, https://... (URL de CI/Sonar)}}]
open_issues: []            # dúvidas/desvios → obrigam decisão do CTO (ou escalonamento ao Owner)
new_risks: []
suggested_next_action: "{{...}}"
```

<!-- Regra de ouro: handoff sem evidência referenciada = handoff inválido
     (gate-check rejeita a transição). Seu texto final no chat é só um ponteiro
     para este arquivo + o suggested_state em uma linha. -->
