# 04 · Deploy & CI/CD

## 1. Ambientes

| Ambiente | Branch/gatilho | URL/ref | Quem promove |
|---|---|---|---|
| local | — | 127.0.0.1 | agente (autônomo) |
| {{homologação}} | `@@FABER_TRUNK@@` | {{...}} | CI |
| produção | `@@FABER_MAIN@@` | {{...}} | @@FABER_OWNER_NAME@@ / CI |

## 2. Estratégia de branches

`feature/TASK-XXX → PR → @@FABER_TRUNK@@ → @@FABER_MAIN@@` (promoção). Merge de PR é sempre humano (G8).

## 3. Pipeline (CI)

| Job | Gatilho | O que valida |
|---|---|---|
| {{build-and-test}} | {{push/PR}} | {{lint, build, testes}} |

Workflows em `.github/workflows/` — edição exige tarefa DevSecOps aprovada (H2 / `workflow-unlock.sh`).

## 4. Deploy

- {{como o artefato é construído e publicado; passos manuais, se houver}}

## 5. Migrations em deploy

- {{quem aplica, quando, e o que acontece se falhar}}

## 6. Rollback

- {{procedimento por camada: aplicação, banco, infra}}

## 7. Observabilidade

- {{logs, métricas, alertas, health checks}}

## 8. Secrets por ambiente

- Nomes (nunca valores): `{{VAR_1}}`, `{{VAR_2}}` — ver 07-ENV-AND-SECRETS.

## 9. Custos e limites

- {{quotas, planos, limites de execução}}

## 10. Checklist pré-merge (DoD baseline)

- [ ] `@@FABER_CMD_LINT@@` · `@@FABER_CMD_BUILD@@` · `@@FABER_CMD_TEST@@` verdes (evidências na demanda)
- [ ] E2E executado quando `ui_impact: true`
- [ ] Migration revisada (destrutividade + rollback) quando houver
- [ ] Variáveis de ambiente novas declaradas nos ambientes afetados
- [ ] CHANGELOG da feature atualizado
