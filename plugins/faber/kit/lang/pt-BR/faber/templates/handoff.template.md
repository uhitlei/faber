# Handoff — {{TASK-XXX}} · {{de}} → cto

<!-- Template do contrato de handoff (ARQUITETURA §17). Todo subagente encerra
     escrevendo faber/tasks/TASK-XXX/handoffs/NN-<de>-para-cto.md
     (NN = maior prefixo numérico existente + 1). O hook H5 valida o bloco
     YAML abaixo: campos obrigatórios + cada evidência existente e não vazia.
     Paths RELATIVOS à pasta da demanda (arquivos de produto: relativos à raiz
     do repo). Nunca cole conteúdo de arquivo — só paths. -->

```yaml
demanda: {{TASK-XXX}}
de: {{product-owner | senior-developer | code-reviewer | qa | devsecops | db-guardian | product-designer | doc-writer}}
para: cto
estado_sugerido: {{estado do §6.2 — sugestão; quem decide é o CTO}}
entradas_consumidas: [{{spec.md, refinamento.md, ...}}]
saidas_produzidas: [{{spec.md | review.md | src/... | ...}}]
evidence: [{{evidence/NN-slug.log, https://... (URL de CI/Sonar)}}]
pendencias: []            # dúvidas/desvios → obrigam decisão do CTO (ou escalonamento ao Owner)
riscos_novos: []
proxima_acao_sugerida: "{{...}}"
```

<!-- Regra de ouro: handoff sem evidência referenciada = handoff inválido
     (gate-check rejeita a transição). Seu texto final no chat é só um ponteiro
     para este arquivo + o estado_sugerido em uma linha. -->
