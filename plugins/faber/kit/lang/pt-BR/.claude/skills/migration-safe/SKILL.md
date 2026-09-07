---
name: migration-safe
description: Cria migrations seguras do padrão da fábrica para bancos relacionais — template com os termos exigidos pelo hook H3 (FABER_MIGRATION_CHECKS; ex. GRANT+RLS+policy+trigger+search_path), análise de destrutividade obrigatória e rollback reverso documentado. Use SEMPRE que uma demanda alterar o banco (tipo banco, ou impacto em dados detectado). Migrations aplicadas são imutáveis.
---

# migration-safe — migrations seguras e imutáveis

Fonte: `faber/ARQUITETURA.md` §11, §13-H2/H3, §19; specs
`@@FABER_SPECS_DIR@@/global/01-DATABASE.md` (modelo/regras de acesso — leia
por seção) e `03-SECURITY.md` (seção *Invariantes intocáveis*). Template:
`faber/templates/migration.template.sql` (Postgres com RLS como exemplo —
adapte ao banco do projeto). Migrations vivem em `@@FABER_MIGRATIONS_DIR@@/`
(`FABER_MIGRATIONS_DIR`; vazio = módulo desligado).

## Procedimento

1. **Timestamp novo, sempre:** `date +%Y%m%d%H%M%S` →
   `@@FABER_MIGRATIONS_DIR@@/<timestamp>_<slug>.sql`. Timestamp já existente
   no histórico = H2 nega (imutabilidade); jamais edite migration aplicada —
   correção é **nova migration corretiva**.
2. **Parta do template** e preencha todos os `{{...}}`; seção não aplicável
   (ex.: sem trigger) é removida **e registrada na análise** do cabeçalho.
3. **Análise de destrutividade (obrigatória, no cabeçalho):**
   - Aditivo (`create table/index/policy`, `add column nullable`): seguro.
   - Destrutivo (`drop`, `alter column type`, `rename`, `delete`,
     `truncate`, `add column not null` sem default): exige detalhar dados
     afetados, compatibilidade com o código em produção (deploy não é
     atômico com o CI) e plano de mitigação. Na dúvida → `clarification`.
4. **Rollback reverso:** bloco comentado ao final do arquivo com os comandos
   que desfazem a mudança — nunca executado ali; vira migration corretiva se
   necessário.
5. **Invariantes do projeto** (o hook H3 valida a presença dos termos listados
   em `FABER_MIGRATION_CHECKS`; §13-H3). No exemplo Postgres/RLS:
   - `search_path` fixado em toda função (`set search_path = public`);
   - controle de acesso por linha (RLS) habilitado em toda tabela nova +
     policies por perfil;
   - GRANTs mínimos (nunca `grant all`; papel anônimo só com exigência da spec);
   - **as invariantes de segurança declaradas em `03-SECURITY.md` (seção
     *Invariantes intocáveis*) não mudam sem revisão explícita de
     @@FABER_OWNER_NAME@@** (§19).
6. **Teste local antes do handoff** (Skill `local-env`):
   `faber/scripts/evidence.sh TASK-XXX reset-local -- faber/scripts/local-env.sh reset`
   (aplica todas as migrations do zero — a evidência do reset verde é o
   critério objetivo de que a migration é aplicável; ambiente local
   indisponível = "não executado" explícito).
7. **Aplicação remota é do CI** (pipeline no merge). Ambientes remotos que
   exigem confirmação (`FABER_REFS_CONFIRM` / `FABER_CMDS_CONFIRM`): só
   com confirmação explícita de @@FABER_OWNER_NAME@@, por execução;
   refs/ambientes de produção (`FABER_REFS_DENY`) — nunca por agente (H1).
