---
description: Prepara o gate G6 (Minha Avaliação) — sobe o ambiente local (se configurado) e o build, e entrega ao Owner instruções passo a passo de teste na issue
argument-hint: TASK-XXX
---

# /faber-validate

Demanda: **$ARGUMENTS**

Prepara o G6 (§12/§18): ambiente pronto + roteiro de teste. Pré-condição:
estado `validation` com G5 aprovado (confira no `state.yaml`; se G5 pendente,
pare e reporte o que falta — nunca pule validação técnica).

1. **Transicione para `my-review`:**
   `faber/scripts/transition.sh TASK-XXX minha-avaliacao`
   (o gate-check exige G5 aprovado e, com `ui_impact: true` e `FABER_E2E=on`,
   evidência de E2E executado; bloqueou → resolva as pendências antes).
2. **Ambiente com evidência real:**
   - Se `FABER_LOCAL_ENV=on` (Skill `local-env`; dependência parada → peça ao
     Owner para iniciá-la):
     `faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`
     `faber/scripts/evidence.sh TASK-XXX seed-local -- faber/scripts/local-env.sh seed`
   - Sempre: `faber/scripts/evidence.sh TASK-XXX build-validacao -- @@FABER_CMD_BUILD@@`
   - Suba o que o Owner precisar para testar (ex.: servidor de dev — informe a
     URL; processos longos em background, nunca bloqueie a sessão).
3. **Roteiro de teste** a partir dos ACs da `spec.md`: passo a passo clicável
   (tela/comando, ação, resultado esperado), com os dados/usuários de teste
   documentados em `@@FABER_SPECS_DIR@@/global/05-TESTING.md`, e qual AC cada
   passo cobre. Inclua os casos de exceção relevantes da spec.
4. **Resumo no chamado (issue) — OBRIGATÓRIO (§20).** O Owner valida a partir
   da **issue**, não do chat. Antes de pedir a aprovação, grave o resumo em
   `faber/tasks/TASK-XXX/validacao-g6.md` e **poste-o na issue**:
   - **(i)** breve resumo do **que foi feito**;
   - **(ii)** as **ressalvas** do review (de `review.md`: o que foi corrigido /
     o que virou follow-up ou demanda filha);
   - **(iii)** **exatamente o que validar** — roteiro clicável + a frase de aprovação.

   Postar: `faber/scripts/board.sh comment-file <issue#> faber/tasks/TASK-XXX/validacao-g6.md`
   (com `FABER_GH=off`, o arquivo em disco é a fonte — aponte o path no chat).
5. **Batch no chat:** aponte para o comentário da issue (fonte única) + a frase
   de aprovação esperada: responda **"TASK-XXX validada"** (G6 aprovado — siga
   com `/faber-approve TASK-XXX G6`) ou **reprove com o motivo**.
6. **Se reprovar:** registre o motivo e regrida:
   `faber/scripts/transition.sh TASK-XXX in-development --motivo "<motivo do Owner>"`
   (as correções seguem o fluxo normal: dev → G3 → review → validação → G6).

Este comando **sempre para** no passo 5 — o G6 é humano, em qualquer modo de
interação.
