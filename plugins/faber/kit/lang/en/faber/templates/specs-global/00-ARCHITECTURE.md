# 00 · Arquitetura

<!-- Gerado/preenchido pelo /faber-init a partir do contexto detectado
     (repo existente: lido do código; spec-kit/PRD/brainstorm: proposto e
     marcado [PROPOSTA] até o Owner confirmar). Nenhum {{...}} pode sobrar. -->

> **Stack:** {{linguagens · frameworks · banco · infra · CI/CD}}
> **Perfis de usuário:** {{ex.: usuário, gestor, admin — ou "n/a" para libs/CLIs}}

## 1. Visão de contexto (C4 nível 1)

```mermaid
flowchart LR
  U[{{Usuário}}]:::user --> App[{{Sistema}}]
  App --> Ext[{{Integrações externas}}]:::ext
  classDef user fill:#0ea5e9,stroke:#0369a1,color:#fff
  classDef ext fill:#475569,stroke:#1e293b,color:#fff
```

## 2. Camadas e organização do código

```text
{{árvore de diretórios comentada — o que vive em cada pasta}}
```

## 3. Componentes e responsabilidades

| Componente | Responsabilidade | Depende de |
|---|---|---|
| {{...}} | {{...}} | {{...}} |

## 4. Fluxos principais

{{2–4 fluxos ponta a ponta (sequência) — Mermaid `sequenceDiagram` quando ajudar.}}

## 5. Decisões arquiteturais (ADRs resumidos)

| # | Decisão | Motivo | Consequências |
|---|---|---|---|
| ADR-1 | {{...}} | {{...}} | {{...}} |

## 6. Limites e restrições

- {{limites de plataforma, quotas, latência, tamanho de payload…}}

## 7. Glossário

- **{{termo}}:** {{definição}}
