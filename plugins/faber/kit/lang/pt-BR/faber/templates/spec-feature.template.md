# Feature {{NN}} · {{Nome da feature}}

<!-- Template da SPEC CANÔNICA de feature (padrão RFC, 17 seções) — destino de
     `@@FABER_SPECS_DIR@@/features/NN-nome/SPEC.md`. Usado pelo /faber-init
     (bootstrap) e pelo doc-writer (spec-sync, G9). Proporcional: inclua só as
     seções aplicáveis; a seção 17 (CHANGELOG) é SEMPRE mantida. Remover os
     comentários ao preencher; nenhum {{...}} pode sobrar. -->

- **Status:** {{Draft | Beta | Stable | Deprecated}}
- **Owners:** {{profiles/áreas responsáveis}}
- **Rotas / pontos de entrada:** {{URLs, comandos, endpoints}}
- **Arquivos-chave:** {{paths principais no código}}

## 1. Resumo

{{Síntese executiva em 3–5 linhas: o que a feature faz e para quem.}}

## 2. Problema

{{Que dor resolve e por quê existe.}}

## 3. Personas

| Persona | Contexto de uso |
|---|---|
| {{perfil}} | {{...}} |

## 4. Requisitos

### 4.1 Funcionais
- **RF-01:** {{...}}

### 4.2 Não-funcionais
- **RNF-01:** {{performance, disponibilidade, acessibilidade, LGPD/privacidade…}}

## 5. Fluxos

```mermaid
flowchart LR
  A[{{início}}] --> B[{{passo}}] --> C[{{fim}}]
```

## 6. Arquitetura

{{Camadas, dependências, integrações externas; ponteiro para 00-ARCHITECTURE.}}

## 7. Modelo de dados

| Entidade/Tabela | Campos-chave | Autorização (RLS/ACL) |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

## 8. Contratos (APIs / RPCs / eventos)

| Operação | Entrada | Saída | Erros |
|---|---|---|---|
| {{...}} | {{...}} | {{...}} | {{...}} |

## 9. UI/UX

{{Rotas, componentes, estados (loading/vazio/erro/sucesso), responsivo, acessibilidade; ponteiro para 02-DESIGN-SYSTEM.}}

## 10. Regras de negócio

- **RN-1:** {{...}}

## 11. Edge cases

- {{cenário atípico → tratamento}}

## 12. Segurança

{{Riscos e mitigações específicas; invariantes de 03-SECURITY que esta feature toca.}}

## 13. Performance

{{Limites, paginação, caches, custos.}}

## 14. Testes

| Tipo | Cobertura | Onde |
|---|---|---|
| unitário | {{...}} | {{path}} |
| E2E | {{...}} | {{path}} |

## 15. Snippets críticos

```{{linguagem}}
{{trecho crítico atual, com path:linha}}
```

## 16. Open questions

- {{decisão pendente / dívida técnica — ou "nenhuma"}}

## 17. CHANGELOG

<!-- Convenção: `- <AAAA-MM-DD> · TASK-XXX — <o que mudou>`, mais recente no topo. -->
- {{AAAA-MM-DD}} · {{TASK-XXX | bootstrap}} — {{criação desta spec}}
