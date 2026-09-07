# 06 · Convenções de Código

## 1. Linguagem e configuração

- {{versão da linguagem; modo estrito; linter/formatter e config}}

## 2. Naming

| Item | Convenção |
|---|---|
| Arquivos | {{...}} |
| Funções/métodos | {{...}} |
| Tipos/classes | {{...}} |
| Constantes | {{...}} |
| Banco (tabelas/colunas) | {{...}} |
| Eventos/telemetria | {{...}} |

## 3. Estrutura de módulos

- {{onde vive cada tipo de código; regras de import; limites de tamanho}}

## 4. Padrões obrigatórios

- {{tratamento de erros; logging; validação de entrada; acesso a dados}}

## 5. Padrões proibidos

- {{`any` sem justificativa; segredos em código; cores hardcoded; …}}

## 6. Commits e branches

- Commits: `tipo(escopo): descrição` (`feat|fix|chore|docs|test|refactor|perf|style|ci|build|revert`), referenciando `TASK-XXX` quando na branch de demanda (hook H4).
- Branches: `feature/TASK-XXX` (demandas) · `docs/TASK-XXX-specs` (consolidação pós-merge).

## 7. Revisão de código — o que o reviewer confere

- Aderência à spec (AC por AC) · segurança (03) · convenções (este doc) · código mínimo (escada da preguiça: repo → stdlib → dependência instalada → código novo) · testes · bordas · performance · regressão.
