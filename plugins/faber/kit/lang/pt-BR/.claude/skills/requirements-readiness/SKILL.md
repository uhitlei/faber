---
name: requirements-readiness
description: Avaliar completude de um pacote de discovery, listar bloqueios e selar a revisão dos artefatos antes do G1. Use com requirements/ de uma demanda ou bootstrap; não substitui revisão semântica nem aprovação humana.
---

# Readiness de requisitos

Use `faber/templates/requirements/assessment.template.yaml` como rubrica.
As verificações e pesos são definidos em `faber/scripts/lib/requirements.py`.
`verified` precisa de justificativa e EVs; `partial` vale metade; `missing`
vale zero. N/A só é permitido em data/integrations com motivo e evidência;
remove seu peso do denominador. O script calcula a nota, nunca o agente.

```bash
python3 faber/scripts/requirements-gate.py report faber/tasks/TASK-XXX --write
```

Troque a pasta por `faber/bootstrap` no bootstrap. O exit 1 indica lacunas
ou estrutura inválida; leia todos os errors. Grave uma execução com a skill
evidence, preservando inclusive exit não zero quando o pacote ainda falha.
Não reclassifique uma lacuna para elevar a nota sem informação nova.

Gate: score real >=95, fontes obrigatórias cobertas, hashes atuais, requisitos
ativos validated/approved, referências e aceites presentes, zero pendência
blocker/high aberta. O programa verifica estrutura, não prova que uma citação
é fiel, uma regra é correta ou um aceite é bom. PO/QA revisam esses aspectos.

Depois de PO/QA, spec e refinamento concluídos:

```bash
python3 faber/scripts/requirements-gate.py seal faber/tasks/TASK-XXX
python3 faber/scripts/requirements-gate.py delivery faber/tasks/TASK-XXX
```

`seal` grava `requirements/delivery.json`; `delivery` recalcula e devolve o
hash do selo se válido. Nunca use seal para esconder divergência: reconcilie
as entradas e saídas antes. `gate-check.sh` verifica o selo em ready-for-dev
e nos avanços a partir de in-development; `gate-set.sh` vincula G1 ao hash quando o Owner o aprova.
O bootstrap registra o hash junto à aprovação humana do PRD/BRD.

Ao reportar, use “completude X/100 e N bloqueios”. Não use “X% de chance de
estar correto”. Nenhum destes comandos aprova G1 nem modifica gates humanos.
