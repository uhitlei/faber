---
description: Registra aprovação de gate humano pelo Owner (G1/G6/G8) e destrava a transição correspondente
argument-hint: TASK-XXX <G1|G6|G8>
---

# /faber-approve

Argumentos: **$ARGUMENTS**

Este comando registra a decisão de **@@FABER_OWNER_NAME@@** — G1, G6 e G8 são
exclusivamente dele (CLAUDE.md §1). O CTO **jamais** executa `/faber-approve` por
iniciativa própria; se este comando foi digitado, foi o Owner quem aprovou.

1. Confirme na resposta qual gate está sendo aprovado e para qual demanda;
   se o argumento estiver ambíguo (sem gate ou sem TASK), pergunte.
2. Registre (mecânica por script, com autor `@@FABER_OWNER@@`):
   `faber/scripts/gate-set.sh TASK-XXX <gate> approved --by @@FABER_OWNER@@ --evidence "aprovação de @@FABER_OWNER_NAME@@ via /faber-approve em <data>"`
   (o H1 pede confirmação neste comando: confirmar o diálogo É a aprovação.)
3. Destrave a transição do fluxo (§5/§6.2):
   - **G1** → `faber/scripts/transition.sh TASK-XXX in-development`
   - **G6** → `faber/scripts/transition.sh TASK-XXX ready-for-pr`
   - **G8** (merge já feito pelo Owner no GitHub) → consolidação final:
     invoque o `doc-writer` (Skill `spec-sync`) para consolidar
     `@@FABER_SPECS_DIR@@/` a partir do trunk já mergeado — as mudanças de
     documentação vão numa branch `docs/TASK-XXX-specs` e viram uma PR de
     fechamento, porque `@@FABER_TRUNK@@` não recebe push direto (H1). Depois
     registre `gate-set.sh TASK-XXX G9 approved --by cto` e
     `transition.sh TASK-XXX done`.
     **Faxina obrigatória ao entrar em `done`:**
     `faber/scripts/worktree.sh clean TASK-XXX` — fecha o worktree e
     **apaga a branch da demanda**, local e remota. Fail-closed: recusa se a
     branch não estiver mergeada no trunk (exit 2). Se `FABER_SONAR=on`,
     apague também o espelho: `faber/scripts/sonar-task.sh delete TASK-XXX`.
4. Se o `gate-check` bloquear a transição, **não force**: reporte as
   pendências listadas e resolva-as primeiro.
5. Reporte o novo estado e a próxima ação do fluxo.

## Encadeamento (FABER_INTERACTION)

- **`gates`**: após **G1**, execute `/faber-develop TASK-XXX` e em seguida
  `/faber-validate TASK-XXX` sem parar (pare só no G6). Após **G6**, execute
  `/faber-pr TASK-XXX` (pare no G8). Após **G8**, conclua G9 → `done` → faxina.
- **`step-by-step`**: pare no passo 5 e aguarde o Owner chamar o próximo comando.

Gates do CTO (G2/G4/G5/G7/G9) **não** passam por `/faber-approve` — são registrados
no próprio fluxo com `gate-set.sh ... --by cto` e evidência.
