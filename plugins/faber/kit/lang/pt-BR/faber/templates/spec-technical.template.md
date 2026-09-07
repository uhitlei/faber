# Spec — {{TASK-XXX}}: {{título}}

<!-- Template: TÉCNICA (tipos: debito-tecnico, infra, seguranca, banco,
     documentacao — ARQUITETURA §14). PO é pulado: CTO ou senior-developer
     especifica. Proporcionalidade (§11): preencher no nível do risco real —
     documentação simples pode ter seções curtas; banco/segurança, nunca.
     Notas por tipo:
     · seguranca — tratamento discreto: NÃO detalhar exploit em issue pública;
       devsecops lidera; db-guardian se houver dados.
     · banco — db-guardian participa DESDE o refinamento; migration-safe
       obrigatória; migrations imutáveis (H2).
     · infra — TODO diff em .github/workflows/ exige revisão explícita de
       @@FABER_OWNER_NAME@@ (H2/§19).
     · documentacao — direto ao doc-writer; gate único = review do CTO. -->

| Campo | Valor |
|---|---|
| Demanda | {{TASK-XXX}} |
| Tipo | {{debito-tecnico \| infra \| seguranca \| banco \| documentacao}} |
| Autor | {{cto \| senior-developer \| devsecops}} |
| Data | {{AAAA-MM-DD}} |

## 1. Motivação

<!-- Por que este trabalho técnico precisa acontecer; custo de NÃO fazer. -->
{{...}}

## 2. Estado atual → estado desejado

- **Hoje:** {{...}}
- **Depois:** {{...}}

## 3. Plano técnico

<!-- Passos objetivos; arquivos/módulos prováveis (o diff final é comparado
     a isto — §15). Para banco: migrations previstas, RLS/GRANT afetados. -->
1. {{...}}

## 4. Critérios de validação

<!-- Numerados AC-1… verificáveis por comando/teste. Base do G5. -->
- **AC-1:** {{comando/teste → resultado esperado}}

## 5. Impactos e segurança

| Área | Impacta? | Detalhe |
|---|---|---|
| Pipeline/workflows (revisão de @@FABER_OWNER_NAME@@ se `.github/workflows/`) | {{sim/não}} | {{...}} |
| Secrets (sempre por NOME, ex.: `API_TOKEN`) | {{sim/não}} | {{...}} |
| Banco/RLS (db-guardian; `01-DATABASE`) | {{sim/não}} | {{...}} |
| Superfície de segurança (`03-SECURITY`) | {{sim/não}} | {{...}} |

## 6. Riscos e rollback

- **Riscos:** {{...}}
- **Rollback:** {{como desfazer com segurança; para banco, plano reverso da
  migration (migration-safe)}}

## 7. Dúvidas abertas

- {{... ou "nenhuma"}}
