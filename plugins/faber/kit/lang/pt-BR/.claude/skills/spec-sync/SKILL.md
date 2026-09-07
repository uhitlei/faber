---
name: spec-sync
description: Consolida a spec de uma demanda concluída em @@FABER_SPECS_DIR@@/ no padrão RFC (17 seções) — atualiza a SPEC.md da feature, o CHANGELOG e os diagramas .mmd, sem duplicar conteúdo. Use no doc-writer, no Done (G9). Merge, nunca cópia.
---

# spec-sync — consolidação canônica em @@FABER_SPECS_DIR@@/

Fonte: `faber/ARQUITETURA.md` §11, §15 (merge **nunca** duplicação); estrutura
canônica `@@FABER_SPECS_DIR@@/features/NN-nome/SPEC.md` (`FABER_SPECS_DIR`).
Idioma PT-BR (P6).

## Onde consolidar

| Impacto da demanda | Destino canônico |
|---|---|
| Feature existente | `@@FABER_SPECS_DIR@@/features/NN-nome/SPEC.md` |
| Banco / segurança / deploy… | a global correspondente em `@@FABER_SPECS_DIR@@/global/` |
| Fluxo/modelo que mudou | fonte `.mmd` em `@@FABER_SPECS_DIR@@/assets/diagrams/` (+ `.png` render) |

## Padrão RFC (ordem canônica — proporcional)

Use esta ordem; **inclua só as seções aplicáveis** (a feature mais completa do
projeto pode usar as 16 primeiras; bug/técnica usam bem menos). A **seção 17
(CHANGELOG) é sempre criada/atualizada** quando uma demanda toca a feature.

1. Resumo · 2. Personas · 3. Requisitos funcionais · 4. Requisitos não-funcionais ·
5. Fluxos · 6. Modelo de dados · 7. RPCs · 8. UI/UX · 9. Regras de negócio detalhadas ·
10. Edge cases · 11. Segurança · 12. Performance · 13. Testes · 14. Snippets críticos ·
15. Open questions · 16. Referências · **17. CHANGELOG**.

## Como consolidar (merge, nunca duplicação — §15)

1. Leia a `spec.md`, o `decisions.md` e as evidências da demanda + a SPEC.md atual da
   feature.
2. **Atualize as seções afetadas** da SPEC.md canônica — reescreva o trecho que mudou,
   **não** anexe um bloco novo paralelo. Regra de negócio que virou verdade nova
   **substitui** a antiga.
3. **CHANGELOG (seção 17):** adicione uma entrada `- <data> · TASK-XXX — <o que mudou>`
   (mais recente no topo). É o histórico rastreável da feature.
4. **Diagramas:** se fluxo/modelo mudou, atualize o `.mmd` correspondente (fonte); **não**
   edite o `.png` à mão (é render). Diagrama novo → `assets/diagrams/NN-nome.mmd`.
5. **Glossário / Open questions:** promova termos novos; **feche** as open questions que
   a demanda resolveu.
6. Consolide **só o que está registrado** (decisões, evidências) — dúvida vai para Open
   questions, nunca se preenche de cabeça.
