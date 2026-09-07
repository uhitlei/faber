---
description: Pós-G6 — confere todos os gates, atualiza a branch com o trunk, consolida a descrição (o quê/por quê/como testar/risco/rollback) e cria a PR
argument-hint: TASK-XXX
---

# /faber-pr

Demanda: **$ARGUMENTS**

Executa o G7 e abre a PR (§12/§18-G7). Pré-condição: G6 aprovado por
@@FABER_OWNER_NAME@@ (via `/faber-approve`) e estado `ready-for-pr`. Merge da PR
(G8) é **sempre do Owner, no GitHub** — você nunca faz merge.

1. **Confira os gates** no `state.yaml`: G1–G6 `approved`/`not-applicable`
   (autoaprovação em gate humano é impossível — mas confira). Pendência →
   pare e reporte.
2. **Atualize a branch com o trunk** (na branch da demanda):
   `faber/scripts/evidence.sh TASK-XXX merge-trunk -- bash -c "git fetch origin @@FABER_TRUNK@@ && git merge --no-edit origin/@@FABER_TRUNK@@"`
   Conflitos: resolva respeitando o escopo da demanda; conflito que exige
   decisão de produto → `clarification` com o Owner.
3. **Sanidade pós-merge** (evidência real):
   `faber/scripts/evidence.sh TASK-XXX lint-pos-merge -- @@FABER_CMD_LINT@@`
   `faber/scripts/evidence.sh TASK-XXX build-pos-merge -- @@FABER_CMD_BUILD@@`
   `faber/scripts/evidence.sh TASK-XXX test-pos-merge -- @@FABER_CMD_TEST@@`
   Vermelho → corrija antes de prosseguir (ou regrida com motivo).
4. **Registre o G7:**
   `faber/scripts/gate-set.sh TASK-XXX G7 approved --by cto --evidence "evidence/NN-merge-trunk.log"`
5. **Push da branch** (autônomo — feature branch): `git push -u origin feature/TASK-XXX`
6. **Consolide a descrição da PR** lendo `spec.md`, `review.md`, `decisions.md`
   e `evidence/` — estrutura obrigatória (§18-G7):
   - **O quê** (escopo entregue, ACs) · **Por quê** (problema/valor)
   - **Como testar** (roteiro curto do G6)
   - **Risco & rollback** (do refinamento/migration-safe; migrations citadas)
   - **Evidências** (paths dos logs de lint/build/test/e2e/análise estática na
     pasta da demanda) · **Spec:** `faber/tasks/TASK-XXX/spec.md`
7. **Crie a PR:** `gh pr create --base @@FABER_TRUNK@@ --title "tipo(escopo): resumo (TASK-XXX)" --body "<descrição consolidada>"`
   (com `FABER_GH=off`: registre a descrição em `faber/tasks/TASK-XXX/pr.md`
   e use `--pr pr.md` na transição.)
8. **Transicione:** `faber/scripts/transition.sh TASK-XXX pr-open --pr "<url da PR>"`
9. **Reporte ao Owner:** link da PR + resumo de 3 linhas + lembrete de que o
   merge (G8) é dele; após o merge, siga o pós-G8 do `/faber-approve` (G9 → done).

Este comando **sempre para** no passo 9 — o G8 é humano, em qualquer modo de
interação.
