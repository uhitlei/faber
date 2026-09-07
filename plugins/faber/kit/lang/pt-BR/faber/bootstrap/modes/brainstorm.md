# Modo `brainstorm` — só existe um arquivo de brainstorm

## Fluxo vigente desde 1.1.0

Execute o playbook `discovery.md` usando o brainstorm como fonte textual.
Preserve IDs B-NN existentes como aliases nas evidências. O pacote e BRD/PRD
ficam em `faber/bootstrap/requirements/`; não crie cópias concorrentes em docs.
A aprovação humana continua obrigatória. As etapas abaixo descrevem o fluxo
legado para leitura de projetos anteriores; não execute os dois fluxos.

## Fluxo histórico 1.0.0

Sinais: `*brainstorm*.md`, `ideias.md`, `ideas.md`, `braindump.md`,
`notas*.md` na raiz ou em `docs/`. É o insumo mais cru: a fábrica primeiro
**produz o PRD e o BRD**, seguindo o guia do Owner, e só depois de aprovados
continua como o modo `prd`.

## Etapa 1 — Ler o guia e o brainstorm (com evidência)

1. `inventario-brainstorm` — liste os arquivos de entrada e o guia em uso.
2. Leia **`faber/templates/prd-brd-guide.md` inteiro** — é o guia do Owner
   (ou o padrão do kit, se ele não trouxe o seu). **Ele manda** na estrutura,
   seções, critérios de completude e tom do PRD/BRD. Os templates
   `prd.template.md`/`brd.template.md` são só o esqueleto padrão: se o guia
   definir outra estrutura, use a do guia.
3. Leia o brainstorm inteiro. Monte `faber/bootstrap/MAPA-BRAINSTORM.md`:
   cada ideia/frase numerada (`B-NN`) com classificação (problema · público ·
   objetivo · requisito · restrição · risco · dúvida · fora de escopo).

## Etapa 2 — PRD e BRD (rascunhos)

- `docs/PRD.md` e `docs/BRD.md` (crie `docs/` se não existir), seguindo o
  guia. **Rastreabilidade obrigatória:** todo requisito cita o `B-NN` de
  origem. O que o brainstorm não diz vira **pergunta aberta** (no PRD e em
  `PERGUNTAS.md`), nunca suposição — métricas, prazos e custos inventados são
  proibidos ("a definir" é a resposta honesta).
- Confira os **critérios de completude** do guia antes de entregar.
- Evidência: `faber/scripts/evidence.sh faber/bootstrap prd-completo --
  bash -c "! grep -qF '{{' docs/PRD.md docs/BRD.md && echo ok"`.

## Etapa 3 — PARADA OBRIGATÓRIA: aprovação do PRD/BRD

Em **qualquer** modo de interação, pare aqui. Commit + push da branch
`faber/bootstrap` e um único pedido ao Owner: ler `docs/PRD.md` e
`docs/BRD.md`, responder as perguntas de `PERGUNTAS.md` e dizer
**"PRD aprovado"** (ou pedir ajustes). Registre a aprovação em
`faber/bootstrap/CONTEXT.md` (`prd_aprovado_em`, `por`). Sem aprovação, não
existem specs — o PRD errado contaminaria tudo que vem depois.

## Etapa 4 — Continuar como `prd`

Com o PRD/BRD aprovados, execute as Etapas 2–5 de
`faber/bootstrap/modes/prd.md` (arquitetura `[PROPOSTA]`, globais, features,
backlog) e o "Encerramento" do `/faber-init`.
