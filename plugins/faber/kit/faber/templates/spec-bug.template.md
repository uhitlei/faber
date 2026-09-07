# Spec — {{TASK-XXX}}: {{título do bug}}

<!-- Template: BUG (ARQUITETURA §14). Spec reduzida DE PROPÓSITO (§11):
     reprodução + causa raiz + fix + teste de regressão. Não inchar.
     REGRA DE OURO: sem reprodução registrada com evidência, a spec não
     avança (§14 — "reprodução obrigatória antes da spec"). -->

| Campo | Valor |
|---|---|
| Demanda | {{TASK-XXX}} |
| Tipo | bug |
| Severidade | {{crítica \| alta \| média \| baixa}} |
| Data | {{AAAA-MM-DD}} |

## 1. Reprodução (obrigatória)

<!-- Passos exatos executados, com evidência REAL gravada em evidence/
     (log, screenshot). Evidência narrada = inválida (§15). -->
- Ambiente: {{local/homologação + browser/dispositivo}}
- Perfil/usuário: {{perfil de usuário}}
- Passos:
  1. {{...}}
- **Evidência da reprodução:** {{evidence/NN-repro.log}}

## 2. Comportamento esperado × observado

- **Esperado:** {{...}}
- **Observado:** {{...}}

## 3. Causa raiz

<!-- Diagnóstico técnico: arquivo/função/query. "Não sei ainda" → investigar
     antes de fechar a spec, ou converter em spike (§14). -->
{{...}}

## 4. Fix proposto

<!-- Escopo mínimo do conserto. Mudança de comportamento além do conserto =
     outra demanda. -->
{{...}}

## 5. Teste de regressão

<!-- Obrigatório (§14): teste que FALHA antes do fix e PASSA depois.
     Indicar o arquivo de teste e as duas execuções como evidência. -->
- Teste: {{caminho do teste unitário | caminho do teste E2E}}
- Evidência "falha antes": {{evidence/NN-teste-antes.log}}
- Evidência "passa depois": {{evidence/NN-teste-depois.log}}

## 6. Riscos e impacto colateral

- {{... ou "nenhum identificado"}}

## 7. Dúvidas abertas

- {{... ou "nenhuma"}}
