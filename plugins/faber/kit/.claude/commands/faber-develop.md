---
description: Fluxo de desenvolvimento pós-G1 — implementação (senior-developer), G3, diff congelado, review de contexto limpo, G4 e validação técnica G5 (QA ∥ db-guardian ∥ devsecops)
argument-hint: TASK-XXX
---

# /faber-develop

Demanda: **$ARGUMENTS** — pré-condição: estado `in-development` (G1 aprovado
por @@FABER_OWNER_NAME@@ via `/faber-approve`).

Este comando encoda a coreografia entre o G1 e o `/faber-validate`. Mecânica sempre
pelos scripts — nunca manual. Trabalhe no worktree da demanda.

0. **Revisão aprovada:** execute `faber/scripts/gate-check.sh TASK-XXX in-development`
   antes de invocar o developer, mesmo em retomada do mesmo estado. Se discovery
   mudou desde G1, o gate bloqueia: reconciliar e renovar aprovação antes de continuar.

1. **Implementação:** invoque o subagente `senior-developer` (Modo 2) com o
   contrato mínimo — paths de `spec.md` + `refinamento.md` da demanda, nunca o
   dump do projeto. O handoff dele é validado pelo H5 (e conta em
   `invocacoes`; anti-loop §15).

2. **Developed + G3:**
   - `faber/scripts/transition.sh TASK-XXX developed`
     (o gate-check exige os logs de lint/build/test em `evidence/`);
   - `faber/scripts/gate-set.sh TASK-XXX G3 aprovado --por gate-check --evidencia "evidence/<NN>-test-run.log"`
     — G3 é do `gate-check` (§18); o registro **espelha** a liberação da
     transição, com o NN real do log de teste.

3. **Push + diff congelado:**
   - `git push -u origin feature/TASK-XXX` (o destino `code-review` exige a
     branch no remoto — e o push dispara o CI da branch, usado no passo 6);
   - `faber/scripts/evidence.sh TASK-XXX diff -- bash -c "git fetch -q origin @@FABER_TRUNK@@ && git diff origin/@@FABER_TRUNK@@...HEAD"`

4. **Review de contexto limpo:**
   - `faber/scripts/transition.sh TASK-XXX code-review`;
   - invoque `code-reviewer` com **apenas**: `spec.md`, o path do diff
     congelado e as seções citadas de `06-CONVENTIONS`/`03-SECURITY`. Nada de
     handoffs do dev ou narrativa da implementação (contamina).

5. **G4:** se o veredicto for `bloqueado` → espelhe as tarefas de correção na
   issue e regrida: `faber/scripts/transition.sh TASK-XXX in-development --motivo "review: <resumo>"`
   (correções voltam por este mesmo fluxo). Senão:
   - `faber/scripts/gate-set.sh TASK-XXX G4 aprovado --por cto --evidencia "review.md"`
   - `faber/scripts/transition.sh TASK-XXX validation`

6. **G5 — validações paralelas** (§5): dispare numa mesma rodada
   - `qa` (Modo 2): ACs + regressão; E2E via Skill `e2e-runner` quando
     `impacto_ui: true` (evidência do comando **direto**, sem pipe);
   - `db-guardian` (Modo 2) se a demanda toca banco;
   - `devsecops` (Papel 2): Sonar via Skill `sonar-gate` se `FABER_SONAR=on`;
     senão CI da branch: `faber/scripts/evidence.sh TASK-XXX ci-branch -- gh run list --branch feature/TASK-XXX --limit 3`
     e `... ci-run -- gh run view <run-id>`.
   Critério: tudo verde **ou exceção formal documentada** (Medium/Low, coverage —
   Critical/High jamais). "Não executado" jamais vira aprovado (CLAUDE.md §4).
   - Verde → `faber/scripts/gate-set.sh TASK-XXX G5 aprovado --por cto --evidencia "evidence/<NN>-<slug>.log"`
   - Vermelho → regrida com motivo (`in-development`) e volte ao passo 1.

7. **Siga para `/faber-validate TASK-XXX`** — o G6 é de @@FABER_OWNER_NAME@@.

## Encadeamento (FABER_INTERACTION)

- **`gates`**: execute 1–7 sem parar, inclusive o `/faber-validate`; pare só no G6.
- **`step-by-step`**: pare após o G3, após o G4 e após o G5, aguardando ok.
