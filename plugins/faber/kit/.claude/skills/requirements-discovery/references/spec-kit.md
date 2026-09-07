# Projeção para Spec-Driven Development

Saída de negócio: `requirements/speckit/spec.md`. Preserve REQ/AC IDs.
Inclua revisão do modelo, objetivo, usuários, jornadas priorizadas, requisitos,
cenários de aceite, exceções, critérios de sucesso e dúvidas remanescentes.
Use o template real `.specify/templates/spec-template.md` quando existir.
Sem Spec Kit instalado, use essas seções em Markdown e registre no cabeçalho
`projeção SDD — não executada/validada pelo CLI Spec Kit`.

O CTO registra no documento qual template e versão/commit foram utilizados,
quando verificáveis. Não invente versão nem assuma comandos da versão mais
recente. A disponibilidade do CLI é verificada no projeto quando for utilizado.

PO converte essa projeção à spec do tipo da demanda, preservando os IDs. Se o
projeto usa Spec Kit operacionalmente, CTO e senior-developer produzem plan,
research, data-model, contracts e tasks após o esclarecimento, usando os
templates instalados. Não atribua escolha de arquitetura ao BA nem declare
esses arquivos existentes antes de criá-los. Execução técnica continua pelo
refinamento/G1 do kit. Não execute implementação automática do Spec Kit antes
do G1 e não instale ferramentas como efeito colateral do discovery.

Uma revisão aprovada corresponde a um único conjunto de requisitos. Ao
alterar PRD, BRD ou spec, reconcilie o modelo, refaça as projeções afetadas e
revalide o selo. Na consolidação G9, doc-writer preserva os IDs e a origem na
SPEC RFC; o pacote de discovery continua como trilha histórica da demanda.
