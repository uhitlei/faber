---
name: requirements-discovery
description: Extrair evidências de transcrições e documentos, estruturar requisitos e conduzir esclarecimentos para BRD/PRD na fábrica. Use antes do PO em discovery ou ao incorporar novas fontes a um pacote existente.
---

# Discovery de requisitos

Leia [o contrato](references/contract.md) ao criar ou atualizar o pacote.
Use os quatro templates em `faber/templates/requirements/`. Não copie um
template sobre trabalho existente. Leia fontes por partes quando necessário,
mantendo registro de cobertura; a economia de contexto não permite omitir
trechos silenciosamente.

1. Registre as fontes e os SHA-256 dos arquivos. Preserve speaker/timestamp
   se presentes; para anotações, use seção/linha. Nunca invente localização.
2. Extraia citações e classifique declaração, decisão ou inferência. Declaração
   não é automaticamente fato verificado; solução sugerida não é requisito aprovado.
3. Estruture contexto, objetivos, usuários, escopo, jornadas, regras, dados,
   qualidades, requisitos e dependências. Cada requisito tem ID estável,
   evidências e critérios de aceite; hipóteses e conflitos ficam explícitos.
4. Produza `requirements/BRD.md` e `requirements/PRD.md` conforme o guia de
   PRD/BRD do projeto. Cabeçalho: revisão, status rascunho/validado e origem
   `model.yaml`. PRD preserva todos os IDs ativos. Lacunas aparecem nos drafts.
5. Use `requirements-readiness`. Priorize perguntas que mudam regra, escopo,
   acesso, integração ou aceite. Cada pergunta informa origem, impacto e quem
   pode responder. Agrupe normalmente até cinco; ajuste ao contexto.
6. Respostas recebidas viram fontes de decisão em arquivo, com evidência;
   atualize os requisitos e resoluções afetados, incremente a revisão.
7. Quando completo, entregue ao CTO para PO e QA. Para a projeção de SDD,
   leia [Spec Kit](references/spec-kit.md). Não faça refinamento técnico.

Não preencha números, prazos, regras ou métricas por plausibilidade. Requisito
inferido permanece proposed até confirmação ou sustentação suficiente em
evidência explícita. `validated` significa reconciliado com as fontes e
verificável; `approved` exige decisão humana referenciada. A aprovação de
desenvolvimento pertence ao G1, mesmo se os requisitos estiverem validated.

Se novas fontes contradizem uma versão aprovada, registre a divergência,
preserve histórico no git e reabra o esclarecimento; não substitua decisões
silenciosamente. Sem informação nova, devolva a pendência ao CTO e respeite
o anti-loop existente.
