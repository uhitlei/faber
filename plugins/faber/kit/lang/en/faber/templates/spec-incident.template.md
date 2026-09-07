# Spec — {{TASK-XXX}}: incidente — {{título}}

<!-- Template: INCIDENTE (ARQUITETURA §14). Fluxo rápido com @@FABER_OWNER_NAME@@ síncrono:
     contenção → diagnóstico → fix → post-mortem. O POST-MORTEM VIRA A SPEC.
     NADA de correção direta em PROD (H1): o fix segue o pipeline normal. -->

| Campo | Valor |
|---|---|
| Demanda | {{TASK-XXX}} |
| Tipo | incident |
| Severidade | {{SEV1 total \| SEV2 degradado \| SEV3 pontual}} |
| Início / fim do impacto | {{AAAA-MM-DDTHH:MM}} → {{...}} |

## 1. Linha do tempo

<!-- Registrar em tempo real, com horários. Fatos, não suposições. -->
| Hora | Evento |
|---|---|
| {{HH:MM}} | {{detecção: como o problema foi percebido}} |
| {{HH:MM}} | {{...}} |

## 2. Contenção aplicada

<!-- Ação imediata para estancar o impacto (e evidência). Contenção NÃO é o
     fix definitivo. -->
{{...}}

## 3. Diagnóstico (causa raiz)

<!-- O que quebrou e por quê; evidências em evidence/. -->
{{...}}

## 4. Fix definitivo

<!-- Escopo do conserto permanente — segue o pipeline (feature branch → PR →
     @@FABER_TRUNK@@ → @@FABER_MAIN@@). Gates comprimidos com @@FABER_OWNER_NAME@@ síncrono (§14). -->
{{...}}

## 5. Post-mortem

<!-- Sem culpados; foco em processo. Este bloco é o coração da spec. -->
- **O que falhou:** {{...}}
- **O que funcionou:** {{...}}
- **Onde tivemos sorte:** {{...}}
- **Ações preventivas:** <!-- cada uma vira demanda filha se não for trivial -->
  - {{...}}

## 6. Demandas filhas geradas

- {{TASK-YYY: … ou "nenhuma"}}
