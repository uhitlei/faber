---
name: e2e-runner
description: Executa a suíte E2E do projeto (Playwright, Cypress ou equivalente — sempre pelo comando canônico @@FABER_CMD_E2E@@) com os padrões reais do projeto — execução seletiva por spec afetada, seeds idempotentes, esperas por estado — e captura o resultado como evidência. Use na validação do QA (estado `validation`). Jamais roda seed/reset destrutivo contra alvo remoto — só contra alvo LOCAL confirmado.
---

# e2e-runner — execução E2E com os padrões do projeto

Fonte: `@@FABER_SPECS_DIR@@/global/05-TESTING.md` (suíte, runner, comandos e
padrões de estabilidade) e a pasta de testes E2E do projeto. Usada pelo QA (§7,
§11) na validação. Módulo `FABER_E2E` em `faber/config/faber.env` (o G5
exige E2E executado quando `FABER_E2E=on` e a demanda tem impacto em UI).
Idioma: PT-BR (P6).

## Suíte e comandos reais (não invente flags)

- **Leia a suíte E2E real do projeto** em `05-TESTING.md` e na pasta de testes:
  quais specs existem, o que cada uma cobre, quais helpers de login/seed/
  navegação já existem. Nunca invente flags, projetos ou paths.
- **Comando canônico:** `@@FABER_CMD_E2E@@` (`FABER_CMD_E2E`). Execução
  **seletiva pela spec afetada** = o comando canônico seguido do path da spec,
  na forma que o runner do projeto aceita (ex.:
  `@@FABER_CMD_E2E@@ <pasta-e2e>/<feature>.spec.ts`).
- **Servidor:** se a configuração do runner sobe o servidor da aplicação
  sozinha, não suba outro à mão; se não sobe, siga o roteiro de
  `05-TESTING.md`. URL/porta são as do projeto — não as decore.
- **Relatório do runner** (HTML ou equivalente), se houver, complementa; a
  evidência de gate é o log com exit code.

## Evidência (alimenta o G5 — §18)

E2E verde é critério do G5. Rode **sempre via `evidence.sh`**, chamando o
comando canônico **DIRETO** — sem `bash -c`, sem pipe. O gate reconhece o
comando que executa pelo `FABER_E2E_CMD_REGEX` e o resultado pelo
`FABER_E2E_SUMMARY_REGEX`/`FABER_E2E_FAIL_REGEX`; um pipe esconde exit
code e sumário:

```bash
faber/scripts/evidence.sh TASK-XXX e2e -- @@FABER_CMD_E2E@@ <pasta-e2e>/<feature>.spec.ts
```

Runner/infra local indisponível = **"não executado"** explícito, jamais
"passou" inferido (§15).

## Padrões de estabilidade (05-TESTING — obrigatórios)

1. **Esperar por estado, não por tempo:** asserções que aguardam o
   elemento/estado (`toBeVisible`, `waitFor…`, `expect.poll` ou equivalentes do
   runner) — nunca espera fixa por tempo.
2. **Seletores acessíveis** (por papel/rótulo — `getByRole`/`getByLabel` ou
   equivalente) > seletores CSS (sobrevivem a refactor).
3. **Aguardar a resposta** das mutations críticas (ex.: `waitForResponse` no
   endpoint da mutation) antes de asserir.
4. **Idempotência:** cada teste cria seus dados ou usa seeds resetados antes do
   run; reaproveite os helpers do projeto, não reimplemente login.
5. Nova spec: siga a convenção de nome/pasta de `05-TESTING.md`, use os helpers
   do projeto, seed idempotente antes do `beforeAll`, logs de depuração só sob
   variável de ambiente de debug.

## Regra de segurança — alvo do E2E

**Seed/reset destrutivo só contra alvo LOCAL confirmado; alvo remoto → pare e
escale ao CTO.**

- **NUNCA** rode seed/reset destrutivo contra um alvo remoto por esta skill —
  um ambiente compartilhado pode ser zerado. Precisa semear/resetar com
  escrita? Use o **ambiente local descartável** (Skill `local-env`, P4).
- Rodar a suíte E2E (leitura + fluxos de UI) é aceitável; se um teste exigir
  escrita de dados, confirme que o alvo é local **antes** — na dúvida, **pare**.
  Refs/ambientes de produção (`FABER_REFS_DENY`) e remotos que exigem
  confirmação (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`): jamais por
  aqui (§19, H1).
