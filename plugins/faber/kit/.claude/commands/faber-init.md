---
description: Bootstrap da fábrica no repositório — lê o contexto detectado pelo install.sh (repo existente · spec-kit · PRD/BRD · brainstorm · vazio), gera specs/ARQUITETURA e prepara a fábrica para a primeira demanda
argument-hint: "[--mode existing-repo|spec-kit|prd|brainstorm|discovery|vazio] [--interaction gates|step-by-step]"
---

# /faber-init

Argumentos (opcionais): **$ARGUMENTS**

Você é o CTO (CLAUDE.md). Este comando **inicializa a fábrica** neste
repositório. Ele roda **uma vez** (ou de novo, deliberadamente, com `--mode`),
e produz a base de conhecimento (`@@FABER_SPECS_DIR@@/`) da qual todas as
demandas partem. Você **não implementa código de produto** aqui — só
conhecimento, configuração e backlog.

## 0. Leia o contexto (disco, não memória)

1. `faber/bootstrap/CONTEXT.md` — escrito pelo `install.sh`: `modo`
   detectado, sinais encontrados, arquivos de entrada, `interacao`, `status`.
   Se `status: concluido` e nenhum `--mode` foi passado → informe que o
   bootstrap já foi feito e pare.
2. `faber/config/faber.env` — a configuração (owner, trunk, comandos,
   módulos). Se `FABER_INTERACTION` estiver vazio ou `--interaction` não foi
   dado e o CONTEXTO marca `interacao: perguntar`, **pergunte agora** a
   @@FABER_OWNER_NAME@@: *"Quer interagir só nos gates de validação (G1/G6/G8
   e dúvidas críticas) ou passo a passo?"* Grave a resposta em
   `FABER_INTERACTION` (edição de `faber/config/faber.env` pede confirmação
   do H2 — a confirmação do Owner é a resposta).
3. O playbook do modo: `faber/bootstrap/modes/<modo>.md`. **Siga-o.**

## 1. Regras do bootstrap (valem para todos os modos)

- Trabalhe na branch `faber/bootstrap` (criada pelo `install.sh`). Commits
  pequenos, `chore(faber): …`. Nunca no trunk/produção (H1).
- **Nada inventado.** Fato lido do código/documento → afirmação. Inferência →
  marcada `[PROPOSTA]`. Lacuna → **pergunta** em `faber/bootstrap/PERGUNTAS.md`
  (agrupadas; uma rodada só, §20).
- Use os templates: `faber/templates/specs-global/*.md` (globais 00–08 +
  README), `faber/templates/spec-feature.template.md` (features, 17 seções),
  `faber/templates/prd.template.md` / `brd.template.md` + o guia
  `faber/templates/prd-brd-guide.md` (brainstorm). Nenhum `{{...}}` sobra em
  documento entregue.
- **Evidência executada** de tudo que for verificável (comandos de lint/build/
  test detectados, contagens, árvore de diretórios):
  `faber/scripts/evidence.sh faber/bootstrap <slug> -- <comando>`
  (a pasta `faber/bootstrap/evidence/` funciona como a de uma demanda).
- Ajuste `faber/config/faber.env` ao que descobrir (comandos reais de lint/
  build/test, dir de migrations, paths protegidos, E2E) — sempre listando as
  mudanças propostas para o Owner confirmar (H2 pede confirmação).
- Atualize `faber/ARQUITETURA.md §2` (cenário) e `CLAUDE.md §6` (ponteiros)
  com o que for específico do projeto — sem mudar regras nem numeração.
- Idioma: `FABER_LANG`.

## 2. Encerramento (todos os modos)

1. `@@FABER_SPECS_DIR@@/README.md` com o mapa real (globais + features).
2. **Backlog inicial** em `faber/bootstrap/BACKLOG.md`: demandas candidatas
   (título, tipo §14, prioridade, origem no documento fonte). **Não** crie as
   issues ainda — o Owner escolhe por onde começar (`/faber-task`).
3. `faber/bootstrap/CONTEXT.md` → `status: concluido` + resumo do que foi gerado.
4. Push da branch e PR `faber/bootstrap → @@FABER_TRUNK@@` com o resumo
   (o merge é o **gate de fundação**, do Owner). Com `FABER_GH=off`: deixe a
   branch pronta e diga como mesclar.
5. Reporte em um único bloco: o que foi gerado (paths), as `[PROPOSTA]` que
   precisam de confirmação, as perguntas abertas e o próximo passo
   (`/faber-task <primeira demanda do backlog>`).

## 3. Interação

- **`gates`**: execute tudo sem parar; as dúvidas vão para `PERGUNTAS.md` e são
  feitas **uma vez**, no fim (ou no início, se o insumo for insuficiente para
  começar). O único ponto de parada é a PR de fundação — exceto no modo
  `brainstorm`/`discovery`, que têm uma parada obrigatória a mais: **aprovação do PRD/BRD
  antes de gerar specs** (ver playbook).
- **`step-by-step`**: pare ao fim de cada etapa do playbook e peça ok.
