# 05 · Testes

## 1. Estratégia (pirâmide)

| Nível | Ferramenta | Comando | Onde |
|---|---|---|---|
| unitário | {{...}} | `@@FABER_CMD_TEST@@` | {{path}} |
| integração | {{...}} | {{...}} | {{path}} |
| E2E | {{Playwright / Cypress / n/a}} | `@@FABER_CMD_E2E@@` | {{path}} |

## 2. Como rodar

```bash
@@FABER_CMD_LINT@@
@@FABER_CMD_BUILD@@
@@FABER_CMD_TEST@@
@@FABER_CMD_E2E@@
```

## 3. Suíte E2E

- {{lista de specs e o que cada uma cobre}}
- Servidor/ambiente: {{como sobe; alvo SEMPRE local para seed/reset}}
- Evidência para o G5: `faber/scripts/evidence.sh TASK-XXX e2e -- @@FABER_CMD_E2E@@` (comando direto, sem pipe).

## 4. Padrões de estabilidade

1. Esperar por **estado**, não por tempo.
2. Seletores acessíveis (role/label) > seletores CSS.
3. Idempotência: cada teste cria seus dados ou usa seeds resetados.
4. Nada de `console.log` fora de modo debug.

## 5. Dados de teste

- {{seeds, factories, usuários de teste — como criar/resetar localmente}}

## 6. Cobertura

- Alvos atuais: {{informativos | bloqueantes por diretório}}
- Exceções a coverage só com decisão documentada do CTO (§18).

## 7. Como escrever um teste novo

- {{convenções de nome, pasta, helpers a reusar}}
