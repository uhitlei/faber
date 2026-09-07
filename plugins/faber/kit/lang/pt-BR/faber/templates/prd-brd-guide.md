# Guia de PRD/BRD — como a fábrica transforma um Brainstorm em PRD e BRD

> **Este arquivo é um SLOT.** Substitua-o pelo SEU guia de PRD/BRD (o `.md`
> que você usa na sua organização): o comando `/faber-init` no modo
> `brainstorm` **segue à letra o que estiver aqui** — estrutura, seções,
> critérios de completude e tom. O instalador aceita `--prd-guide <arquivo.md>`
> para colocar o seu guia neste lugar. O conteúdo abaixo é o guia PADRÃO,
> usado só quando você não fornece o seu.

## 1. Princípios

1. **Nada inventado:** todo requisito deve rastrear a uma linha do brainstorm
   ou a uma decisão explícita do Owner. O que não está no brainstorm vira
   **pergunta aberta**, nunca suposição.
2. **Problema antes de solução:** o PRD descreve o problema, o público e o
   resultado esperado; a solução técnica pertence às specs (fase seguinte).
3. **Mensurável:** objetivos com métrica e alvo; requisitos com critério de
   aceitação verificável.
4. **Proporcional:** um brainstorm curto gera um PRD curto. Seções sem
   substância recebem "não se aplica" explícito, nunca texto de enchimento.
5. **Gate humano:** o PRD/BRD gerado é um RASCUNHO até o Owner aprovar
   (`/faber-approve` do bootstrap). Só depois nascem as specs.

## 2. Estrutura do PRD (`docs/PRD.md`)

1. **Visão** — uma frase: para quem, o quê, por quê.
2. **Problema e oportunidade** — dores observadas (cite o brainstorm), contexto, o custo de não fazer.
3. **Público e personas** — quem usa, em que contexto, com que frequência.
4. **Objetivos e métricas de sucesso** — tabela objetivo × métrica × alvo × prazo.
5. **Escopo do MVP** — o que entra na primeira entrega (lista numerada).
6. **Fora de escopo** — o que explicitamente NÃO entra agora (e por quê).
7. **Requisitos funcionais** — `RF-NN`, um por linha, cada um com critério de aceitação testável.
8. **Requisitos não-funcionais** — `RNF-NN`: desempenho, segurança/privacidade, acessibilidade, disponibilidade, compliance.
9. **Jornadas principais** — 2–5 fluxos de ponta a ponta em passos numerados.
10. **Dependências, riscos e premissas** — tabela com mitigação/dono.
11. **Roadmap de alto nível** — fases/marcos (sem datas inventadas: "a definir" se não houver).
12. **Perguntas abertas** — tudo que o brainstorm não responde; cada uma com quem decide.
13. **Rastreabilidade** — tabela `RF/RNF × trecho do brainstorm` (citação curta).

## 3. Estrutura do BRD (`docs/BRD.md`)

1. **Resumo executivo** — o caso de negócio em 5 linhas.
2. **Contexto de negócio** — mercado/organização, motivação, alternativas consideradas.
3. **Stakeholders** — papel, interesse, influência, decisão que tomam.
4. **Objetivos de negócio e KPIs** — alinhados aos objetivos do PRD.
5. **Benefícios esperados** — quantitativos e qualitativos.
6. **Custos e esforço estimado** — ordem de grandeza (ou "a estimar após as specs").
7. **Restrições** — prazo, orçamento, regulatório, tecnologia imposta.
8. **Riscos de negócio** — probabilidade × impacto × mitigação.
9. **Critérios de sucesso do projeto** — como saberemos que deu certo.
10. **Aprovação** — quem aprova e o que muda após aprovado.

## 4. Critérios de completude (o CTO confere antes de pedir aprovação)

- [ ] Toda seção presente (ou "não se aplica" justificado).
- [ ] Todo RF/RNF com critério de aceitação e linha de rastreabilidade.
- [ ] Nenhuma métrica/prazo/custo inventado — ausência declarada.
- [ ] Perguntas abertas listadas e endereçadas a quem decide.
- [ ] Idioma: o de `FABER_LANG`.
