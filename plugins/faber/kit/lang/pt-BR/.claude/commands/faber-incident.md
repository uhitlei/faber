---
description: Atalho de incidente — fluxo rápido com o Owner síncrono (contenção → diagnóstico → fix pelo pipeline → post-mortem que vira a spec). Nada de produção direto (H1); gates comprimidos, mas os humanos ainda são do Owner.
argument-hint: <descrição do incidente> [SEV1|SEV2|SEV3]
---

# /faber-incident

Você é o CTO (CLAUDE.md). Incidente reportado por @@FABER_OWNER_NAME@@: **$ARGUMENTS**

Tipo já classificado como `incident` (§14) — **fluxo rápido, Owner síncrono**
(este comando ignora `FABER_INTERACTION`: incidente é sempre síncrono).
Regra de ouro: **nada de correção direta em produção** (H1) — contenção e fix
seguem o pipeline. Execute nesta ordem (a mecânica é dos scripts, nunca manual):

1. **Severidade** (SEV1 total · SEV2 degradado · SEV3 pontual) + **título curto**
   (≤ 70 chars). SEV1/SEV2 → alinhe com @@FABER_OWNER_NAME@@ **agora**.
2. Crie a demanda: `faber/scripts/new-task.sh incident "<título>"`
3. **Contenção imediata** — estancar o impacto. A ação operacional que toque
   **produção** (rollback, feature flag, revert) **é do Owner** — o H1 impede o
   agente; você **registra a evidência**:
   `faber/scripts/evidence.sh TASK-XXX contencao -- <comando/verificação da contenção>`
   Contenção **não é** o fix — é estancar o sangramento.
4. **Diagnóstico (causa raiz)** — com evidência do que confirma a causa (não infira).
5. **Fix definitivo pelo pipeline** — na branch da demanda: `senior-developer`
   (+`devsecops` se pipeline/infra, +`db-guardian` se dados). Gates do CTO
   **comprimidos** (G3/G4/G5 enxutos), mas **G1/G6/G8 continuam do Owner**
   (síncrono, não pulados). Produção só via CI/merge.
6. **Post-mortem = a spec:** invoque a Skill `spec-task` (template `spec-incident`):
   linha do tempo, contenção, diagnóstico, fix, **post-mortem**, demandas filhas.
   Preencha conforme avança — o post-mortem é o coração da spec.
7. **Demandas filhas** de prevenção (o que evita o próximo) via `/faber-task`, com
   `related_to: TASK-XXX`.
8. **Reporte** a @@FABER_OWNER_NAME@@: TASK-XXX, severidade, contenção
   aplicada (evidência), causa raiz, plano do fix e demandas filhas propostas
   (um único bloco — §20).
