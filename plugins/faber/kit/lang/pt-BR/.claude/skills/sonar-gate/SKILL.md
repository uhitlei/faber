---
name: sonar-gate
description: Módulo opcional (FABER_SONAR=on). Publica a análise da branch da demanda num projeto-espelho do Sonar (sonar-task.sh) e consulta as issues Critical/High dela (sonar-gate.sh, via SONAR_TOKEN/SONAR_HOST_URL por nome) para formar a evidência do G5. Use na validação (devsecops/CTO). API indisponível, projeto sem análise ou análise de outro commit vira "não executado", jamais inferido. Critical/High nunca é excepcionável.
---

# sonar-gate — Critical/High do Sonar como evidência

Fonte: `faber/ARCHITECTURE.md` §11, §18-G5, §21-R3; `07-ENV-AND-SECRETS` §4.
Mecânica determinística: `faber/scripts/sonar-task.sh` +
`faber/scripts/sonar-gate.sh` (zero LLM). **Módulo opcional:** só vale com
`FABER_SONAR=on` e `FABER_SONAR_PROJECT_KEY` preenchido em
`faber/config/faber.env`; desligado → registre "Sonar não configurado — não
executado" (o devsecops valida pelo CI da branch). PT-BR (P6).

## Como usar (dois passos)

Rodar o scanner de uma feature branch contra o projeto do trunk
(`$FABER_SONAR_PROJECT_KEY`) **sobrescreveria o trunk** com código não
mergeado (servidores sem análise multi-branch). Por isso a demanda é medida num
**projeto-espelho** `<PROJECT_KEY>-TASK-XXX`, publicado **localmente**: o CI
continua analisando só o trunk, em push a `@@FABER_TRUNK@@`/`@@FABER_MAIN@@`.

```bash
# 1. publica a análise da branch no espelho (gera cobertura, escaneia e ESPERA
#    o servidor processar; falha fechada em qualquer erro)
faber/scripts/evidence.sh TASK-XXX sonar-analise -- \
  faber/scripts/sonar-task.sh TASK-XXX

# 2. veredito sobre o espelho, com a catraca contra o trunk
faber/scripts/evidence.sh TASK-XXX sonar -- \
  faber/scripts/sonar-gate.sh --project "${FABER_SONAR_PROJECT_KEY}-TASK-XXX" \
    --branch feature/TASK-XXX --baseline "$FABER_SONAR_PROJECT_KEY"

# 3. no G9, apague o espelho (faxina)
faber/scripts/sonar-task.sh delete TASK-XXX
```

O passo 1 é obrigatório antes do passo 2: o gate **recusa** (exit 3) uma análise
cuja `revision` não seja o commit local avaliado — veredito só vale para o
código que foi analisado.

Uso direto no trunk: `sonar-gate.sh @@FABER_TRUNK@@` — mede a branch do
projeto `$FABER_SONAR_PROJECT_KEY` e exige que o ref local
`refs/heads/@@FABER_TRUNK@@` seja o commit analisado.

## Saída parseável

`PROJECT`, `BRANCH`, `MODO`, `ANALISE`, `REVISION`, `REVISAO_CONFERIDA`,
`QUALITY_GATE`, `CRITICAL_LEGACY`, `HIGH_IMPACTO`, `CRITICAL_HIGH`,
`BASELINE_*`, `NOVAS_VS_BASELINE`, `NOVA=` (uma por issue nova), `CATRACA`,
`MOTIVO`, `VEREDITO` (`approved` | `rejected` | `nao-executado`) + exit code
(`0` | `2` | `3`).

- `CRITICAL_LEGACY` = modelo **legacy** (`BLOCKER,CRITICAL`);
  `HIGH_IMPACTO` = modelo de **impacto** (`BLOCKER,HIGH`);
  `CRITICAL_HIGH` = a **união** dos dois (por chave de issue, não soma nem max).

## Interpretação (§18-G5)

- **aprovado** (exit 0) = `CRITICAL_HIGH=0`, ou `NOVAS_VS_BASELINE=0` quando a
  catraca está ligada (dívida herdada, toda ela já no trunk). O
  `QUALITY_GATE` é **informativo**: ele reprova por hotspots por revisar e por
  New Code Period indefinido, que não é a regra pedida — não bloqueia o G5.
- **reprovado** (exit 2) = há Critical/High **novo** (as linhas `NOVA=` dizem
  `regra|arquivo|hash`), ou qualquer Critical/High quando não há catraca →
  **jamais excepcionável** (§2, §19). Medium/Low → registrados; exceção só com
  **decisão do CTO documentada** em `decisions.md`.
- **nao-executado** (exit 3) = token/host ausente, API off, projeto sem análise,
  **análise de outro commit**, dado inconsistente (união menor que as contagens
  da API), parâmetro fora do padrão → registre "não executado" explícito;
  **nunca** infira "passou" (§15). O G5 fica pendente no eixo Sonar.

## Regras

1. `SONAR_TOKEN` e `SONAR_HOST_URL` entram **por nome**, via env da sessão ou
   do arquivo local não versionado apontado por `SONAR_ENV_FILE` (P2); nunca em
   arquivo versionado, nunca logados. Nenhum dos dois scripts imprime o valor
   de qualquer um deles.
2. A Skill só **consulta e publica análise**; **não** configura o pipeline.
   Alterar o job do Sonar em `.github/workflows/` exige tarefa DevSecOps
   aprovada (H2).
3. Escopo e cobertura vêm de `sonar-project.properties` (o `sonar-task.sh` só
   sobrescreve a identidade do espelho). A versão do scanner é **fixa** no
   script e sai na evidência (`SCANNER=`).
4. O baseline da catraca é o trunk (`$FABER_SONAR_PROJECT_KEY`) **lido na
   hora** — nunca um número escrito à mão. Ele envelhece se o CI do trunk parar
   de rodar.
