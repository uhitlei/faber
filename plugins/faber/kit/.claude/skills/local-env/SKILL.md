---
name: local-env
description: Opera o ambiente LOCAL descartável da fábrica — subir, resetar, aplicar migrations e seeds sintéticos, sempre via faber/scripts/local-env.sh (que delega aos comandos FABER_CMD_LOCAL_* do faber.env). Módulo opcional (FABER_LOCAL_ENV=on). Use para validações locais do senior-developer, do QA e do db-guardian; ambiente descartável com autonomia total (P4). Jamais toca alvo remoto.
---

# local-env — ambiente local descartável

Fonte: `faber/ARQUITETURA.md` §11, P4 (autonomia total no local — e somente
no local). Mecânica: `faber/scripts/local-env.sh` (nunca comandos soltos) —
cada subcomando delega ao comando configurado em `faber/config/faber.env`.
Módulo opcional: `FABER_LOCAL_ENV=on`.

## Comandos

| Ação | Comando | Delega a |
|---|---|---|
| Subir o stack | `faber/scripts/local-env.sh up` | `FABER_CMD_LOCAL_UP` |
| Estado | `faber/scripts/local-env.sh status` | `FABER_CMD_LOCAL_STATUS` |
| Recriar banco + todas as migrations | `faber/scripts/local-env.sh reset` | `FABER_CMD_LOCAL_RESET` |
| Seeds sintéticos | `faber/scripts/local-env.sh seed` | `FABER_CMD_LOCAL_SEED` |
| Parar | `faber/scripts/local-env.sh stop` | `FABER_CMD_LOCAL_STOP` |
| Relatório consolidado | `faber/scripts/local-env.sh report` | (gerado pelo script: estado + últimas ações) |

Validação que alimenta gate/handoff: rode via `evidence.sh` —
`faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`

## Regras

1. **Só local.** O script tem guard estrutural (recusa alvo que não seja
   `127.0.0.1`/`localhost`) e, por fora, o H1 nega refs/ambientes de produção
   (`FABER_REFS_DENY`) e pede confirmação para os remotos
   (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`). Banco remoto de
   qualquer ambiente: **nunca** por esta skill (§19).
2. **Ferramenta indisponível = não executado.** `FABER_LOCAL_ENV=off`,
   comando `FABER_CMD_LOCAL_*` vazio ou infra parada → o script falha com
   instrução; o log da falha (via `evidence.sh`) é a evidência da
   indisponibilidade. Registre **"não executado"** explícito no handoff — jamais
   infira que a migration/seed aplicaria (§15).
3. **Infra primeiro.** Dependência local parada (ex.: Docker) → `up` falha com
   instrução; peça a @@FABER_OWNER_NAME@@ para iniciá-la — não tente
   instalar/iniciar por conta própria.
4. **Seeds:** `seed` roda o comando configurado e pressupõe os pré-requisitos
   documentados em `@@FABER_SPECS_DIR@@/global/05-TESTING.md` (ex.: usuários
   de teste criados). Sem eles, o erro é esperado, não "flaky".
5. **Descartável de verdade:** quebrou, resete (`reset`); não conserte estado
   local à mão — o valor do ambiente é ser reproduzível pelas migrations.
