---
name: evidence
description: Gera evidência executada real (evidence/NN-*.log) para gates e handoffs da fábrica — todo comando de validação roda via faber/scripts/evidence.sh. Use sempre que um resultado de comando precisar virar evidência; evidência narrada é inválida.
---

# evidence — evidência executada, nunca narrada

Fonte: `faber/ARCHITECTURE.md` §11 (Skill), §15 (anti-"falsa alegação de
execução"), §17 (handoff sem evidência = inválido), R6 (2 MB).

## Regra de ouro

Evidência é o **arquivo gravado por execução real** — o `gate-check.sh`
confere o arquivo, não a sua narrativa. Output colado de memória, log editado
ou criado à mão = evidência inválida.

## Como usar

```
faber/scripts/evidence.sh <TASK-XXX> <slug> -- <comando> [args...]
```

- Pipelines/redirecionamentos: `... -- bash -c "@@FABER_CMD_LINT@@ 2>&1 | tail -50"`
  (exceção: o comando E2E `@@FABER_CMD_E2E@@` é chamado **direto**, sem pipe —
  ver Skill `e2e-runner`)
- O exit code do comando é **propagado** — encadeie:
  `evidence.sh TASK-XXX test-run -- @@FABER_CMD_TEST@@ && <próximo passo>`
- `NN` incrementa sozinho; o log sai em `evidence/NN-<slug>.log` com
  cabeçalho (comando, início, fim, duração, exit code) + output integral.

## Slugs convencionais

`lint`, `build`, `test-run`, `e2e`, `repro`, `teste-antes`, `teste-depois`,
`sonar`, `db-validacao` — descritivos e curtos. O gate G3 procura
`*lint*`/`*build*`/`*test*` em `evidence/` (gate-check).

## Regras complementares

1. **Ferramenta indisponível** (Sonar fora do ar, rede caída): rode o comando
   mesmo assim via `evidence.sh` — o log da falha É a evidência da
   indisponibilidade. Declare "não executado" no handoff; **jamais** inferir
   resultado (CLAUDE.md §4).
2. **Log > 2 MB** (R6): o script avisa — não commite; deixe o arquivo fora do
   commit e **referencie o caminho** (ou URL do relatório) no handoff.
3. Um comando = uma evidência. Validações distintas (lint, build, test) geram
   logs distintos — não agrupe num só.
4. Handoffs referenciam os paths dos logs em `evidence:` (§17); handoff sem
   evidência referenciada é rejeitado pelo gate-check.
