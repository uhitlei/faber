# 01 · Banco de Dados / Modelo de dados

<!-- Se o projeto não tem persistência própria, escreva "não se aplica" na
     seção 1 e remova o resto. Fonte: migrations em FABER_MIGRATIONS_DIR
     (repo existente) ou o PRD/specs (proposta). -->

## 1. Visão geral

- **SGBD / serviço:** {{Postgres, MySQL, SQLite, Mongo, DynamoDB…}}
- **Migrations:** `{{FABER_MIGRATIONS_DIR}}` — imutáveis depois de aplicadas (H2); correção = nova migration.
- **Autorização em dados:** {{RLS por linha | ACL na aplicação | n/a}}

## 2. Diagrama ER

```mermaid
erDiagram
  {{ENTIDADE_A}} ||--o{ {{ENTIDADE_B}} : "{{relação}}"
```

## 3. Entidades

| Entidade/Tabela | Propósito | Campos-chave | Índices | Autorização |
|---|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} | {{...}} |

## 4. Funções / procedures / RPCs

| Nome | Entrada → Saída | Segurança (invoker/definer) | Observações |
|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} |

## 5. Regras de integridade e triggers

- {{...}}

## 6. Convenções

- Nomes: {{snake_case…}}; timestamps: {{timestamptz}}; ids: {{uuid}}.
- Toda entidade nova: {{RLS/ACL habilitada + GRANTs mínimos + índice nas FKs}}.

## 7. Dados de teste / seeds

- {{como os seeds são gerados; idempotência; onde vivem}}
