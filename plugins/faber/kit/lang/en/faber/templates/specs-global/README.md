# @@FABER_PROJECT@@ — Specs

Knowledge base **canônica** do projeto, no padrão RFC (uma `SPEC.md` densa por
feature + documentos globais transversais). Pensada para ser consumida por
agentes de IA e por humanos. Toda decisão técnica nova é refletida aqui antes
(ou imediatamente após) ser codificada — o `doc-writer` consolida no G9.

## Estrutura

```text
@@FABER_SPECS_DIR@@/
├── README.md               # este mapa
├── global/                 # docs transversais (00–08)
├── features/               # uma pasta por feature: NN-nome/SPEC.md (17 seções)
└── assets/diagrams/        # fontes .mmd (Mermaid) e renders
```

## Globais — leitura obrigatória para qualquer agente

| # | Documento | Quando ler |
|---|---|---|
| 00 | [Arquitetura](./global/00-ARCHITECTURE.md) | Sempre, antes de qualquer mudança |
| 01 | [Banco de Dados / Modelo de dados](./global/01-DATABASE.md) | Antes de tocar em dados, migrations, contratos de persistência |
| 02 | [Design System](./global/02-DESIGN-SYSTEM.md) | Antes de qualquer mudança visual |
| 03 | [Segurança](./global/03-SECURITY.md) | Antes de criar entidade, policy, endpoint ou integração |
| 04 | [Deploy & CI/CD](./global/04-DEPLOYMENT.md) | Antes de mexer em workflows ou ambientes |
| 05 | [Testes](./global/05-TESTING.md) | Antes de adicionar feature crítica |
| 06 | [Convenções de Código](./global/06-CONVENTIONS.md) | Sempre que escrever código novo |
| 07 | [Env & Secrets](./global/07-ENV-AND-SECRETS.md) | Configuração inicial e troca de ambiente |
| 08 | [Agent Playbook](./global/08-AGENT-PLAYBOOK.md) | **Primeira leitura para IAs/agentes** |

## Features

<!-- Preenchido pelo /faber-init (bootstrap) e mantido pelo doc-writer. -->
| # | Feature | Perfis | Status |
|---|---|---|---|
| 01 | [{{nome}}](./features/01-{{slug}}/SPEC.md) | {{perfis}} | {{Draft}} |

## Como o agente deve usar isto

1. Começar por `global/00-ARCHITECTURE.md` + `global/08-AGENT-PLAYBOOK.md`.
2. Para implementar/alterar uma feature, abrir `features/NN-<nome>/SPEC.md` e seguir os contratos antes de tocar no código.
3. Mudanças de dados só por migration nova (imutáveis); invariantes de segurança em `03-SECURITY.md` são intocáveis sem revisão do Owner.
