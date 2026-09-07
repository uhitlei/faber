---
name: spec-task
description: Seleciona e preenche o template de spec proporcional ao tipo da demanda da fábrica (TASK-XXX). Use ao criar, revisar ou completar o spec.md de uma demanda — nunca escrever spec de cabeça sem template.
---

# spec-task — templates proporcionais por tipo

Fonte: `faber/ARCHITECTURE.md` §11 (Skill), §14 (tipos), §18 (DoR do G1).
Templates em `faber/templates/`. Idioma: PT-BR (P6).

## Seleção do template (tipo → arquivo)

| Tipo (slug do `_schema.tipos`) | Template |
|---|---|
| feature | `spec-feature.template.md` |
| design | `spec-feature.template.md` |
| bug | `spec-bug.template.md` |
| incident | `spec-incident.template.md` |
| tech-debt | `spec-technical.template.md` |
| infra | `spec-technical.template.md` |
| security | `spec-technical.template.md` |
| database | `spec-technical.template.md` |
| docs | `spec-technical.template.md` |
| spike | `spec-spike.template.md` |

Nuances por tipo estão comentadas dentro de cada template (ex.: `security`
sem exploit em issue pública; `database` com db-guardian desde o refinamento;
`design` com a seção de impactos UX como centro).

## Como preencher

1. Copiar o template para `faber/tasks/TASK-XXX/spec.md`.
2. Substituir todos os `{{...}}`; **remover os comentários `<!-- -->`** ao
   preencher (eles são instruções, não conteúdo).
3. Nenhum `{{...}}` pode sobrar — placeholder restante = spec incompleta
   (bloqueia o DoR/G1).
4. ACs numerados (`AC-1`, `AC-2`…) e testáveis: são a base da matriz
   requisito×teste do QA e da validação do G5.
5. Proporcionalidade (§11): a spec deve estar **no nível do template do
   tipo** — não inchar bug simples com seções de feature, não afinar feature
   grande. Seção não aplicável recebe "nenhuma"/"não se aplica" explícito,
   nunca fica com placeholder.
6. Dúvida crítica aberta → estado `clarification` e pergunta a
   @@FABER_OWNER_NAME@@; parar é sempre preferível a avançar com dúvida
   (§6.2). O PO nunca inventa regra de negócio.
7. A spec é viva: mudanças durante refinamento/desenvolvimento são editadas
   na própria `spec.md` com registro no `history`/`decisions.md` da demanda.
