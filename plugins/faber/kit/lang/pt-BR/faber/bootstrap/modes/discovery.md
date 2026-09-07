# Modo discovery — transcrições, notas e documentos de cliente

Seleção explícita: `/faber-init --mode discovery` ou instalação `--mode discovery`.
O CTO identifica os paths fornecidos pelo usuário e confirma apenas o escopo
que não puder inferir deles. Nenhuma exigência de reunião real para instalar o kit.

1. Use `faber/bootstrap/requirements/`. Invoque business-analyst com fontes
   e escopo do produto; ele usa as duas skills de requirements. Estado e
   pendências ficam em CONTEXT.md/PERGUNTAS.md, sem inventar uma TASK.
2. Produza BRD/PRD e projeção SDD; registre cobertura das fontes. Lacunas
   bloqueantes geram perguntas antes de qualquer especificação técnica.
3. PO/QA revisam a especificação de negócio e o BA reconcilia o modelo.
   Score >=95 e zero bloqueios: selo por requirements-gate.py seal.
4. Parada de aprovação do PRD/BRD já existente no bootstrap: apresente os
   paths, dúvidas restantes não críticas e completude. Registre a decisão do
   Owner, data e hash de `requirements-gate.py delivery` em CONTEXT.md.
   Antes de continuar, verifique que o hash ainda corresponde ao aprovado.
5. Continue nas etapas 2–5 do modo prd, consumindo as projeções em requirements
   (não crie cópias divergentes em docs). Preserve REQ/AC IDs nas features e
   no backlog. Demandas futuras importam apenas o subconjunto relevante,
   conservam IDs e origem e geram seu próprio selo/G1.
6. Siga encerramento do faber-init. Sem criar issues automaticamente no bootstrap.

Áudio bruto é inventário pendente de transcrição, não fonte textual analisada.
Não configure serviço de transcrição nem instale Spec Kit nesse fluxo.
